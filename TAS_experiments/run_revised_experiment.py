#!/usr/bin/env python3
"""
Revised Experiment Execution — REAL COMPUTATION
CGI 2026 / TVC Journal Track

This script implements the full experiment pipeline defined in revisedexperiment.md,
calling the real computation modules in src/.

Stages:
  1. RQ1: Task shift analysis (CC, JSD, entropy, centroid between FreeLook and Scoring)
  2. RQ2-FR: TAS prediction with Full-Reference artifact maps (LOCO)
  3. RQ2-NR: TAS prediction with No-Reference artifact maps (LOCO)
  4. RQ3: Background distraction metric (Dbg)
  5. Mechanism validation: FR vs NR consistency + distortion correlation
  6. Diagnostic parameter grid on a high-distortion subset
  7. Statistical analysis: Wilcoxon, Cohen's d, Bootstrap CI, Holm-Bonferroni
  8. Content-level best/median/worst analysis
  9. Stability-threshold diagnostic

The final full-R2 parameter sensitivity and stability stress test reported in
the paper are implemented in run_ablation_sensitivity_experiments.py. R1/INT
evaluation is implemented in run_crossdataset_baselines.py.

"""

import sys
import os
import json
import time
import logging
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from scipy.stats import sem, wilcoxon, ttest_rel, pearsonr, spearmanr
from scipy.spatial.distance import jensenshannon

warnings.filterwarnings('ignore')

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics
from sctas import SCTAS

# ─── Logging ────────────────────────────────────────────────────────────────────
RESULTS_DIR = config.RESULTS_DIR / 'revised_real'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

log_file = RESULTS_DIR / 'experiment.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ─── SC-TAS: Paper method (Eq.7 of the paper) ──────────────────────────────────
# ─── Helper functions ───────────────────────────────────────────────────────────
def normalize_to_prob(m: np.ndarray) -> np.ndarray:
    """Normalize map to probability distribution."""
    m = np.maximum(m, 0).astype(np.float64)
    s = np.sum(m) + 1e-12
    return m / s


def compute_dbg(p: np.ndarray) -> float:
    """Background mass: probability outside central 50% window."""
    h, w = p.shape
    ch, cw = h // 4, w // 4
    mask = np.ones_like(p)
    mask[ch:h-ch, cw:w-cw] = 0  # central half is 0
    return float(np.sum(p * mask))


def bootstrap_ci(values, n_boot=2000, ci=0.95, seed=42):
    """Bootstrap confidence interval."""
    rng = np.random.RandomState(seed)
    vals = np.array(values)
    n = len(vals)
    if n < 2:
        return vals.mean(), vals.mean(), vals.mean()
    boot_means = np.array([rng.choice(vals, n, replace=True).mean() for _ in range(n_boot)])
    lo = np.percentile(boot_means, (1 - ci) / 2 * 100)
    hi = np.percentile(boot_means, (1 + ci) / 2 * 100)
    return float(lo), float(vals.mean()), float(hi)


def cohens_d(x, y):
    """Cohen's d effect size (paired)."""
    diff = np.array(x) - np.array(y)
    return float(diff.mean() / (diff.std(ddof=1) + 1e-12))


