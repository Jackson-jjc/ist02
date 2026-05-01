#!/usr/bin/env python3
"""
Cross-Dataset Generalization + Learning Baselines Experiment
CGI 2026 / TVC Journal Track

Supplements the main R2 experiment (run_revised_experiment.py) with:
  Stage 1: Cross-dataset R1 — stability on 29 pristine LIVE images
  Stage 2: Cross-dataset INT — zero-shot on 54 multi-distortion stimuli
  Stage 3: LB1 (Ridge) + LB2 (MLP) on R2 with LOCO
  Stage 4: Final models trained on all R2 → zero-shot on INT
  Stage 5: Summary tables (Table-G1, Table-G2) + statistical tests

Datasets:
  R2 (main):  40 contents × 4 JPEG QF = 160 stimuli  (FreeLook + Scoring)
  R1:         29 pristine LIVE images + free-looking saliency  (no distortion)
  INT:        6 contents × 3 dist-types × 3 levels = 54 stimuli  (blur/jpeg/noise)

Cross-dataset protocol:
  - SC-TAS parameters fixed from R2 (alpha=1.0, beta_NR=0.3, beta_FR=0.5, tau=0.83)
  - R1 free-looking saliency maps serve as priors for INT (all 6 INT contents overlap R1)
  - No re-tuning: pure zero-shot transfer
"""

import sys
import os
import re
import json
import time
import logging
import warnings
import numpy as np
import pandas as pd
import cv2
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from scipy.stats import wilcoxon, ttest_rel, pearsonr, spearmanr
from scipy.spatial.distance import jensenshannon
from PIL import Image

warnings.filterwarnings('ignore')

# ─── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics

RESULTS_DIR = PROJECT_ROOT / 'results' / 'crossdataset_baselines'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

R1_ROOT = Path('/iridisfs/scratch/jc15u24/Code/IST02/TUD_LIVE_EyeTracking/TUD_LIVE_EyeTracking')
INT_ROOT = Path('/iridisfs/scratch/jc15u24/Code/IST02/TUD_Interactions')

log_file = RESULTS_DIR / 'experiment.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────────────────
LB_RESIZE = 64  # Downsample resolution for learning baselines


# ─── SC-TAS (Eq.7 of the paper) ────────────────────────────────────────────────
class SCTAS:
    """Stability-Constrained Task-Adaptive Saliency."""
    def __init__(self, alpha=1.0, beta=0.3, tau=0.83, eta=0.9):
        self.alpha = alpha
        self.beta = beta
        self.tau = tau
        self.eta = eta

    def predict(self, p_free, a_map):
        alpha, beta = self.alpha, self.beta
        eps = 1e-12
        for _ in range(50):
            raw = alpha * p_free + beta * a_map
            raw = np.maximum(raw, 0)
            total = np.sum(raw) + eps
            p_hat = raw / total
            cc = np.corrcoef(p_hat.flatten(), p_free.flatten())[0, 1]
            if np.isnan(cc) or cc >= self.tau:
                break
            beta *= self.eta
        return p_hat


# ─── Helpers ────────────────────────────────────────────────────────────────────
def normalize_to_prob(m):
    m = np.maximum(m, 0).astype(np.float64)
    s = np.sum(m) + 1e-12
    return m / s


def bootstrap_ci(values, n_boot=2000, ci=0.95, seed=42):
    rng = np.random.RandomState(seed)
    vals = np.array(values)
    n = len(vals)
    if n < 2:
        return float(vals.mean()), float(vals.mean()), float(vals.mean())
    boot_means = np.array([rng.choice(vals, n, replace=True).mean() for _ in range(n_boot)])
    lo = np.percentile(boot_means, (1 - ci) / 2 * 100)
    hi = np.percentile(boot_means, (1 + ci) / 2 * 100)
    return float(lo), float(vals.mean()), float(hi)


def cohens_d(x, y):
    diff = np.array(x) - np.array(y)
    return float(diff.mean() / (diff.std(ddof=1) + 1e-12))


def load_bmp_gray(path):
    """Load BMP image as grayscale float32."""
    img = Image.open(path)
    arr = np.array(img, dtype=np.float32)
    if len(arr.shape) == 3:
        arr = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    return arr


def load_bmp_ycrcb(path):
    """Load BMP image in YCrCb color space (3-channel)."""
    img = Image.open(path)
    arr = np.array(img, dtype=np.float32)
    if len(arr.shape) == 3 and arr.shape[2] >= 3:
        bgr = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2BGR)
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    # Grayscale → fake 3-channel
    gray = arr if len(arr.shape) == 2 else arr[:, :, 0]
    return np.stack([gray, gray, gray], axis=-1).astype(np.float32)


def load_sal_prob(path, target_shape=None):
    """Load saliency map as probability distribution."""
    sal = load_bmp_gray(path)
    if target_shape and sal.shape[:2] != target_shape:
        sal = cv2.resize(sal, (target_shape[1], target_shape[0]),
                         interpolation=cv2.INTER_LINEAR)
    return normalize_to_prob(sal)


