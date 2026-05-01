#!/usr/bin/env python3
"""
M5 Sensitivity Analysis: Center-Bias Prior Experiment
=====================================================

Quantifies how much SC-TAS degrades when the ground-truth free-viewing FDM
is replaced by a generic center-bias Gaussian prior.

This directly addresses the assumption that a free-viewing FDM is available
at test time. If the degradation is small, the method is robust to prior
quality; if large, a good saliency predictor is needed in practice.

Conditions evaluated:
  1. GT Prior:       True free-viewing FDM (P^F)         → SC-TAS NR
  2. Center-bias:    Isotropic Gaussian center-bias       → SC-TAS NR
  3. Blurred Prior:  Gaussian-blurred P^F (σ=30px)        → SC-TAS NR
  4. Uniform Prior:  Flat/uniform map                     → SC-TAS NR
  5. Baselines:      Each prior alone (no fusion)

Author: Automated pipeline for CGI 2026
"""

import sys
import os
import json
import time
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from scipy.stats import sem
from scipy.spatial.distance import jensenshannon
from scipy.ndimage import gaussian_filter

warnings.filterwarnings('ignore')

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics

RESULTS_DIR = PROJECT_ROOT / 'results' / 'centerbias_sensitivity'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class SCTAS:
    """SC-TAS: P_hat = N(alpha * P_F + beta * A), with CC-threshold constraint."""
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


def normalize_to_prob(m):
    """Normalize map to probability distribution."""
    m = np.maximum(m, 0).astype(np.float64)
    total = np.sum(m) + 1e-12
    return m / total