# ─── MAIN PIPELINE ──────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    logger.info("=" * 80)
    logger.info("REVISED EXPERIMENT — REAL COMPUTATION")
    logger.info(f"Start time: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # ─── Data loading ───────────────────────────────────────────────────────
    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)
    contents = loader.get_unique_contents()
    logger.info(f"Dataset: {len(contents)} contents, 160 stimuli total")

    # Pre-load all data
    logger.info("Loading all data into memory...")
    all_data = {}
    for c in contents:
        all_data[c] = loader.get_data_for_content(c, preprocess_saliency=True)
    logger.info(f"Data loaded in {time.time()-t0:.1f}s")

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 1: RQ1 — Task Shift Analysis
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 1: RQ1 — Task Shift Analysis")
    logger.info("=" * 80)

    rq1_rows = []
    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            p_free = data['saliency_freelook'][level]
            p_score = data['saliency_scoring'][level]
            if p_free is None or p_score is None:
                continue

            cc = SaliencyMetrics.pearson_correlation(p_free, p_score)
            jsd = SaliencyMetrics.jensen_shannon_divergence(p_free, p_score)
            entropy_free = SaliencyMetrics.entropy(p_free)
            entropy_score = SaliencyMetrics.entropy(p_score)
            cshift = SaliencyMetrics.centroid_shift(p_free, p_score)
            dbg_free = compute_dbg(p_free)
            dbg_score = compute_dbg(p_score)

            rq1_rows.append({
                'content': c, 'level': level,
                'cc': cc, 'jsd': jsd,
                'entropy_free': entropy_free, 'entropy_score': entropy_score,
                'centroid_shift': cshift,
                'dbg_free': dbg_free, 'dbg_score': dbg_score,
            })

    df_rq1 = pd.DataFrame(rq1_rows)
    df_rq1.to_csv(RESULTS_DIR / 'rq1_task_shift.csv', index=False)

    logger.info(f"RQ1: {len(df_rq1)} samples processed")
    logger.info(f"  Mean CC (FreeLook vs Scoring): {df_rq1['cc'].mean():.4f} ± {df_rq1['cc'].std():.4f}")
    logger.info(f"  Mean JSD: {df_rq1['jsd'].mean():.4f} ± {df_rq1['jsd'].std():.4f}")
    logger.info(f"  Mean Dbg (FreeLook): {df_rq1['dbg_free'].mean():.4f}")
    logger.info(f"  Mean Dbg (Scoring): {df_rq1['dbg_score'].mean():.4f}")
    logger.info(f"  Δ Dbg = {(df_rq1['dbg_score'] - df_rq1['dbg_free']).mean():.4f}")

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 2 & 3: RQ2 — LOCO Prediction (FR and NR)
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 2-3: RQ2 — LOCO Saliency Prediction (FR + NR)")
    logger.info("=" * 80)

    # Pre-compute all artifact maps
    logger.info("Computing artifact maps for all 160 stimuli...")
    artifact_maps_fr = {}  # (content, level) -> artifact prob map
    artifact_maps_nr = {}

    for c in contents:
        data = all_data[c]
        # Load original reference for FR
        ref_img = loader.load_original_image(c, color_space='ycrcb')

        for level in data['levels']:
            img = data['images'][level]
            key = (c, level)

            # FR artifact (uses reference)
            if ref_img is not None:
                # Ensure same size
                if ref_img.shape[:2] != img.shape[:2]:
                    import cv2
                    ref_resized = cv2.resize(ref_img, (img.shape[1], img.shape[0]))
                else:
                    ref_resized = ref_img
                a_fr = artifact_gen.compute_fr_artifact(ref_resized, img, use_luminance=True)
            else:
                a_fr = artifact_gen.compute_fr_artifact(img, img, use_luminance=True)
            artifact_maps_fr[key] = artifact_gen.normalize_artifact_to_probability(a_fr)

            # NR artifact (no reference)
            a_nr = artifact_gen.compute_nr_artifact(img, use_blockiness=True, use_dct=True, use_ringing=True)
            artifact_maps_nr[key] = artifact_gen.normalize_artifact_to_probability(a_nr)

    logger.info("Artifact maps computed.")

    # SC-TAS configurations (paper parameters)
    sctas_fr = SCTAS(alpha=1.0, beta=0.5, tau=0.83, eta=0.9)
    sctas_nr = SCTAS(alpha=1.0, beta=0.3, tau=0.83, eta=0.9)

    # LOCO evaluation
    rq2_rows = []
    for fold_idx, test_content in enumerate(contents):
        logger.info(f"LOCO Fold {fold_idx+1}/40: Test={test_content}")

        for level in all_data[test_content]['levels']:
            p_free = all_data[test_content]['saliency_freelook'][level]
            p_score = all_data[test_content]['saliency_scoring'][level]
            if p_free is None or p_score is None:
                continue

            key = (test_content, level)
            a_fr = artifact_maps_fr[key]
            a_nr = artifact_maps_nr[key]

            row = {'content': test_content, 'level': level}

            # ── Method 1: FreeLook prior (baseline) ──
            cc_fl = SaliencyMetrics.pearson_correlation(p_free, p_score)
            jsd_fl = SaliencyMetrics.jensen_shannon_divergence(p_free, p_score)
            row['freelook_cc'] = cc_fl
            row['freelook_jsd'] = jsd_fl

            # ── Method 2: Artifact-only FR ──
            cc_afr = SaliencyMetrics.pearson_correlation(a_fr, p_score)
            jsd_afr = SaliencyMetrics.jensen_shannon_divergence(a_fr, p_score)
            row['artifact_fr_cc'] = cc_afr
            row['artifact_fr_jsd'] = jsd_afr

            # ── Method 3: Artifact-only NR ──
            cc_anr = SaliencyMetrics.pearson_correlation(a_nr, p_score)
            jsd_anr = SaliencyMetrics.jensen_shannon_divergence(a_nr, p_score)
            row['artifact_nr_cc'] = cc_anr
            row['artifact_nr_jsd'] = jsd_anr

            # ── Method 4: Fixed mixture FR: N(0.5*P_F + 0.5*A_FR) ──
            p_mix_fr = normalize_to_prob(0.5 * p_free + 0.5 * a_fr)
            cc_mfr = SaliencyMetrics.pearson_correlation(p_mix_fr, p_score)
            jsd_mfr = SaliencyMetrics.jensen_shannon_divergence(p_mix_fr, p_score)
            row['mixture_fr_cc'] = cc_mfr
            row['mixture_fr_jsd'] = jsd_mfr

            # ── Method 5: Fixed mixture NR: N(0.5*P_F + 0.5*A_NR) ──
            p_mix_nr = normalize_to_prob(0.5 * p_free + 0.5 * a_nr)
            cc_mnr = SaliencyMetrics.pearson_correlation(p_mix_nr, p_score)
            jsd_mnr = SaliencyMetrics.jensen_shannon_divergence(p_mix_nr, p_score)
            row['mixture_nr_cc'] = cc_mnr
            row['mixture_nr_jsd'] = jsd_mnr

            # ── Method 6: SC-TAS FR (paper method) ──
            p_tas_fr = sctas_fr.predict(p_free, a_fr)
            cc_tfr = SaliencyMetrics.pearson_correlation(p_tas_fr, p_score)
            jsd_tfr = SaliencyMetrics.jensen_shannon_divergence(p_tas_fr, p_score)
            row['tas_fr_cc'] = cc_tfr
            row['tas_fr_jsd'] = jsd_tfr

            # ── Method 7: SC-TAS NR (paper method) ──
            p_tas_nr = sctas_nr.predict(p_free, a_nr)
            cc_tnr = SaliencyMetrics.pearson_correlation(p_tas_nr, p_score)
            jsd_tnr = SaliencyMetrics.jensen_shannon_divergence(p_tas_nr, p_score)
            row['tas_nr_cc'] = cc_tnr
            row['tas_nr_jsd'] = jsd_tnr

            # ── Additional metrics: NSS, SIM ──
            row['freelook_nss'] = SaliencyMetrics.nss(p_free, p_score)
            row['tas_nr_nss'] = SaliencyMetrics.nss(p_tas_nr, p_score)
            row['tas_fr_nss'] = SaliencyMetrics.nss(p_tas_fr, p_score)

            rq2_rows.append(row)

    df_rq2 = pd.DataFrame(rq2_rows)
    df_rq2.to_csv(RESULTS_DIR / 'rq2_prediction_all.csv', index=False)
    logger.info(f"RQ2: {len(df_rq2)} samples evaluated across 7 methods")

    # Print summary table
    methods_map = {
        'FreeLook prior': ('freelook_cc', 'freelook_jsd'),
        'Artifact-only (FR)': ('artifact_fr_cc', 'artifact_fr_jsd'),
        'Fixed mixture (FR)': ('mixture_fr_cc', 'mixture_fr_jsd'),
        'TAS FR': ('tas_fr_cc', 'tas_fr_jsd'),
        'Artifact-only (NR)': ('artifact_nr_cc', 'artifact_nr_jsd'),
        'Fixed mixture (NR)': ('mixture_nr_cc', 'mixture_nr_jsd'),
        'TAS NR': ('tas_nr_cc', 'tas_nr_jsd'),
    }

    logger.info("\n--- Main Quantitative Results (Table 1) ---")
    table1_rows = []
    for method_name, (cc_col, jsd_col) in methods_map.items():
        cc_mean = df_rq2[cc_col].mean()
        cc_std = df_rq2[cc_col].std()
        jsd_mean = df_rq2[jsd_col].mean()
        jsd_std = df_rq2[jsd_col].std()
        logger.info(f"  {method_name:25s}  CC={cc_mean:.4f}±{cc_std:.4f}  JSD={jsd_mean:.4f}±{jsd_std:.4f}")
        table1_rows.append({
            'Method': method_name,
            'CC_mean': cc_mean, 'CC_std': cc_std,
            'JSD_mean': jsd_mean, 'JSD_std': jsd_std,
        })

    df_table1 = pd.DataFrame(table1_rows)
    df_table1.to_csv(RESULTS_DIR / 'table1_main_results.csv', index=False)

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 4: RQ3 — Background Distraction
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 4: RQ3 — Background Distraction Analysis")
    logger.info("=" * 80)

    dbg_free_mean = df_rq1['dbg_free'].mean()
    dbg_score_mean = df_rq1['dbg_score'].mean()
    dbg_free_std = df_rq1['dbg_free'].std()
    dbg_score_std = df_rq1['dbg_score'].std()
    dbg_delta = (df_rq1['dbg_score'] - df_rq1['dbg_free']).mean()
    logger.info(f"  Dbg (FreeLook): {dbg_free_mean:.4f} ± {dbg_free_std:.4f}")
    logger.info(f"  Dbg (Scoring):  {dbg_score_mean:.4f} ± {dbg_score_std:.4f}")
    logger.info(f"  Δ Dbg:          {dbg_delta:.4f}")

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 5: Mechanism Validation
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 5: Mechanism Validation (FR vs NR + Distortion Correlation)")
    logger.info("=" * 80)

    fr_nr_corrs = []
    distortion_strengths = []
    mean_artifact_nrs = []
    gaze_shift_artifact_corrs = []

    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            key = (c, level)
            a_fr_flat = artifact_maps_fr[key].flatten()
            a_nr_flat = artifact_maps_nr[key].flatten()

            # FR vs NR pixel-level Spearman correlation
            rho, _ = spearmanr(a_fr_flat, a_nr_flat)
            if not np.isnan(rho):
                fr_nr_corrs.append(rho)

            # Mean artifact energy vs compression level
            mean_artifact_nrs.append(np.mean(artifact_maps_nr[key]))
            distortion_strengths.append(100 - level)  # lower QF = higher distortion

            # Gaze shift vs artifact correlation
            p_free = data['saliency_freelook'][level]
            p_score = data['saliency_scoring'][level]
            if p_free is not None and p_score is not None:
                delta_gaze = np.abs(p_score - p_free)
                delta_flat = delta_gaze.flatten()
                rho_gaze, _ = spearmanr(delta_flat, a_nr_flat)
                if not np.isnan(rho_gaze):
                    gaze_shift_artifact_corrs.append(rho_gaze)

    fr_nr_mean = np.mean(fr_nr_corrs)
    fr_nr_ci = bootstrap_ci(fr_nr_corrs)
    dist_corr, _ = pearsonr(distortion_strengths, mean_artifact_nrs)
    gaze_corr_mean = np.mean(gaze_shift_artifact_corrs)
    gaze_ci = bootstrap_ci(gaze_shift_artifact_corrs)

    mechanism_results = {
        'fr_nr_correlation': {'mean': fr_nr_mean, 'ci_lo': fr_nr_ci[0], 'ci_hi': fr_nr_ci[2], 'n': len(fr_nr_corrs)},
        'distortion_strength_correlation': {'pearson_r': float(dist_corr), 'n': len(distortion_strengths)},
        'gaze_shift_artifact_correlation': {'mean': gaze_corr_mean, 'ci_lo': gaze_ci[0], 'ci_hi': gaze_ci[2], 'n': len(gaze_shift_artifact_corrs)},
    }

    logger.info(f"  FR vs NR Spearman (mean): {fr_nr_mean:.4f}  95%CI [{fr_nr_ci[0]:.4f}, {fr_nr_ci[2]:.4f}]")
    logger.info(f"  Distortion strength vs A_NR: r={dist_corr:.4f}")
    logger.info(f"  Gaze shift vs A_NR (mean):   {gaze_corr_mean:.4f}  95%CI [{gaze_ci[0]:.4f}, {gaze_ci[2]:.4f}]")

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 6: Parameter Sensitivity (alpha-beta grid)
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 6: Parameter Sensitivity Analysis")
    logger.info("=" * 80)

    # Select 10 high-distortion samples (lowest QF per content)
    high_dist_samples = []
    for c in contents:
        data = all_data[c]
        min_level = min(data['levels'])
        p_free = data['saliency_freelook'][min_level]
        p_score = data['saliency_scoring'][min_level]
        if p_free is not None and p_score is not None:
            high_dist_samples.append({
                'content': c, 'level': min_level,
                'p_free': p_free, 'p_score': p_score,
                'a_nr': artifact_maps_nr[(c, min_level)],
            })
    high_dist_samples = high_dist_samples[:10]
    logger.info(f"Using {len(high_dist_samples)} high-distortion samples for sensitivity study")

    alpha_range = np.arange(0.5, 2.6, 0.1)
    beta_range = np.arange(0.0, 1.05, 0.05)
    grid_results = []

    for a in alpha_range:
        for b in beta_range:
            ccs = []
            jsds = []
            for s in high_dist_samples:
                raw = a * s['p_free'] + b * s['a_nr']
                raw = np.maximum(raw, 0)
                p_hat = raw / (np.sum(raw) + 1e-12)
                ccs.append(SaliencyMetrics.pearson_correlation(p_hat, s['p_score']))
                jsds.append(SaliencyMetrics.jensen_shannon_divergence(p_hat, s['p_score']))
            grid_results.append({
                'alpha': round(a, 2), 'beta': round(b, 2),
                'mean_cc': np.mean(ccs), 'mean_jsd': np.mean(jsds),
            })

    df_grid = pd.DataFrame(grid_results)
    df_grid.to_csv(RESULTS_DIR / 'parameter_sensitivity.csv', index=False)
    best = df_grid.loc[df_grid['mean_cc'].idxmax()]
    logger.info(f"  Best CC on grid: α={best['alpha']}, β={best['beta']}, CC={best['mean_cc']:.4f}, JSD={best['mean_jsd']:.4f}")

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 7: Statistical Analysis
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 7: Statistical Analysis")
    logger.info("=" * 80)

    stat_rows = []

    # Pairwise comparisons (TAS NR vs each other method)
    comparisons = [
        ('TAS NR vs FreeLook', 'tas_nr_jsd', 'freelook_jsd'),
        ('TAS NR vs Artifact-only NR', 'tas_nr_jsd', 'artifact_nr_jsd'),
        ('TAS NR vs Fixed-mixture NR', 'tas_nr_jsd', 'mixture_nr_jsd'),
        ('TAS FR vs FreeLook', 'tas_fr_jsd', 'freelook_jsd'),
        ('TAS FR vs Artifact-only FR', 'tas_fr_jsd', 'artifact_fr_jsd'),
        ('TAS FR vs Fixed-mixture FR', 'tas_fr_jsd', 'mixture_fr_jsd'),
        ('TAS NR vs TAS FR', 'tas_nr_jsd', 'tas_fr_jsd'),
    ]

    p_values = []
    for comp_name, col_a, col_b in comparisons:
        vals_a = df_rq2[col_a].values
        vals_b = df_rq2[col_b].values

        # Wilcoxon signed-rank test
        stat_w, p_w = wilcoxon(vals_a, vals_b)
        # Paired t-test
        stat_t, p_t = ttest_rel(vals_a, vals_b)
        # Effect size
        d = cohens_d(vals_a, vals_b)
        # Bootstrap CI for difference
        diff = vals_a - vals_b
        ci = bootstrap_ci(diff)

        stat_rows.append({
            'Comparison': comp_name,
            'Wilcoxon_stat': stat_w, 'Wilcoxon_p': p_w,
            'ttest_stat': stat_t, 'ttest_p': p_t,
            'Cohens_d': d,
            'diff_mean': diff.mean(),
            'diff_ci_lo': ci[0], 'diff_ci_hi': ci[2],
        })
        p_values.append(p_w)

        logger.info(f"  {comp_name:35s}  Δ={diff.mean():.4f}  p={p_w:.2e}  d={d:.3f}")

    # Holm-Bonferroni correction
    sorted_idx = np.argsort(p_values)
    n_tests = len(p_values)
    for rank, idx in enumerate(sorted_idx):
        corrected_alpha = 0.05 / (n_tests - rank)
        stat_rows[idx]['holm_bonferroni_sig'] = p_values[idx] < corrected_alpha

    df_stats = pd.DataFrame(stat_rows)
    df_stats.to_csv(RESULTS_DIR / 'statistical_tests.csv', index=False)

    # Bootstrap CIs for main metrics
    logger.info("\n  Bootstrap 95% CIs:")
    for method_name, (cc_col, jsd_col) in methods_map.items():
        cc_ci = bootstrap_ci(df_rq2[cc_col].values)
        jsd_ci = bootstrap_ci(df_rq2[jsd_col].values)
        logger.info(f"    {method_name:25s}  CC=[{cc_ci[0]:.4f}, {cc_ci[2]:.4f}]  JSD=[{jsd_ci[0]:.4f}, {jsd_ci[2]:.4f}]")

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 8: Content-level Analysis (best/median/worst)
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 8: Content-Level Analysis")
    logger.info("=" * 80)

    content_summary = df_rq2.groupby('content').agg({
        'freelook_cc': 'mean', 'freelook_jsd': 'mean',
        'artifact_fr_cc': 'mean', 'artifact_nr_cc': 'mean',
        'mixture_fr_cc': 'mean', 'mixture_nr_cc': 'mean',
        'tas_fr_cc': 'mean', 'tas_fr_jsd': 'mean',
        'tas_nr_cc': 'mean', 'tas_nr_jsd': 'mean',
    }).reset_index()

    # Improvement = freelook_jsd - tas_nr_jsd (positive = TAS NR is better)
    content_summary['jsd_improvement'] = (
        df_rq2.groupby('content')['freelook_jsd'].mean().values -
        df_rq2.groupby('content')['tas_nr_jsd'].mean().values
    )
    content_summary = content_summary.sort_values('jsd_improvement', ascending=False)
    content_summary.to_csv(RESULTS_DIR / 'content_level_analysis.csv', index=False)

    best_c = content_summary.iloc[0]['content']
    median_idx = len(content_summary) // 2
    median_c = content_summary.iloc[median_idx]['content']
    worst_c = content_summary.iloc[-1]['content']
    logger.info(f"  Best content:   {best_c} (ΔJSD={content_summary.iloc[0]['jsd_improvement']:.4f})")
    logger.info(f"  Median content: {median_c} (ΔJSD={content_summary.iloc[median_idx]['jsd_improvement']:.4f})")
    logger.info(f"  Worst content:  {worst_c} (ΔJSD={content_summary.iloc[-1]['jsd_improvement']:.4f})")

    # ═══════════════════════════════════════════════════════════════════════
    # STAGE 9: Ablation — Stability Constraint Necessity
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 9: Ablation — Stability Constraint")
    logger.info("=" * 80)

    tau_values = [0.0, 0.50, 0.60, 0.70, 0.75, 0.80, 0.83, 0.85, 0.90, 0.95]
    ablation_rows = []

    for tau_test in tau_values:
        model_test = SCTAS(alpha=1.0, beta=0.3, tau=tau_test, eta=0.9)
        cc_all = []
        jsd_all = []
        for c in contents:
            data = all_data[c]
            for level in data['levels']:
                p_free = data['saliency_freelook'][level]
                p_score = data['saliency_scoring'][level]
                if p_free is None or p_score is None:
                    continue
                a_nr = artifact_maps_nr[(c, level)]
                p_hat = model_test.predict(p_free, a_nr)
                cc_all.append(SaliencyMetrics.pearson_correlation(p_hat, p_score))
                jsd_all.append(SaliencyMetrics.jensen_shannon_divergence(p_hat, p_score))

        ablation_rows.append({
            'tau': tau_test,
            'mean_cc': np.mean(cc_all), 'std_cc': np.std(cc_all),
            'mean_jsd': np.mean(jsd_all), 'std_jsd': np.std(jsd_all),
        })
        logger.info(f"  τ={tau_test:.2f}  CC={np.mean(cc_all):.4f}±{np.std(cc_all):.4f}  JSD={np.mean(jsd_all):.4f}±{np.std(jsd_all):.4f}")

    df_ablation = pd.DataFrame(ablation_rows)
    df_ablation.to_csv(RESULTS_DIR / 'ablation_tau.csv', index=False)

    # ═══════════════════════════════════════════════════════════════════════
    # FINAL: Save comprehensive results JSON
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("SAVING FINAL RESULTS")
    logger.info("=" * 80)

    final_results = {
        'timestamp': datetime.now().isoformat(),
        'dataset': {
            'name': 'TUD Eye Tracking Release 2',
            'n_contents': len(contents),
            'n_stimuli': len(df_rq2),
            'n_levels_per_content': 4,
        },
        'rq1_task_shift': {
            'cc_mean': float(df_rq1['cc'].mean()),
            'cc_std': float(df_rq1['cc'].std()),
            'jsd_mean': float(df_rq1['jsd'].mean()),
            'jsd_std': float(df_rq1['jsd'].std()),
            'dbg_free_mean': float(df_rq1['dbg_free'].mean()),
            'dbg_score_mean': float(df_rq1['dbg_score'].mean()),
            'dbg_delta': float((df_rq1['dbg_score'] - df_rq1['dbg_free']).mean()),
        },
        'rq2_main_table': {m: {
            'cc_mean': float(df_rq2[cc].mean()), 'cc_std': float(df_rq2[cc].std()),
            'jsd_mean': float(df_rq2[jsd].mean()), 'jsd_std': float(df_rq2[jsd].std()),
            'cc_ci': list(bootstrap_ci(df_rq2[cc].values)),
            'jsd_ci': list(bootstrap_ci(df_rq2[jsd].values)),
        } for m, (cc, jsd) in methods_map.items()},
        'mechanism_validation': mechanism_results,
        'parameter_sensitivity': {
            'best_alpha': float(best['alpha']),
            'best_beta': float(best['beta']),
            'best_cc': float(best['mean_cc']),
            'best_jsd': float(best['mean_jsd']),
        },
        'case_study': {
            'best': best_c, 'median': median_c, 'worst': worst_c,
        },
        'runtime_seconds': time.time() - t0,
    }

    with open(RESULTS_DIR / 'comprehensive_results.json', 'w') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    logger.info(f"\nAll results saved to {RESULTS_DIR}/")
    logger.info(f"Total runtime: {time.time()-t0:.1f} seconds")
    logger.info("\n" + "=" * 80)
    logger.info("REVISED EXPERIMENT COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