def make_pixel_features(p_f, a, size):
    """
    Create pixel-level feature matrix for regression.
    Features: [P_F value, A value, x_norm, y_norm]
    Returns: (X matrix [N×4], p_f_resized, a_resized)
    """
    p_f_r = cv2.resize(p_f.astype(np.float32), (size, size),
                       interpolation=cv2.INTER_LINEAR)
    a_r = cv2.resize(a.astype(np.float32), (size, size),
                     interpolation=cv2.INTER_LINEAR)
    p_f_r = normalize_to_prob(p_f_r).astype(np.float32)
    a_r = normalize_to_prob(a_r).astype(np.float32)

    yy, xx = np.mgrid[0:size, 0:size]
    xn = (xx.flatten().astype(np.float32)) / size
    yn = (yy.flatten().astype(np.float32)) / size
    X = np.column_stack([p_f_r.flatten(), a_r.flatten(), xn, yn])
    return X, p_f_r, a_r


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════
def load_all_r2(loader, artifact_gen):
    """Load R2 dataset + compute all artifact maps."""
    logger.info("Loading R2 dataset (40 contents × 4 JPEG QF)...")
    t = time.time()
    contents = loader.get_unique_contents()
    all_data = {}
    artifact_nr = {}
    artifact_fr = {}

    for c in contents:
        all_data[c] = loader.get_data_for_content(c, preprocess_saliency=True)
        ref_img = loader.load_original_image(c, color_space='ycrcb')
        for level in all_data[c]['levels']:
            img = all_data[c]['images'][level]
            key = (c, level)
            # FR artifact
            if ref_img is not None:
                ref_r = ref_img
                if ref_img.shape[:2] != img.shape[:2]:
                    ref_r = cv2.resize(ref_img, (img.shape[1], img.shape[0]))
                a_fr = artifact_gen.compute_fr_artifact(ref_r, img)
            else:
                a_fr = artifact_gen.compute_fr_artifact(img, img)
            artifact_fr[key] = artifact_gen.normalize_artifact_to_probability(a_fr)
            # NR artifact
            a_nr = artifact_gen.compute_nr_artifact(img)
            artifact_nr[key] = artifact_gen.normalize_artifact_to_probability(a_nr)

    logger.info(f"R2 loaded in {time.time()-t:.1f}s: {len(contents)} contents, "
                f"{sum(len(all_data[c]['levels']) for c in contents)} stimuli")
    return contents, all_data, artifact_nr, artifact_fr


def load_all_r1(artifact_gen):
    """Load R1: 29 pristine LIVE images + free-looking saliency maps."""
    logger.info("Loading R1 dataset (29 pristine LIVE images)...")
    t = time.time()
    r1_data = []
    test_dir = R1_ROOT / 'TestImages'
    sal_dir = R1_ROOT / 'SaliencyMaps'

    if not test_dir.exists():
        logger.error(f"R1 TestImages dir not found: {test_dir}")
        return []

    for fname in sorted(os.listdir(test_dir)):
        if not fname.lower().endswith('.bmp'):
            continue
        content = fname.rsplit('.', 1)[0].lower()  # e.g. "bikes"

        img_path = test_dir / fname
        sal_path = sal_dir / fname
        if not sal_path.exists():
            # Try case-insensitive
            found = False
            for sf in os.listdir(sal_dir):
                if sf.lower() == fname.lower():
                    sal_path = sal_dir / sf
                    found = True
                    break
            if not found:
                logger.warning(f"R1: saliency not found for {content}")
                continue

        img = load_bmp_ycrcb(img_path)
        sal = load_sal_prob(sal_path, target_shape=img.shape[:2])
        a_nr = artifact_gen.compute_nr_artifact(img)
        a_nr_prob = artifact_gen.normalize_artifact_to_probability(a_nr)

        r1_data.append({
            'content': content,
            'image_shape': img.shape[:2],
            'saliency': sal,
            'artifact_nr': a_nr_prob,
        })
        # Don't keep full image in memory
        del img

    logger.info(f"R1 loaded in {time.time()-t:.1f}s: {len(r1_data)} images")
    logger.info(f"  Contents: {[d['content'] for d in r1_data[:6]]}... ({len(r1_data)} total)")
    return r1_data