def make_center_bias(h, w, sigma_frac=0.20):
    """Create isotropic Gaussian center-bias map.
    sigma_frac: fraction of image diagonal used as Gaussian sigma.
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = h / 2.0, w / 2.0
    diag = np.sqrt(h**2 + w**2)
    sigma = sigma_frac * diag
    g = np.exp(-((xx - cx)**2 + (yy - cy)**2) / (2 * sigma**2))
    return normalize_to_prob(g)


def make_blurred_prior(p_free, sigma_px=30):
    """Blur the GT free-viewing FDM with Gaussian filter."""
    blurred = gaussian_filter(p_free.astype(np.float64), sigma=sigma_px)
    return normalize_to_prob(blurred)


def make_uniform(h, w):
    """Uniform prior."""
    return np.ones((h, w), dtype=np.float64) / (h * w)


def compute_metrics(pred, gt):
    """Compute CC and JSD between prediction and ground truth."""
    cc = SaliencyMetrics.pearson_correlation(pred, gt)
    jsd = SaliencyMetrics.jensen_shannon_divergence(pred, gt)
    return cc, jsd


def main():
    t0 = time.time()
    print("=" * 80)
    print("M5 SENSITIVITY ANALYSIS: CENTER-BIAS PRIOR EXPERIMENT")
    print(f"Start: {datetime.now().isoformat()}")
    print("=" * 80)

    # Load data
    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)
    contents = loader.get_unique_contents()
    print(f"Dataset: {len(contents)} contents")

    print("Loading all data...")
    all_data = {}
    for c in contents:
        all_data[c] = loader.get_data_for_content(c, preprocess_saliency=True)
    print(f"Data loaded in {time.time()-t0:.1f}s")

    # Pre-compute NR artifact maps
    print("Computing NR artifact maps...")
    artifact_maps_nr = {}
    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            img = data['images'][level]
            key = (c, level)
            a_nr = artifact_gen.compute_nr_artifact(
                img, use_blockiness=True, use_dct=True, use_ringing=True
            )
            artifact_maps_nr[key] = artifact_gen.normalize_artifact_to_probability(a_nr)
    print("Artifact maps computed.")

    # SC-TAS NR model
    sctas_nr = SCTAS(alpha=1.0, beta=0.3, tau=0.83, eta=0.9)

    rows = []

    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            p_free = data['saliency_freelook'][level]
            p_score = data['saliency_scoring'][level]
            if p_free is None or p_score is None:
                continue

            key = (c, level)
            a_nr = artifact_maps_nr[key]
            h, w = p_free.shape[:2]

            # Ensure probability distributions
            p_free_prob = normalize_to_prob(p_free)
            p_score_prob = normalize_to_prob(p_score)

            # ── Create alternative priors ──
            p_center = make_center_bias(h, w, sigma_frac=0.20)
            p_blurred = make_blurred_prior(p_free_prob, sigma_px=30)
            p_uniform = make_uniform(h, w)

            row = {'content': c, 'level': level}

            # ── Condition 1: GT Prior → SC-TAS NR ──
            pred_gt = sctas_nr.predict(p_free_prob, a_nr)
            cc_gt, jsd_gt = compute_metrics(pred_gt, p_score_prob)
            row['cc_gt_sctas'] = cc_gt
            row['jsd_gt_sctas'] = jsd_gt

            # ── Condition 1b: GT Prior alone (no fusion) ──
            cc_gt_alone, jsd_gt_alone = compute_metrics(p_free_prob, p_score_prob)
            row['cc_gt_alone'] = cc_gt_alone
            row['jsd_gt_alone'] = jsd_gt_alone

            # ── Condition 2: Center-bias → SC-TAS NR ──
            pred_cb = sctas_nr.predict(p_center, a_nr)
            cc_cb, jsd_cb = compute_metrics(pred_cb, p_score_prob)
            row['cc_cb_sctas'] = cc_cb
            row['jsd_cb_sctas'] = jsd_cb

            # ── Condition 2b: Center-bias alone ──
            cc_cb_alone, jsd_cb_alone = compute_metrics(p_center, p_score_prob)
            row['cc_cb_alone'] = cc_cb_alone
            row['jsd_cb_alone'] = jsd_cb_alone

            # ── Condition 3: Blurred Prior → SC-TAS NR ──
            pred_blur = sctas_nr.predict(p_blurred, a_nr)
            cc_blur, jsd_blur = compute_metrics(pred_blur, p_score_prob)
            row['cc_blur_sctas'] = cc_blur
            row['jsd_blur_sctas'] = jsd_blur

            # ── Condition 3b: Blurred prior alone ──
            cc_blur_alone, jsd_blur_alone = compute_metrics(p_blurred, p_score_prob)
            row['cc_blur_alone'] = cc_blur_alone
            row['jsd_blur_alone'] = jsd_blur_alone

            # ── Condition 4: Uniform → SC-TAS NR ──
            pred_uni = sctas_nr.predict(p_uniform, a_nr)
            cc_uni, jsd_uni = compute_metrics(pred_uni, p_score_prob)
            row['cc_uni_sctas'] = cc_uni
            row['jsd_uni_sctas'] = jsd_uni

            # ── Condition 4b: Uniform alone ──
            cc_uni_alone, jsd_uni_alone = compute_metrics(p_uniform, p_score_prob)
            row['cc_uni_alone'] = cc_uni_alone
            row['jsd_uni_alone'] = jsd_uni_alone

            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / 'centerbias_sensitivity.csv', index=False)

    # ── Summary ──
    print("\n" + "=" * 80)
    print("SUMMARY: Prior Quality Sensitivity Analysis (160 R2 samples)")
    print("=" * 80)
    print(f"{'Condition':<30} {'CC (mean±std)':<22} {'JSD (mean±std)':<22}")
    print("-" * 74)

    conditions = [
        ('GT Prior alone',        'cc_gt_alone',    'jsd_gt_alone'),
        ('GT Prior → SC-TAS NR',  'cc_gt_sctas',    'jsd_gt_sctas'),
        ('Center-bias alone',     'cc_cb_alone',    'jsd_cb_alone'),
        ('Center-bias → SC-TAS',  'cc_cb_sctas',    'jsd_cb_sctas'),
        ('Blurred Prior alone',   'cc_blur_alone',  'jsd_blur_alone'),
        ('Blurred → SC-TAS',      'cc_blur_sctas',  'jsd_blur_sctas'),
        ('Uniform alone',         'cc_uni_alone',   'jsd_uni_alone'),
        ('Uniform → SC-TAS',      'cc_uni_sctas',   'jsd_uni_sctas'),
    ]

    summary = {}
    for name, cc_col, jsd_col in conditions:
        cc_mean = df[cc_col].mean()
        cc_std = df[cc_col].std()
        jsd_mean = df[jsd_col].mean()
        jsd_std = df[jsd_col].std()
        print(f"{name:<30} {cc_mean:.3f} ± {cc_std:.3f}       {jsd_mean:.3f} ± {jsd_std:.3f}")
        summary[name] = {
            'cc_mean': round(float(cc_mean), 4),
            'cc_std': round(float(cc_std), 4),
            'jsd_mean': round(float(jsd_mean), 4),
            'jsd_std': round(float(jsd_std), 4),
        }

    # Compute degradation from GT prior
    print("\n" + "=" * 80)
    print("DEGRADATION: SC-TAS CC drop from GT prior to alternative priors")
    print("=" * 80)
    gt_cc = df['cc_gt_sctas'].mean()
    for name, cc_col, _ in conditions:
        if 'sctas' in cc_col:
            delta = df[cc_col].mean() - gt_cc
            pct = 100 * delta / gt_cc if gt_cc != 0 else 0
            print(f"  {name}: ΔCC = {delta:+.4f} ({pct:+.1f}%)")

    # Save summary
    with open(RESULTS_DIR / 'centerbias_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"Results saved to {RESULTS_DIR}")


if __name__ == '__main__':
    main()
