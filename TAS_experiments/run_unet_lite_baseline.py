#!/usr/bin/env python3
"""
LB3: U-Net-lite baseline for SC-TAS paper (CGI 2026).

A lightweight convolutional encoder-decoder trained on pixel-level features
to predict scoring FDM from free-viewing prior + NR artifact map.

Architecture:
  Input:  2-channel (P_F, A) at 128x128
  Enc-1:  Conv(2->16,3)-ReLU, Conv(16->16,3)-ReLU, MaxPool  -> 64x64
  Enc-2:  Conv(16->32,3)-ReLU, Conv(32->32,3)-ReLU, MaxPool  -> 32x32
  Bottleneck: Conv(32->64,3)-ReLU, Conv(64->64,3)-ReLU
  Dec-2:  Upsample + cat(skip2) -> Conv(96->32,3)-ReLU, Conv(32->32,3)-ReLU -> 64x64
  Dec-1:  Upsample + cat(skip1) -> Conv(48->16,3)-ReLU, Conv(16->16,3)-ReLU -> 128x128
  Head:   Conv(16->1,1) + Sigmoid
  Total:  118,129 trainable parameters

Evaluation protocol (same as Ridge/MLP):
  R2: 40-fold LOCO  (leave-one-content-out)
  INT: trained on ALL R2, zero-shot to 54 INT stimuli
  Metrics: CC, JSD
"""

import sys, os, re, json, time, logging, warnings
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader as TorchDL

warnings.filterwarnings('ignore')

# --- Paths -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics

RESULTS_DIR = config.RESULTS_DIR / 'unet_lite_baseline'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