def load_all_int(artifact_gen, r1_priors):
    """
    Load INT dataset: 54 distorted stimuli with saliency GT.
    Uses R1 free-looking maps as priors (all 6 INT contents overlap R1).
    """
    logger.info("Loading INT dataset (6 contents × 3 dist-types × 3 levels)...")
    t = time.time()

    img_dir = INT_ROOT / 'images'
    orig_dir = INT_ROOT / 'images' / 'originals'
    sal_dir = INT_ROOT / 'Saliency Maps'

    if not img_dir.exists():
        logger.error(f"INT images dir not found: {img_dir}")
        return []

    # Load originals for FR artifact computation
    originals = {}
    if orig_dir.exists():
        for fname in os.listdir(orig_dir):
            if not fname.lower().endswith('.bmp'):
                continue
            # BikesO.bmp → bikes
            cname = fname.split('.')[0]  # "BikesO"
            if cname.endswith('O') or cname.endswith('o'):
                cname = cname[:-1]
            originals[cname.lower()] = load_bmp_ycrcb(orig_dir / fname)
    logger.info(f"INT originals: {sorted(originals.keys())}")

    # Parse distorted images
    pat = re.compile(r'(.+?)_(blur|jpeg|noise)_\((\d+)\)\.bmp', re.IGNORECASE)
    int_data = []

    for fname in sorted(os.listdir(img_dir)):
        fpath = img_dir / fname
        if fpath.is_dir():
            continue
        m = pat.match(fname)
        if not m:
            continue

        content_raw = m.group(1)       # e.g. "Bikes"
        dist_type = m.group(2).lower() # "blur" / "jpeg" / "noise"
        dist_level = int(m.group(3))   # 10 / 20 / 30
        content = content_raw.lower()  # "bikes"

        img = load_bmp_ycrcb(fpath)
        h, w = img.shape[:2]

        # Load GT saliency — try exact name first, then case-insensitive
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
                logger.warning(f"INT: saliency not found for {fname} (tried {sal_name})")
                continue

        sal_gt = load_sal_prob(sal_path, target_shape=(h, w))

        # R1 prior for this content
        if content in r1_priors:
            prior = r1_priors[content]
            if prior.shape[:2] != (h, w):
                prior = cv2.resize(prior.astype(np.float32), (w, h),
                                   interpolation=cv2.INTER_LINEAR)
                prior = normalize_to_prob(prior)
        else:
            logger.warning(f"INT: no R1 prior for '{content}', using Gaussian center bias")
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            prior = np.exp(-((yy - h/2)**2 + (xx - w/2)**2) / (2 * (min(h, w)/4)**2))
            prior = normalize_to_prob(prior)

        # NR artifact
        a_nr = artifact_gen.compute_nr_artifact(img)
        a_nr_prob = artifact_gen.normalize_artifact_to_probability(a_nr)

        # FR artifact (using original)
        a_fr_prob = None
        if content in originals:
            ref = originals[content]
            if ref.shape[:2] != (h, w):
                ref = cv2.resize(ref, (w, h))
            a_fr = artifact_gen.compute_fr_artifact(ref, img)
            a_fr_prob = artifact_gen.normalize_artifact_to_probability(a_fr)

        int_data.append({
            'content': content,
            'dist_type': dist_type,
            'dist_level': dist_level,
            'saliency_gt': sal_gt,
            'prior': prior,
            'artifact_nr': a_nr_prob,
            'artifact_fr': a_fr_prob,
            'image_shape': (h, w),
        })
        del img  # free memory

    logger.info(f"INT loaded in {time.time()-t:.1f}s: {len(int_data)} stimuli")
    for dt in ['jpeg', 'blur', 'noise']:
        n = sum(1 for d in int_data if d['dist_type'] == dt)
        logger.info(f"  {dt}: {n} stimuli")
    return int_data


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1: R1 Stability Test
# ═══════════════════════════════════════════════════════════════════════════════
def stage1_r1_stability(r1_data, sctas_nr):
    """Test SC-TAS stability on pristine images (no distortion → artifact ≈ 0)."""
    logger.info("\n" + "═" * 80)
    logger.info("STAGE 1: R1 Stability Test (Pristine Images)")
    logger.info("═" * 80)

    rows = []
    for item in r1_data:
        p_f = item['saliency']
        a = item['artifact_nr']

        # SC-TAS NR prediction
        p_hat = sctas_nr.predict(p_f, a)

        # Fixed mixture (0.5 * P_F + 0.5 * A)
        p_mix = normalize_to_prob(0.5 * p_f + 0.5 * a)

        rows.append({
            'content': item['content'],
            # Stability: SC-TAS vs prior (should be ~1.0 CC / ~0.0 JSD)
            'sctas_cc_vs_prior': SaliencyMetrics.pearson_correlation(p_hat, p_f),
            'sctas_jsd_vs_prior': SaliencyMetrics.jensen_shannon_divergence(p_hat, p_f),
            # Fixed mixture vs prior
            'mixture_cc_vs_prior': SaliencyMetrics.pearson_correlation(p_mix, p_f),
            'mixture_jsd_vs_prior': SaliencyMetrics.jensen_shannon_divergence(p_mix, p_f),
            # Artifact vs prior (sanity check: should be low CC)
            'artifact_cc_vs_prior': SaliencyMetrics.pearson_correlation(a, p_f),
            'artifact_jsd_vs_prior': SaliencyMetrics.jensen_shannon_divergence(a, p_f),
            # Mean artifact energy (should be low on pristine BMP)
            'mean_artifact_energy': float(np.mean(a)),
            'max_artifact_pixel': float(np.max(a)),
        })

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / 'r1_stability.csv', index=False)

    logger.info(f"R1: {len(df)} pristine images evaluated")
    logger.info(f"  SC-TAS  CC(P_hat, P_F):   {df['sctas_cc_vs_prior'].mean():.4f} ± {df['sctas_cc_vs_prior'].std():.4f}  (ideal: 1.0)")
    logger.info(f"  SC-TAS  JSD(P_hat, P_F):  {df['sctas_jsd_vs_prior'].mean():.4f} ± {df['sctas_jsd_vs_prior'].std():.4f}  (ideal: 0.0)")
    logger.info(f"  FixMix  CC(P_mix, P_F):   {df['mixture_cc_vs_prior'].mean():.4f} ± {df['mixture_cc_vs_prior'].std():.4f}")
    logger.info(f"  FixMix  JSD(P_mix, P_F):  {df['mixture_jsd_vs_prior'].mean():.4f} ± {df['mixture_jsd_vs_prior'].std():.4f}")
    logger.info(f"  Artifact CC(A, P_F):       {df['artifact_cc_vs_prior'].mean():.4f}")
    logger.info(f"  Mean artifact energy:      {df['mean_artifact_energy'].mean():.6f}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2: INT Cross-Dataset Zero-Shot
# ═══════════════════════════════════════════════════════════════════════════════
def stage2_int_crossdataset(int_data, sctas_nr, sctas_fr):
    """Zero-shot cross-dataset + cross-distortion evaluation on INT."""
    logger.info("\n" + "═" * 80)
    logger.info("STAGE 2: INT Cross-Dataset Zero-Shot Evaluation")
    logger.info("═" * 80)

    rows = []
    for item in int_data:
        p_f = item['prior']       # R1 free-looking prior
        p_gt = item['saliency_gt'] # INT GT saliency
        a_nr = item['artifact_nr']
        a_fr = item['artifact_fr']

        row = {
            'content': item['content'],
            'dist_type': item['dist_type'],
            'dist_level': item['dist_level'],
        }

        # 1. Prior only (baseline: R1 free-looking → INT GT)
        row['prior_cc'] = SaliencyMetrics.pearson_correlation(p_f, p_gt)
        row['prior_jsd'] = SaliencyMetrics.jensen_shannon_divergence(p_f, p_gt)

        # 2. Artifact-only NR
        row['artifact_nr_cc'] = SaliencyMetrics.pearson_correlation(a_nr, p_gt)
        row['artifact_nr_jsd'] = SaliencyMetrics.jensen_shannon_divergence(a_nr, p_gt)

        # 3. Fixed mixture NR
        p_mix_nr = normalize_to_prob(0.5 * p_f + 0.5 * a_nr)
        row['mixture_nr_cc'] = SaliencyMetrics.pearson_correlation(p_mix_nr, p_gt)
        row['mixture_nr_jsd'] = SaliencyMetrics.jensen_shannon_divergence(p_mix_nr, p_gt)

        # 4. SC-TAS NR (zero-shot with R2 params)
        p_tas_nr = sctas_nr.predict(p_f, a_nr)
        row['sctas_nr_cc'] = SaliencyMetrics.pearson_correlation(p_tas_nr, p_gt)
        row['sctas_nr_jsd'] = SaliencyMetrics.jensen_shannon_divergence(p_tas_nr, p_gt)

        # 5. FR variants (if original available)
        if a_fr is not None:
            row['artifact_fr_cc'] = SaliencyMetrics.pearson_correlation(a_fr, p_gt)
            row['artifact_fr_jsd'] = SaliencyMetrics.jensen_shannon_divergence(a_fr, p_gt)

            p_mix_fr = normalize_to_prob(0.5 * p_f + 0.5 * a_fr)
            row['mixture_fr_cc'] = SaliencyMetrics.pearson_correlation(p_mix_fr, p_gt)
            row['mixture_fr_jsd'] = SaliencyMetrics.jensen_shannon_divergence(p_mix_fr, p_gt)

            p_tas_fr = sctas_fr.predict(p_f, a_fr)
            row['sctas_fr_cc'] = SaliencyMetrics.pearson_correlation(p_tas_fr, p_gt)
            row['sctas_fr_jsd'] = SaliencyMetrics.jensen_shannon_divergence(p_tas_fr, p_gt)
        else:
            for k in ['artifact_fr_cc', 'artifact_fr_jsd',
                       'mixture_fr_cc', 'mixture_fr_jsd',
                       'sctas_fr_cc', 'sctas_fr_jsd']:
                row[k] = np.nan

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / 'int_crossdataset_all.csv', index=False)

    # Print summary
    methods = [
        ('Prior only',    'prior_cc',      'prior_jsd'),
        ('Artifact NR',   'artifact_nr_cc', 'artifact_nr_jsd'),
        ('Fixed mix NR',  'mixture_nr_cc',  'mixture_nr_jsd'),
        ('SC-TAS NR',     'sctas_nr_cc',    'sctas_nr_jsd'),
        ('Artifact FR',   'artifact_fr_cc', 'artifact_fr_jsd'),
        ('Fixed mix FR',  'mixture_fr_cc',  'mixture_fr_jsd'),
        ('SC-TAS FR',     'sctas_fr_cc',    'sctas_fr_jsd'),
    ]

    logger.info(f"\nINT: {len(df)} stimuli evaluated")
    logger.info("\n  ── Overall ──")
    for name, cc_col, jsd_col in methods:
        vals_cc = df[cc_col].dropna()
        vals_jsd = df[jsd_col].dropna()
        if len(vals_cc) > 0:
            logger.info(f"    {name:15s}  CC={vals_cc.mean():.4f}±{vals_cc.std():.4f}"
                        f"  JSD={vals_jsd.mean():.4f}±{vals_jsd.std():.4f}")

    # By distortion type → Table-G2
    g2_rows = []
    for dt in ['jpeg', 'blur', 'noise']:
        sub = df[df['dist_type'] == dt]
        if len(sub) == 0:
            continue
        logger.info(f"\n  ── {dt.upper()} (n={len(sub)}) ──")
        g2_row = {'dist_type': dt, 'n': len(sub)}
        for name, cc_col, jsd_col in methods:
            vals_cc = sub[cc_col].dropna()
            vals_jsd = sub[jsd_col].dropna()
            if len(vals_cc) > 0:
                logger.info(f"    {name:15s}  CC={vals_cc.mean():.4f}  JSD={vals_jsd.mean():.4f}")
                g2_row[f'{name}_cc'] = float(vals_cc.mean())
                g2_row[f'{name}_jsd'] = float(vals_jsd.mean())
        g2_rows.append(g2_row)

    df_g2 = pd.DataFrame(g2_rows)
    df_g2.to_csv(RESULTS_DIR / 'int_by_distortion_type.csv', index=False)

    # By distortion level within each type
    logger.info("\n  ── By Distortion Level ──")
    for dt in ['jpeg', 'blur', 'noise']:
        for lvl in [10, 20, 30]:
            sub = df[(df['dist_type'] == dt) & (df['dist_level'] == lvl)]
            if len(sub) == 0:
                continue
            logger.info(f"    {dt:5s} level={lvl:2d}:  Prior CC={sub['prior_cc'].mean():.4f}"
                        f"  SC-TAS NR CC={sub['sctas_nr_cc'].mean():.4f}"
                        f"  ΔJSD={sub['sctas_nr_jsd'].mean() - sub['prior_jsd'].mean():.4f}")

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 3: Learning Baselines on R2 (LOCO)
# ═══════════════════════════════════════════════════════════════════════════════
def stage3_learning_baselines_r2(all_data, artifact_maps_nr, contents):
    """LB1 (Ridge) + LB2 (MLP) on R2 with Leave-One-Content-Out."""
    logger.info("\n" + "═" * 80)
    logger.info("STAGE 3: Learning Baselines on R2 (LOCO)")
    logger.info("═" * 80)

    # Lazy import — only needed here
    from sklearn.linear_model import Ridge
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler

    SZ = LB_RESIZE

    # Pre-compute downsampled features/targets for all R2 stimuli
    prep = {}
    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            p_f = data['saliency_freelook'][level]
            p_q = data['saliency_scoring'][level]
            a = artifact_maps_nr[(c, level)]
            if p_f is None or p_q is None:
                continue

            X, pf_small, a_small = make_pixel_features(p_f, a, SZ)
            pq_small = cv2.resize(p_q.astype(np.float32), (SZ, SZ),
                                  interpolation=cv2.INTER_LINEAR)
            pq_small = normalize_to_prob(pq_small).astype(np.float32)

            prep[(c, level)] = {
                'X': X,
                'y': pq_small.flatten(),
                'p_f_full': p_f,
                'p_q_full': p_q,
                'a_full': a,
            }

    logger.info(f"Prepared {len(prep)} R2 samples at {SZ}×{SZ}")
    logger.info(f"  Pixels per sample: {SZ*SZ}, Features per pixel: 4 [P_F, A, x, y]")

    # LOCO evaluation
    rows = []
    ridge_weights_all = []
    t_loco = time.time()

    for fold_idx, test_c in enumerate(contents):
        if fold_idx % 10 == 0:
            elapsed = time.time() - t_loco
            logger.info(f"  LOCO fold {fold_idx+1}/40... ({elapsed:.0f}s elapsed)")

        # Build training data (all contents except test)
        X_train_list, y_train_list = [], []
        for key, val in prep.items():
            if key[0] == test_c:
                continue
            X_train_list.append(val['X'])
            y_train_list.append(val['y'])

        X_train = np.vstack(X_train_list)
        y_train = np.concatenate(y_train_list)

        # ── LB1: Ridge regression ──
        ridge = Ridge(alpha=1.0, fit_intercept=True)
        ridge.fit(X_train, y_train)
        ridge_weights_all.append(ridge.coef_.copy())

        # ── LB2: MLP regressor ──
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        mlp = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation='relu',
            solver='adam',
            max_iter=100,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=5,
            batch_size=min(2048, len(X_train)),
        )
        mlp.fit(X_train_s, y_train)

        # Evaluate on held-out content
        for level in all_data[test_c]['levels']:
            key = (test_c, level)
            if key not in prep:
                continue
            val = prep[key]

            X_test = val['X']
            p_q_full = val['p_q_full']
            orig_h, orig_w = p_q_full.shape[:2]

            # Ridge prediction → upsample → normalize
            pred_r = ridge.predict(X_test).reshape(SZ, SZ)
            pred_r_full = cv2.resize(pred_r.astype(np.float32),
                                     (orig_w, orig_h),
                                     interpolation=cv2.INTER_LINEAR)
            pred_r_prob = normalize_to_prob(pred_r_full)

            # MLP prediction → upsample → normalize
            X_test_s = scaler.transform(X_test)
            pred_m = mlp.predict(X_test_s).reshape(SZ, SZ)
            pred_m_full = cv2.resize(pred_m.astype(np.float32),
                                     (orig_w, orig_h),
                                     interpolation=cv2.INTER_LINEAR)
            pred_m_prob = normalize_to_prob(pred_m_full)

            rows.append({
                'content': test_c, 'level': level,
                'ridge_cc':  SaliencyMetrics.pearson_correlation(pred_r_prob, p_q_full),
                'ridge_jsd': SaliencyMetrics.jensen_shannon_divergence(pred_r_prob, p_q_full),
                'mlp_cc':    SaliencyMetrics.pearson_correlation(pred_m_prob, p_q_full),
                'mlp_jsd':   SaliencyMetrics.jensen_shannon_divergence(pred_m_prob, p_q_full),
            })

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / 'learning_baselines_r2.csv', index=False)

    # Ridge weight analysis
    w_arr = np.array(ridge_weights_all)  # shape (40, 4)
    elapsed = time.time() - t_loco

    logger.info(f"\nLearning Baselines on R2 ({len(df)} samples, {elapsed:.0f}s):")
    logger.info(f"  LB1 (Ridge)  CC={df['ridge_cc'].mean():.4f}±{df['ridge_cc'].std():.4f}"
                f"  JSD={df['ridge_jsd'].mean():.4f}±{df['ridge_jsd'].std():.4f}")
    logger.info(f"  LB2 (MLP)    CC={df['mlp_cc'].mean():.4f}±{df['mlp_cc'].std():.4f}"
                f"  JSD={df['mlp_jsd'].mean():.4f}±{df['mlp_jsd'].std():.4f}")
    logger.info(f"\n  Ridge learned weights (mean ± std across 40 LOCO folds):")
    logger.info(f"    w_PF  = {w_arr[:,0].mean():.4f} ± {w_arr[:,0].std():.4f}  (cf. SC-TAS α = 1.0)")
    logger.info(f"    w_A   = {w_arr[:,1].mean():.4f} ± {w_arr[:,1].std():.4f}  (cf. SC-TAS β = 0.3)")
    logger.info(f"    w_x   = {w_arr[:,2].mean():.6f} ± {w_arr[:,2].std():.6f}")
    logger.info(f"    w_y   = {w_arr[:,3].mean():.6f} ± {w_arr[:,3].std():.6f}")
    logger.info(f"    bias  = (from last fold) {ridge.intercept_:.6f}")

    return df, w_arr


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 4: Learning Baselines Zero-Shot on INT
# ═══════════════════════════════════════════════════════════════════════════════
def stage4_baselines_zeroshot_int(int_data, all_data, artifact_maps_nr, contents):
    """Train final Ridge + MLP on ALL R2, apply zero-shot to INT."""
    logger.info("\n" + "═" * 80)
    logger.info("STAGE 4: Learning Baselines → Zero-Shot on INT")
    logger.info("═" * 80)

    from sklearn.linear_model import Ridge
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler

    SZ = LB_RESIZE
    t = time.time()

    # Build FULL R2 training set
    X_all, y_all = [], []
    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            p_f = data['saliency_freelook'][level]
            p_q = data['saliency_scoring'][level]
            a = artifact_maps_nr[(c, level)]
            if p_f is None or p_q is None:
                continue
            X, _, _ = make_pixel_features(p_f, a, SZ)
            pq_s = cv2.resize(p_q.astype(np.float32), (SZ, SZ),
                              interpolation=cv2.INTER_LINEAR)
            pq_s = normalize_to_prob(pq_s).astype(np.float32)
            X_all.append(X)
            y_all.append(pq_s.flatten())

    X_all = np.vstack(X_all)
    y_all = np.concatenate(y_all)
    logger.info(f"Training on ALL R2: {X_all.shape[0]:,} pixel samples, {X_all.shape[1]} features")

    # Train final Ridge
    ridge_final = Ridge(alpha=1.0, fit_intercept=True)
    ridge_final.fit(X_all, y_all)
    logger.info(f"  Final Ridge weights: w_PF={ridge_final.coef_[0]:.4f}, "
                f"w_A={ridge_final.coef_[1]:.4f}, bias={ridge_final.intercept_:.6f}")

    # Train final MLP
    scaler_final = StandardScaler()
    X_all_s = scaler_final.fit_transform(X_all)
    mlp_final = MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation='relu', solver='adam',
        max_iter=100, random_state=42,
        early_stopping=True, validation_fraction=0.1,
        n_iter_no_change=5, batch_size=min(2048, len(X_all)),
    )
    mlp_final.fit(X_all_s, y_all)
    logger.info(f"  Final MLP trained ({mlp_final.n_iter_} iterations)")

    # Evaluate on INT
    rows = []
    for item in int_data:
        p_f = item['prior']
        p_gt = item['saliency_gt']
        a_nr = item['artifact_nr']
        h, w = item['image_shape']

        X_int, _, _ = make_pixel_features(p_f, a_nr, SZ)

        # Ridge
        pred_r = ridge_final.predict(X_int).reshape(SZ, SZ)
        pred_r_full = cv2.resize(pred_r.astype(np.float32), (w, h),
                                 interpolation=cv2.INTER_LINEAR)
        pred_r_prob = normalize_to_prob(pred_r_full)

        # MLP
        X_int_s = scaler_final.transform(X_int)
        pred_m = mlp_final.predict(X_int_s).reshape(SZ, SZ)
        pred_m_full = cv2.resize(pred_m.astype(np.float32), (w, h),
                                 interpolation=cv2.INTER_LINEAR)
        pred_m_prob = normalize_to_prob(pred_m_full)

        rows.append({
            'content': item['content'],
            'dist_type': item['dist_type'],
            'dist_level': item['dist_level'],
            'ridge_cc':  SaliencyMetrics.pearson_correlation(pred_r_prob, p_gt),
            'ridge_jsd': SaliencyMetrics.jensen_shannon_divergence(pred_r_prob, p_gt),
            'mlp_cc':    SaliencyMetrics.pearson_correlation(pred_m_prob, p_gt),
            'mlp_jsd':   SaliencyMetrics.jensen_shannon_divergence(pred_m_prob, p_gt),
        })

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / 'learning_baselines_int.csv', index=False)

    logger.info(f"\nLearning Baselines on INT ({len(df)} stimuli, {time.time()-t:.0f}s):")
    logger.info(f"  LB1 (Ridge)  CC={df['ridge_cc'].mean():.4f}±{df['ridge_cc'].std():.4f}"
                f"  JSD={df['ridge_jsd'].mean():.4f}±{df['ridge_jsd'].std():.4f}")
    logger.info(f"  LB2 (MLP)    CC={df['mlp_cc'].mean():.4f}±{df['mlp_cc'].std():.4f}"
                f"  JSD={df['mlp_jsd'].mean():.4f}±{df['mlp_jsd'].std():.4f}")

    # By distortion type
    for dt in ['jpeg', 'blur', 'noise']:
        sub = df[df['dist_type'] == dt]
        if len(sub) > 0:
            logger.info(f"    {dt.upper()}: Ridge CC={sub['ridge_cc'].mean():.4f}"
                        f"  JSD={sub['ridge_jsd'].mean():.4f}"
                        f"  |  MLP CC={sub['mlp_cc'].mean():.4f}"
                        f"  JSD={sub['mlp_jsd'].mean():.4f}")

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 5: Summary Tables + Statistical Tests
# ═══════════════════════════════════════════════════════════════════════════════
def stage5_summary_and_stats(df_r1, df_int, df_lb_r2, df_lb_int):
    """Generate Table-G1 (cross-dataset summary) and statistical tests."""
    logger.info("\n" + "═" * 80)
    logger.info("STAGE 5: Summary Tables & Statistical Tests")
    logger.info("═" * 80)

    # ── Table-G1: Cross-Dataset Performance Comparison ──
    g1_rows = []

    # Load existing R2 main results for comparison
    r2_path = PROJECT_ROOT / 'results' / 'revised_real' / 'rq2_prediction_all.csv'
    df_r2 = None
    if r2_path.exists():
        df_r2 = pd.read_csv(r2_path)
        r2_methods = {
            'Prior only':    ('freelook_cc',   'freelook_jsd'),
            'Artifact NR':   ('artifact_nr_cc', 'artifact_nr_jsd'),
            'Fixed mix NR':  ('mixture_nr_cc',  'mixture_nr_jsd'),
            'SC-TAS NR':     ('tas_nr_cc',      'tas_nr_jsd'),
            'SC-TAS FR':     ('tas_fr_cc',      'tas_fr_jsd'),
        }
        for mname, (cc_col, jsd_col) in r2_methods.items():
            g1_rows.append({
                'Dataset': 'R2', 'Method': mname,
                'CC_mean': float(df_r2[cc_col].mean()),
                'CC_std': float(df_r2[cc_col].std()),
                'JSD_mean': float(df_r2[jsd_col].mean()),
                'JSD_std': float(df_r2[jsd_col].std()),
                'n': len(df_r2),
            })
        # Learning baselines on R2
        for bname, cc_col, jsd_col in [
            ('LB1 (Ridge)', 'ridge_cc', 'ridge_jsd'),
            ('LB2 (MLP)',   'mlp_cc',   'mlp_jsd'),
        ]:
            g1_rows.append({
                'Dataset': 'R2', 'Method': bname,
                'CC_mean': float(df_lb_r2[cc_col].mean()),
                'CC_std': float(df_lb_r2[cc_col].std()),
                'JSD_mean': float(df_lb_r2[jsd_col].mean()),
                'JSD_std': float(df_lb_r2[jsd_col].std()),
                'n': len(df_lb_r2),
            })
    else:
        logger.warning("R2 main results not found — Table-G1 will be partial")

    # INT results (SC-TAS variants)
    int_methods = [
        ('Prior only',   'prior_cc',       'prior_jsd'),
        ('Artifact NR',  'artifact_nr_cc', 'artifact_nr_jsd'),
        ('Fixed mix NR', 'mixture_nr_cc',  'mixture_nr_jsd'),
        ('SC-TAS NR',    'sctas_nr_cc',    'sctas_nr_jsd'),
        ('SC-TAS FR',    'sctas_fr_cc',    'sctas_fr_jsd'),
    ]
    for mname, cc_col, jsd_col in int_methods:
        vals_cc = df_int[cc_col].dropna()
        vals_jsd = df_int[jsd_col].dropna()
        if len(vals_cc) > 0:
            g1_rows.append({
                'Dataset': 'INT', 'Method': mname,
                'CC_mean': float(vals_cc.mean()),
                'CC_std': float(vals_cc.std()),
                'JSD_mean': float(vals_jsd.mean()),
                'JSD_std': float(vals_jsd.std()),
                'n': int(len(vals_cc)),
            })

    # Learning baselines on INT
    for bname, cc_col, jsd_col in [
        ('LB1 (Ridge)', 'ridge_cc', 'ridge_jsd'),
        ('LB2 (MLP)',   'mlp_cc',   'mlp_jsd'),
    ]:
        g1_rows.append({
            'Dataset': 'INT', 'Method': bname,
            'CC_mean': float(df_lb_int[cc_col].mean()),
            'CC_std': float(df_lb_int[cc_col].std()),
            'JSD_mean': float(df_lb_int[jsd_col].mean()),
            'JSD_std': float(df_lb_int[jsd_col].std()),
            'n': len(df_lb_int),
        })

    # R1 stability (different framing: CC against prior, not GT)
    g1_rows.append({
        'Dataset': 'R1 (stability)', 'Method': 'SC-TAS NR',
        'CC_mean': float(df_r1['sctas_cc_vs_prior'].mean()),
        'CC_std': float(df_r1['sctas_cc_vs_prior'].std()),
        'JSD_mean': float(df_r1['sctas_jsd_vs_prior'].mean()),
        'JSD_std': float(df_r1['sctas_jsd_vs_prior'].std()),
        'n': len(df_r1),
    })
    g1_rows.append({
        'Dataset': 'R1 (stability)', 'Method': 'Fixed mix NR',
        'CC_mean': float(df_r1['mixture_cc_vs_prior'].mean()),
        'CC_std': float(df_r1['mixture_cc_vs_prior'].std()),
        'JSD_mean': float(df_r1['mixture_jsd_vs_prior'].mean()),
        'JSD_std': float(df_r1['mixture_jsd_vs_prior'].std()),
        'n': len(df_r1),
    })

    df_g1 = pd.DataFrame(g1_rows)
    df_g1.to_csv(RESULTS_DIR / 'table_g1_crossdataset.csv', index=False)

    # Pretty-print Table-G1
    logger.info("\n  ════════════════ TABLE G1: Cross-Dataset Summary ════════════════")
    logger.info(f"  {'Dataset':17s} | {'Method':14s} | {'CC':18s} | {'JSD':18s} | n")
    logger.info("  " + "─" * 80)
    for _, row in df_g1.iterrows():
        logger.info(f"  {row['Dataset']:17s} | {row['Method']:14s} | "
                     f"{row['CC_mean']:.4f}±{row['CC_std']:.4f}      | "
                     f"{row['JSD_mean']:.4f}±{row['JSD_std']:.4f}      | {int(row['n'])}")

    # ── Statistical tests on INT ──
    logger.info("\n  ════════════════ Statistical Tests (INT) ════════════════")

    # Merge INT SC-TAS results with LB results for paired tests
    df_int_merged = df_int.merge(
        df_lb_int[['content', 'dist_type', 'dist_level', 'ridge_jsd', 'ridge_cc',
                    'mlp_jsd', 'mlp_cc']],
        on=['content', 'dist_type', 'dist_level'],
        how='inner'
    )

    test_pairs = [
        ('SC-TAS NR vs Prior only',     'sctas_nr_jsd', 'prior_jsd'),
        ('SC-TAS NR vs Fixed-mix NR',   'sctas_nr_jsd', 'mixture_nr_jsd'),
        ('SC-TAS NR vs LB1 (Ridge)',    'sctas_nr_jsd', 'ridge_jsd'),
        ('SC-TAS NR vs LB2 (MLP)',      'sctas_nr_jsd', 'mlp_jsd'),
        ('SC-TAS NR vs SC-TAS FR',      'sctas_nr_jsd', 'sctas_fr_jsd'),
    ]

    stat_rows = []
    p_values = []
    for comp_name, col_a, col_b in test_pairs:
        vals_a = df_int_merged[col_a].dropna().values
        vals_b = df_int_merged[col_b].dropna().values
        # Ensure same length
        n_min = min(len(vals_a), len(vals_b))
        vals_a, vals_b = vals_a[:n_min], vals_b[:n_min]

        try:
            stat_w, p_w = wilcoxon(vals_a, vals_b)
        except Exception:
            stat_w, p_w = np.nan, 1.0
        try:
            stat_t, p_t = ttest_rel(vals_a, vals_b)
        except Exception:
            stat_t, p_t = np.nan, 1.0

        d = cohens_d(vals_a, vals_b)
        diff = vals_a - vals_b
        ci = bootstrap_ci(diff)

        stat_rows.append({
            'Comparison': comp_name,
            'Wilcoxon_p': float(p_w),
            'ttest_p': float(p_t),
            'Cohens_d': d,
            'diff_mean': float(diff.mean()),
            'CI_lo': ci[0], 'CI_hi': ci[2],
            'n': n_min,
        })
        p_values.append(p_w)
        logger.info(f"  {comp_name:30s}  Δ={diff.mean():.4f}  p={p_w:.2e}  d={d:.3f}  n={n_min}")

    # Holm-Bonferroni correction
    sorted_idx = np.argsort(p_values)
    n_tests = len(p_values)
    for rank, idx in enumerate(sorted_idx):
        corrected_alpha = 0.05 / (n_tests - rank)
        stat_rows[idx]['holm_sig'] = bool(p_values[idx] < corrected_alpha)

    df_stats = pd.DataFrame(stat_rows)
    df_stats.to_csv(RESULTS_DIR / 'statistical_tests_int.csv', index=False)

    # ── Performance drop R2 → INT ──
    if df_r2 is not None and 'tas_nr_cc' in df_r2.columns:
        logger.info("\n  ════════════════ Performance Drop R2 → INT ════════════════")
        r2_cc = df_r2['tas_nr_cc'].mean()
        r2_jsd = df_r2['tas_nr_jsd'].mean()
        int_cc = df_int['sctas_nr_cc'].mean()
        int_jsd = df_int['sctas_nr_jsd'].mean()
        logger.info(f"  SC-TAS NR:  R2 CC={r2_cc:.4f} → INT CC={int_cc:.4f}  (Δ={int_cc - r2_cc:+.4f})")
        logger.info(f"  SC-TAS NR:  R2 JSD={r2_jsd:.4f} → INT JSD={int_jsd:.4f}  (Δ={int_jsd - r2_jsd:+.4f})")

        # Learning baselines drop
        r2_ridge_cc = df_lb_r2['ridge_cc'].mean()
        int_ridge_cc = df_lb_int['ridge_cc'].mean()
        r2_mlp_cc = df_lb_r2['mlp_cc'].mean()
        int_mlp_cc = df_lb_int['mlp_cc'].mean()
        logger.info(f"  LB1 Ridge:  R2 CC={r2_ridge_cc:.4f} → INT CC={int_ridge_cc:.4f}  (Δ={int_ridge_cc - r2_ridge_cc:+.4f})")
        logger.info(f"  LB2 MLP:    R2 CC={r2_mlp_cc:.4f} → INT CC={int_mlp_cc:.4f}  (Δ={int_mlp_cc - r2_mlp_cc:+.4f})")

    return df_g1


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    logger.info("=" * 80)
    logger.info("CROSS-DATASET GENERALIZATION + LEARNING BASELINES")
    logger.info(f"Start: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # ── Verify directories ──
    for name, path in [('R1', R1_ROOT), ('INT', INT_ROOT),
                        ('R2', config.DATA_ROOT)]:
        if not path.exists():
            logger.error(f"Dataset directory not found: {name} → {path}")
            sys.exit(1)
    logger.info("All dataset directories verified ✓")

    # ── Initialize ──
    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)
    sctas_nr = SCTAS(alpha=1.0, beta=0.3, tau=0.83, eta=0.9)
    sctas_fr = SCTAS(alpha=1.0, beta=0.5, tau=0.83, eta=0.9)

    # ── Load all datasets ──
    contents, all_data, artifact_nr, artifact_fr = load_all_r2(loader, artifact_gen)

    r1_data = load_all_r1(artifact_gen)
    r1_priors = {item['content']: item['saliency'] for item in r1_data}

    int_data = load_all_int(artifact_gen, r1_priors)

    logger.info(f"\nData loading complete in {time.time()-t0:.1f}s")
    logger.info(f"  R2:  {len(contents)} contents × 4 levels = {len(contents)*4} stimuli")
    logger.info(f"  R1:  {len(r1_data)} pristine images")
    logger.info(f"  INT: {len(int_data)} distorted stimuli")
    logger.info(f"  R1↔INT content overlap: {sorted(set(d['content'] for d in int_data) & set(r1_priors.keys()))}")

    # ── Run experiment stages ──
    df_r1 = stage1_r1_stability(r1_data, sctas_nr)

    df_int = stage2_int_crossdataset(int_data, sctas_nr, sctas_fr)

    df_lb_r2, ridge_weights = stage3_learning_baselines_r2(
        all_data, artifact_nr, contents)

    df_lb_int = stage4_baselines_zeroshot_int(
        int_data, all_data, artifact_nr, contents)

    df_g1 = stage5_summary_and_stats(df_r1, df_int, df_lb_r2, df_lb_int)

    # ── Save comprehensive JSON ──
    runtime = time.time() - t0
    results = {
        'timestamp': datetime.now().isoformat(),
        'runtime_seconds': runtime,
        'datasets': {
            'R2': {'n_contents': len(contents), 'n_stimuli': len(contents) * 4},
            'R1': {'n_images': len(r1_data)},
            'INT': {'n_stimuli': len(int_data),
                    'by_type': {dt: sum(1 for d in int_data if d['dist_type'] == dt)
                                for dt in ['jpeg', 'blur', 'noise']}},
        },
        'r1_stability': {
            'n': len(df_r1),
            'sctas_cc_vs_prior_mean': float(df_r1['sctas_cc_vs_prior'].mean()),
            'sctas_cc_vs_prior_std': float(df_r1['sctas_cc_vs_prior'].std()),
            'sctas_jsd_vs_prior_mean': float(df_r1['sctas_jsd_vs_prior'].mean()),
            'sctas_jsd_vs_prior_std': float(df_r1['sctas_jsd_vs_prior'].std()),
            'mixture_cc_vs_prior_mean': float(df_r1['mixture_cc_vs_prior'].mean()),
        },
        'int_crossdataset': {
            'n': len(df_int),
            'overall': {
                'sctas_nr_cc': float(df_int['sctas_nr_cc'].mean()),
                'sctas_nr_jsd': float(df_int['sctas_nr_jsd'].mean()),
                'prior_cc': float(df_int['prior_cc'].mean()),
                'prior_jsd': float(df_int['prior_jsd'].mean()),
            },
            'by_distortion_type': {},
        },
        'learning_baselines_r2': {
            'n': len(df_lb_r2),
            'ridge_cc': float(df_lb_r2['ridge_cc'].mean()),
            'ridge_jsd': float(df_lb_r2['ridge_jsd'].mean()),
            'mlp_cc': float(df_lb_r2['mlp_cc'].mean()),
            'mlp_jsd': float(df_lb_r2['mlp_jsd'].mean()),
            'ridge_weights_mean': ridge_weights.mean(axis=0).tolist(),
            'ridge_weights_std': ridge_weights.std(axis=0).tolist(),
        },
        'learning_baselines_int': {
            'n': len(df_lb_int),
            'ridge_cc': float(df_lb_int['ridge_cc'].mean()),
            'ridge_jsd': float(df_lb_int['ridge_jsd'].mean()),
            'mlp_cc': float(df_lb_int['mlp_cc'].mean()),
            'mlp_jsd': float(df_lb_int['mlp_jsd'].mean()),
        },
    }

    # INT by distortion type
    for dt in ['jpeg', 'blur', 'noise']:
        sub = df_int[df_int['dist_type'] == dt]
        sub_lb = df_lb_int[df_lb_int['dist_type'] == dt]
        if len(sub) > 0:
            results['int_crossdataset']['by_distortion_type'][dt] = {
                'n': len(sub),
                'sctas_nr_cc': float(sub['sctas_nr_cc'].mean()),
                'sctas_nr_jsd': float(sub['sctas_nr_jsd'].mean()),
                'prior_cc': float(sub['prior_cc'].mean()),
                'prior_jsd': float(sub['prior_jsd'].mean()),
            }
            if len(sub_lb) > 0:
                results['int_crossdataset']['by_distortion_type'][dt].update({
                    'ridge_cc': float(sub_lb['ridge_cc'].mean()),
                    'ridge_jsd': float(sub_lb['ridge_jsd'].mean()),
                    'mlp_cc': float(sub_lb['mlp_cc'].mean()),
                    'mlp_jsd': float(sub_lb['mlp_jsd'].mean()),
                })

    with open(RESULTS_DIR / 'comprehensive_results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\nAll results saved to {RESULTS_DIR}/")
    logger.info(f"Output files:")
    for f in sorted(RESULTS_DIR.glob('*')):
        logger.info(f"  {f.name}")
    logger.info(f"\nTotal runtime: {runtime:.1f}s ({runtime/60:.1f} min)")
    logger.info("\n" + "=" * 80)
    logger.info("✓ CROSS-DATASET + LEARNING BASELINES EXPERIMENT COMPLETED")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