R1_ROOT = config.R1_ROOT
INT_ROOT = config.INT_ROOT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(
            RESULTS_DIR / 'unet_lite.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Constants ----------------------------------------------------------------
LB_RESIZE  = 128   # Conv net benefits from higher resolution than Ridge/MLP 64
BATCH_SIZE = 64
EPOCHS     = 100
LR         = 1e-3
PATIENCE   = 15
SEED       = 42


# ==============================================================================
# MODEL
# ==============================================================================
class UNetLite(nn.Module):
    """Lightweight U-Net: 2-ch input (P_F, A) -> 1-ch output (P_Q_hat)."""
    def __init__(self):
        super().__init__()
        self.enc1 = nn.Sequential(
            nn.Conv2d(2, 16, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(16, 16, 3, padding=1), nn.ReLU(inplace=True),
        )
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = nn.Sequential(
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, 3, padding=1), nn.ReLU(inplace=True),
        )
        self.pool2 = nn.MaxPool2d(2)
        self.bottleneck = nn.Sequential(
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(inplace=True),
        )
        self.up2 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        self.dec2 = nn.Sequential(
            nn.Conv2d(64 + 32, 32, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, 3, padding=1), nn.ReLU(inplace=True),
        )
        self.up1 = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        self.dec1 = nn.Sequential(
            nn.Conv2d(32 + 16, 16, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(16, 16, 3, padding=1), nn.ReLU(inplace=True),
        )
        self.head = nn.Sequential(nn.Conv2d(16, 1, 1), nn.Sigmoid())

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        b  = self.bottleneck(self.pool2(e2))
        d2 = self.dec2(torch.cat([self.up2(b), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.head(d1)

    @staticmethod
    def param_count():
        m = UNetLite()
        return sum(p.numel() for p in m.parameters() if p.requires_grad)


# ==============================================================================
# HELPERS
# ==============================================================================
def normalize_to_prob(m):
    m = np.maximum(m, 0).astype(np.float64)
    s = np.sum(m) + 1e-12
    return m / s


def minmax_normalize(m):
    """Normalize map to [0,1] range for training."""
    mn = m.min()
    mx = m.max()
    if mx - mn < 1e-10:
        return np.zeros_like(m, dtype=np.float32)
    return ((m - mn) / (mx - mn)).astype(np.float32)


def negative_cc_loss(pred, target):
    """Negative Pearson correlation loss (differentiable)."""
    # pred, target: (B, 1, H, W)
    pred_flat = pred.view(pred.size(0), -1)
    tgt_flat = target.view(target.size(0), -1)
    pred_mean = pred_flat.mean(dim=1, keepdim=True)
    tgt_mean = tgt_flat.mean(dim=1, keepdim=True)
    pred_c = pred_flat - pred_mean
    tgt_c = tgt_flat - tgt_mean
    num = (pred_c * tgt_c).sum(dim=1)
    den = torch.sqrt((pred_c ** 2).sum(dim=1) * (tgt_c ** 2).sum(dim=1) + 1e-8)
    cc = num / den
    return -cc.mean()  # minimize = maximize CC


def resize_map(m, size):
    """Resize 2-D map to (size, size) using cv2."""
    return cv2.resize(m.astype(np.float32), (size, size),
                      interpolation=cv2.INTER_LINEAR)


def load_bmp_gray(path):
    from PIL import Image as PILImage
    arr = np.array(PILImage.open(path), dtype=np.float32)
    if len(arr.shape) == 3:
        arr = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    return arr


def load_bmp_ycrcb(path):
    from PIL import Image as PILImage
    arr = np.array(PILImage.open(path), dtype=np.float32)
    if len(arr.shape) == 3 and arr.shape[2] >= 3:
        bgr = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2BGR)
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    gray = arr if len(arr.shape) == 2 else arr[:, :, 0]
    return np.stack([gray, gray, gray], axis=-1).astype(np.float32)


def load_sal_prob(path, target_shape=None):
    sal = load_bmp_gray(path)
    if target_shape and sal.shape[:2] != target_shape:
        sal = cv2.resize(sal, (target_shape[1], target_shape[0]),
                         interpolation=cv2.INTER_LINEAR)
    return normalize_to_prob(sal)


class SaliencyDataset(Dataset):
    """Dataset of (P_F, A) -> P_Q tensors at LB_RESIZE resolution.
    All maps are min-max normalized to [0,1] for stable training."""
    def __init__(self, samples):
        self.samples = samples   # list of (pf, a, pq) each (LB_RESIZE, LB_RESIZE) float32 [0,1]
    def __len__(self):
        return len(self.samples)
    def __getitem__(self, idx):
        pf, a, pq = self.samples[idx]
        x = np.stack([pf, a], axis=0).astype(np.float32)   # (2, H, W)
        y = pq[np.newaxis].astype(np.float32)               # (1, H, W)
        return torch.from_numpy(x), torch.from_numpy(y)


def train_unet(train_data, device, tag=''):
    """Train U-Net-lite and return model with best training loss."""
    model = UNetLite().to(device)
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    ds = SaliencyDataset(train_data)
    dl = TorchDL(ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True)

    best_loss = float('inf')
    best_state = None
    patience_cnt = 0

    for ep in range(EPOCHS):
        model.train()
        ep_loss = 0.0
        n_b = 0
        for xb, yb in dl:
            xb, yb = xb.to(device), yb.to(device)
            pred = model(xb)
            loss = negative_cc_loss(pred, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            ep_loss += loss.item()
            n_b += 1
        avg = ep_loss / max(n_b, 1)
        scheduler.step(avg)

        if avg < best_loss - 1e-7:
            best_loss = avg
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_cnt = 0
        else:
            patience_cnt += 1
        if patience_cnt >= PATIENCE:
            break

    model.load_state_dict(best_state)
    model.eval()
    return model


# ==============================================================================
# DATA LOADING (mirrors run_crossdataset_baselines.py exactly)
# ==============================================================================
def load_all_r2(loader, artifact_gen):
    """Load R2 -> dict[content] -> list of sample dicts."""
    logger.info("Loading R2 dataset (40 x 4 JPEG QF)...")
    t = time.time()
    contents = loader.get_unique_contents()
    all_data = {}
    artifact_nr = {}

    for c in contents:
        cdata = loader.get_data_for_content(c, preprocess_saliency=True)
        all_data[c] = cdata
        for level in cdata['levels']:
            img = cdata['images'][level]
            a = artifact_gen.compute_nr_artifact(img)
            artifact_nr[(c, level)] = artifact_gen.normalize_artifact_to_probability(a)

    logger.info(f"R2 loaded in {time.time()-t:.1f}s: {len(contents)} contents, "
                f"{sum(len(all_data[c]['levels']) for c in contents)} stimuli")
    return contents, all_data, artifact_nr


def load_all_r1(artifact_gen):
    """Load R1: 29 pristine LIVE images + free-looking saliency."""
    logger.info("Loading R1...")
    t = time.time()
    r1_data = []
    test_dir = R1_ROOT / 'TestImages'
    sal_dir  = R1_ROOT / 'SaliencyMaps'
    if not test_dir.exists():
        logger.error(f"R1 not found: {test_dir}")
        return []

    for fname in sorted(os.listdir(test_dir)):
        if not fname.lower().endswith('.bmp'):
            continue
        content = fname.rsplit('.', 1)[0].lower()
        img_path = test_dir / fname
        sal_path = sal_dir / fname
        if not sal_path.exists():
            found = False
            for sf in os.listdir(sal_dir):
                if sf.lower() == fname.lower():
                    sal_path = sal_dir / sf
                    found = True
                    break
            if not found:
                continue

        img = load_bmp_ycrcb(img_path)
        sal = load_sal_prob(sal_path, target_shape=img.shape[:2])
        a_nr = artifact_gen.compute_nr_artifact(img)
        a_nr_prob = artifact_gen.normalize_artifact_to_probability(a_nr)
        r1_data.append({
            'content': content, 'image_shape': img.shape[:2],
            'saliency': sal, 'artifact_nr': a_nr_prob,
        })
        del img

    logger.info(f"R1: {len(r1_data)} images in {time.time()-t:.1f}s")
    return r1_data


def load_all_int(artifact_gen, r1_priors):
    """Load INT: 54 distorted stimuli with R1 priors."""
    logger.info("Loading INT...")
    t = time.time()
    img_dir  = INT_ROOT / 'images'
    sal_dir  = INT_ROOT / 'Saliency Maps'
    if not img_dir.exists():
        logger.error(f"INT not found: {img_dir}")
        return []

    pat = re.compile(r'(.+?)_(blur|jpeg|noise)_\((\d+)\)\.bmp', re.IGNORECASE)
    int_data = []

    for fname in sorted(os.listdir(img_dir)):
        fpath = img_dir / fname
        if fpath.is_dir():
            continue
        m = pat.match(fname)
        if not m:
            continue

        content_raw = m.group(1)
        dist_type   = m.group(2).lower()
        dist_level  = int(m.group(3))
        content     = content_raw.lower()

        img = load_bmp_ycrcb(fpath)
        h, w = img.shape[:2]

        # GT saliency
        sal_name = f"{content_raw}_{dist_type}_({dist_level})_AVG.bmp"
        sal_path = sal_dir / sal_name
        if not sal_path.exists():
            found = False
            for sf in os.listdir(sal_dir):
                if sf.lower() == sal_name.lower():
                    sal_path = sal_dir / sf
                    found = True
                    break
            if not found:
                continue

        sal_gt = load_sal_prob(sal_path, target_shape=(h, w))

        # R1 prior
        if content in r1_priors:
            prior = r1_priors[content]
            if prior.shape[:2] != (h, w):
                prior = cv2.resize(prior.astype(np.float32), (w, h),
                                   interpolation=cv2.INTER_LINEAR)
                prior = normalize_to_prob(prior)
        else:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            prior = np.exp(-((yy - h/2)**2 + (xx - w/2)**2) / (2 * (min(h,w)/4)**2))
            prior = normalize_to_prob(prior)

        # NR artifact
        a_nr = artifact_gen.compute_nr_artifact(img)
        a_nr_prob = artifact_gen.normalize_artifact_to_probability(a_nr)

        int_data.append({
            'content': content, 'dist_type': dist_type, 'dist_level': dist_level,
            'saliency_gt': sal_gt, 'prior': prior,
            'artifact_nr': a_nr_prob, 'image_shape': (h, w),
        })
        del img

    logger.info(f"INT: {len(int_data)} stimuli in {time.time()-t:.1f}s")
    return int_data


# ==============================================================================
# MAIN PIPELINE
# ==============================================================================
def main():
    t0 = time.time()
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")
    if device.type == 'cuda':
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

    SZ = LB_RESIZE
    n_params = UNetLite.param_count()
    logger.info(f"U-Net-lite parameters: {n_params:,}")

    # -- Load R2 ---------------------------------------------------------------
    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator()
    contents, all_data, artifact_nr = load_all_r2(loader, artifact_gen)

    # Pre-compute resized features for every (content, level)
    prep = {}
    for c in contents:
        cdata = all_data[c]
        for level in cdata['levels']:
            pf = cdata['saliency_freelook'][level]
            pq = cdata['saliency_scoring'][level]
            a  = artifact_nr[(c, level)]
            if pf is None or pq is None:
                continue

            pf_s = minmax_normalize(resize_map(pf, SZ))
            a_s  = minmax_normalize(resize_map(a,  SZ))
            pq_s = minmax_normalize(resize_map(pq, SZ))

            prep[(c, level)] = {
                'pf_s': pf_s, 'a_s': a_s, 'pq_s': pq_s,
                'pf_full': pf, 'pq_full': pq,
            }
    logger.info(f"Prepared {len(prep)} R2 samples at {SZ}x{SZ}")

    # ==========================================================================
    # STAGE 1: LOCO on R2
    # ==========================================================================
    logger.info("\n" + "=" * 70)
    logger.info("STAGE 1: LOCO on R2 (U-Net-lite)")
    logger.info("=" * 70)

    import pandas as pd   # installed via SLURM pip
    loco_rows = []
    t_loco = time.time()

    for fold_idx, held_out in enumerate(contents):
        if fold_idx % 10 == 0:
            logger.info(f"  Fold {fold_idx+1}/40  ({time.time()-t_loco:.0f}s)")

        # Build training set
        train_data = []
        for key, val in prep.items():
            if key[0] == held_out:
                continue
            train_data.append((val['pf_s'], val['a_s'], val['pq_s']))

        model = train_unet(train_data, device, tag=f'fold{fold_idx}')

        # Evaluate on held-out content
        with torch.no_grad():
            for level in all_data[held_out]['levels']:
                key = (held_out, level)
                if key not in prep:
                    continue
                val = prep[key]

                x = np.stack([val['pf_s'], val['a_s']], axis=0).astype(np.float32)
                xt = torch.from_numpy(x).unsqueeze(0).to(device)
                pred_s = model(xt).squeeze().cpu().numpy()   # (SZ, SZ)

                # Upsample to original resolution
                orig_h, orig_w = val['pq_full'].shape[:2]
                pred_full = cv2.resize(pred_s.astype(np.float32),
                                       (orig_w, orig_h),
                                       interpolation=cv2.INTER_LINEAR)
                pred_prob = normalize_to_prob(pred_full)

                cc  = SaliencyMetrics.pearson_correlation(pred_prob, val['pq_full'])
                jsd = SaliencyMetrics.jensen_shannon_divergence(pred_prob, val['pq_full'])

                loco_rows.append({
                    'content': held_out, 'level': level,
                    'unet_cc': cc, 'unet_jsd': jsd,
                })

        # Periodic progress
        if (fold_idx + 1) % 10 == 0:
            tmp = pd.DataFrame(loco_rows)
            logger.info(f"    Running: CC={tmp.unet_cc.mean():.4f}  JSD={tmp.unet_jsd.mean():.4f}")

    df_r2 = pd.DataFrame(loco_rows)
    df_r2.to_csv(RESULTS_DIR / 'unet_lite_r2_loco.csv', index=False)
    logger.info(f"\nR2 LOCO (U-Net-lite, {time.time()-t_loco:.0f}s):")
    logger.info(f"  CC  = {df_r2.unet_cc.mean():.4f} +/- {df_r2.unet_cc.std():.4f}")
    logger.info(f"  JSD = {df_r2.unet_jsd.mean():.4f} +/- {df_r2.unet_jsd.std():.4f}")

    # ==========================================================================
    # STAGE 2: INT zero-shot
    # ==========================================================================
    logger.info("\n" + "=" * 70)
    logger.info("STAGE 2: INT Zero-Shot (train on all R2)")
    logger.info("=" * 70)

    # Train on all R2
    all_train = []
    for key, val in prep.items():
        all_train.append((val['pf_s'], val['a_s'], val['pq_s']))

    model_full = train_unet(all_train, device, tag='full_r2')
    logger.info(f"Full R2 model trained")

    # Load R1 priors + INT data
    r1_data = load_all_r1(artifact_gen)
    r1_priors = {d['content']: d['saliency'] for d in r1_data}
    int_data = load_all_int(artifact_gen, r1_priors)

    int_rows = []
    with torch.no_grad():
        for item in int_data:
            pf = item['prior']
            a  = item['artifact_nr']
            gt = item['saliency_gt']
            h, w = item['image_shape']

            pf_s = minmax_normalize(resize_map(pf, SZ))
            a_s  = minmax_normalize(resize_map(a,  SZ))

            x = np.stack([pf_s, a_s], axis=0).astype(np.float32)
            xt = torch.from_numpy(x).unsqueeze(0).to(device)
            pred_s = model_full(xt).squeeze().cpu().numpy()

            pred_full = cv2.resize(pred_s.astype(np.float32), (w, h),
                                   interpolation=cv2.INTER_LINEAR)
            pred_prob = normalize_to_prob(pred_full)

            # Ensure GT matches
            if gt.shape != pred_prob.shape:
                gt = cv2.resize(gt.astype(np.float32),
                                (pred_prob.shape[1], pred_prob.shape[0]),
                                interpolation=cv2.INTER_LINEAR)
                gt = normalize_to_prob(gt)

            cc  = SaliencyMetrics.pearson_correlation(pred_prob, gt)
            jsd = SaliencyMetrics.jensen_shannon_divergence(pred_prob, gt)

            int_rows.append({
                'content': item['content'],
                'dist_type': item['dist_type'],
                'dist_level': item['dist_level'],
                'unet_cc': cc, 'unet_jsd': jsd,
            })

    df_int = pd.DataFrame(int_rows)
    df_int.to_csv(RESULTS_DIR / 'unet_lite_int_zeroshot.csv', index=False)
    logger.info(f"\nINT Zero-Shot (U-Net-lite):")
    logger.info(f"  CC  = {df_int.unet_cc.mean():.4f} +/- {df_int.unet_cc.std():.4f}")
    logger.info(f"  JSD = {df_int.unet_jsd.mean():.4f} +/- {df_int.unet_jsd.std():.4f}")

    for dt in ['jpeg', 'blur', 'noise']:
        sub = df_int[df_int.dist_type == dt]
        if len(sub) > 0:
            logger.info(f"  {dt:5s}: CC={sub.unet_cc.mean():.4f}  JSD={sub.unet_jsd.mean():.4f} (n={len(sub)})")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    elapsed = time.time() - t0
    summary = {
        'model': 'U-Net-lite',
        'resolution': SZ,
        'n_parameters': n_params,
        'epochs_max': EPOCHS,
        'patience': PATIENCE,
        'lr': LR,
        'r2_loco': {
            'cc_mean':  round(float(df_r2.unet_cc.mean()), 4),
            'cc_std':   round(float(df_r2.unet_cc.std()), 4),
            'jsd_mean': round(float(df_r2.unet_jsd.mean()), 4),
            'jsd_std':  round(float(df_r2.unet_jsd.std()), 4),
            'n': len(df_r2),
        },
        'int_zeroshot': {
            'cc_mean':  round(float(df_int.unet_cc.mean()), 4),
            'cc_std':   round(float(df_int.unet_cc.std()), 4),
            'jsd_mean': round(float(df_int.unet_jsd.mean()), 4),
            'jsd_std':  round(float(df_int.unet_jsd.std()), 4),
            'n': len(df_int),
        },
        'elapsed_seconds': round(elapsed, 1),
    }

    with open(RESULTS_DIR / 'unet_lite_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\n{'='*70}")
    logger.info(f"DONE in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    logger.info(f"Results: {RESULTS_DIR}")
    logger.info(f"{'='*70}")


if __name__ == '__main__':
    main()
