#!/usr/bin/env python3
"""
Supplementary Experiments for the CGI 2026 Paper
=====================================================

Three additional analyses reported with the main experiments:

Stage 1 — Inter-observer ceiling (split-half bootstrap approximation)
    Since only aggregated FDMs (_COMBINED.jpg) are available, the ceiling
    is estimated via pixel-level split-half bootstrap on the scoring FDMs.
    100 bootstrap iterations; each randomly splits pixels into two halves
    and computes CC/JSD between the two halves.

Stage 2 — Extended metrics (SIM, AUC-Top20, KL divergence)
    Adds three standard saliency metrics to the LOCO evaluation on R2.

Stage 3 — Large-β stability-constraint ablation
    Fixes α=1.0, sweeps β ∈ {0.3, 0.5, 0.8, 1.0, 1.5, 2.0} and for each β
    sweeps τ ∈ {disabled, 0.0, 0.50, 0.70, 0.83, 0.90, 0.95} to demonstrate
    that the stability constraint becomes necessary as β grows.

All results are saved to results/supplementary/.

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
from scipy.stats import sem, pearsonr, spearmanr
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

# ─── Results directory ──────────────────────────────────────────────────────────
RESULTS_DIR = config.RESULTS_DIR / 'supplementary'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

log_file = RESULTS_DIR / 'supplementary.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ─── SC-TAS model (same as main script) ────────────────────────────────────────
def normalize_to_prob(m: np.ndarray) -> np.ndarray:
    m = np.maximum(m, 0).astype(np.float64)
    s = np.sum(m) + 1e-12
    return m / s


# ─── Additional metric functions ────────────────────────────────────────────────
def sim_metric(pred: np.ndarray, target: np.ndarray) -> float:
    """
    Similarity (SIM) metric.
    SIM = sum( min(p1, p2) )  where p1, p2 are L1-normalised.
    Range [0, 1]; higher is better.
    """
    p1 = pred.flatten().astype(np.float64)
    p2 = target.flatten().astype(np.float64)
    p1 = p1 / (np.sum(p1) + 1e-12)
    p2 = p2 / (np.sum(p2) + 1e-12)
    return float(np.sum(np.minimum(p1, p2)))


def kl_divergence(pred: np.ndarray, target: np.ndarray) -> float:
    """
    KL divergence: KL(target || pred).
    Convention: target is the "true" distribution.
    Lower is better (0 = identical).
    """
    eps = 1e-12
    p = target.flatten().astype(np.float64)
    q = pred.flatten().astype(np.float64)
    p = p / (np.sum(p) + eps)
    q = q / (np.sum(q) + eps)
    # Smooth
    p = np.maximum(p, eps)
    q = np.maximum(q, eps)
    return float(np.sum(p * np.log(p / q)))


def auc_judd(pred: np.ndarray, fixation_map: np.ndarray) -> float:
    """AUC-Top20 using the target's top 20% density as pseudo-fixations.

    The function name is retained for compatibility with the archived output
    columns. This is not canonical AUC-Judd because point fixation records are
    not available in the released aggregate FDM data.
    """
    pred_flat = pred.flatten()
    fix_flat = fixation_map.flatten()
    # Threshold at top 20% of fixation_map
    threshold = np.percentile(fix_flat, 80)
    fix_binary = (fix_flat >= threshold).astype(int)

    # Edge case
    pos = np.sum(fix_binary)
    neg = len(fix_binary) - pos
    if pos == 0 or neg == 0:
        return 0.5

    # Sort by prediction value
    sorted_idx = np.argsort(-pred_flat)
    sorted_fix = fix_binary[sorted_idx]

    tp = np.cumsum(sorted_fix)
    fp = np.arange(1, len(sorted_idx) + 1) - tp
    tpr = tp / pos
    fpr = fp / neg

    # Trapezoidal AUC
    auc = np.trapz(tpr, fpr)
    return float(np.clip(auc, 0.0, 1.0))


def bootstrap_ci(values, n_boot=2000, ci=0.95, seed=42):
    rng = np.random.RandomState(seed)
    vals = np.array(values)
    n = len(vals)
    if n < 2:
        return vals.mean(), vals.mean(), vals.mean()
    boot_means = np.array([rng.choice(vals, n, replace=True).mean() for _ in range(n_boot)])
    lo = np.percentile(boot_means, (1 - ci) / 2 * 100)
    hi = np.percentile(boot_means, (1 + ci) / 2 * 100)
    return float(lo), float(vals.mean()), float(hi)


# ═════════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    logger.info("=" * 80)
    logger.info("SUPPLEMENTARY EXPERIMENTS - CGI 2026")
    logger.info(f"Start: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # ─── Data loading ───────────────────────────────────────────────────────
    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)
    contents = loader.get_unique_contents()
    logger.info(f"Dataset: {len(contents)} contents, {len(contents)*4} stimuli")

    logger.info("Loading all data...")
    all_data = {}
    for c in contents:
        all_data[c] = loader.get_data_for_content(c, preprocess_saliency=True)
    logger.info(f"Data loaded in {time.time()-t0:.1f}s")

    # Pre-compute NR artifact maps (reuse across stages)
    logger.info("Computing NR artifact maps for all stimuli...")
    artifact_maps_nr = {}
    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            img = data['images'][level]
            a_nr = artifact_gen.compute_nr_artifact(img, use_blockiness=True,
                                                     use_dct=True, use_ringing=True)
            artifact_maps_nr[(c, level)] = artifact_gen.normalize_artifact_to_probability(a_nr)
    logger.info("Artifact maps ready.")

    # ═════════════════════════════════════════════════════════════════════════
    # STAGE 1: Inter-Observer Ceiling (Split-Half Bootstrap)
    # ═════════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 1: Inter-Observer Ceiling (Split-Half Bootstrap)")
    logger.info("=" * 80)

    # Method: for each scoring FDM, add independent Gaussian noise to create
    # two "pseudo-observer-half" maps, then compute CC/JSD between them.
    # We vary noise levels σ ∈ {0.05, 0.10, 0.15, 0.20} relative to map std.
    # The true ceiling lies somewhere between the noise-free (CC=1) and the
    # noisiest condition. We use σ=0.10 as the primary estimate (moderate noise).
    #
    # Additionally, we use a spatial split-half: randomly divide each FDM into
    # two disjoint pixel subsets, reconstruct each half, and measure agreement.
    # This gives an upper-bound on how well *any* model could match the FDM.

    n_bootstrap = 100
    rng = np.random.RandomState(42)

    # Approach 1: Noise-injection split-half
    noise_sigmas = [0.05, 0.10, 0.15, 0.20]
    ceiling_noise_results = []

    for sigma_rel in noise_sigmas:
        cc_all = []
        jsd_all = []
        sim_all = []
        for c in contents:
            data = all_data[c]
            for level in data['levels']:
                p_score = data['saliency_scoring'][level]
                if p_score is None:
                    continue
                sigma = sigma_rel * np.std(p_score)
                for _ in range(n_bootstrap):
                    noise1 = rng.normal(0, sigma, p_score.shape)
                    noise2 = rng.normal(0, sigma, p_score.shape)
                    half1 = normalize_to_prob(p_score + noise1)
                    half2 = normalize_to_prob(p_score + noise2)
                    cc_all.append(SaliencyMetrics.pearson_correlation(half1, half2))
                    jsd_all.append(SaliencyMetrics.jensen_shannon_divergence(half1, half2))
                    sim_all.append(sim_metric(half1, half2))

        ceiling_noise_results.append({
            'sigma_rel': sigma_rel,
            'cc_mean': np.mean(cc_all), 'cc_std': np.std(cc_all),
            'jsd_mean': np.mean(jsd_all), 'jsd_std': np.std(jsd_all),
            'sim_mean': np.mean(sim_all), 'sim_std': np.std(sim_all),
            'n_pairs': len(cc_all),
        })
        logger.info(f"  σ_rel={sigma_rel:.2f}  CC={np.mean(cc_all):.4f}±{np.std(cc_all):.4f}  "
                     f"JSD={np.mean(jsd_all):.4f}±{np.std(jsd_all):.4f}  "
                     f"SIM={np.mean(sim_all):.4f}±{np.std(sim_all):.4f}")

    # Approach 2: Spatial split-half (more principled)
    # Randomly split pixel positions into two halves, compute smoothed FDMs,
    # then measure CC. Repeated 100 times per sample.
    logger.info("\n  Spatial split-half approach:")
    spatial_cc_all = []
    spatial_jsd_all = []
    spatial_sim_all = []

    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            p_score = data['saliency_scoring'][level]
            if p_score is None:
                continue
            h, w = p_score.shape
            n_pix = h * w
            flat = p_score.flatten()

            for _ in range(n_bootstrap):
                # Random permutation of pixel indices
                perm = rng.permutation(n_pix)
                half1_idx = perm[:n_pix // 2]
                half2_idx = perm[n_pix // 2:]

                # Create two half-maps
                m1 = np.zeros(n_pix)
                m2 = np.zeros(n_pix)
                m1[half1_idx] = flat[half1_idx]
                m2[half2_idx] = flat[half2_idx]
                m1 = m1.reshape(h, w)
                m2 = m2.reshape(h, w)

                # Smooth with Gaussian (σ=5 pixels) to reduce noise
                from scipy.ndimage import gaussian_filter
                m1_smooth = gaussian_filter(m1, sigma=5.0)
                m2_smooth = gaussian_filter(m2, sigma=5.0)
                m1_prob = normalize_to_prob(m1_smooth)
                m2_prob = normalize_to_prob(m2_smooth)

                spatial_cc_all.append(SaliencyMetrics.pearson_correlation(m1_prob, m2_prob))
                spatial_jsd_all.append(SaliencyMetrics.jensen_shannon_divergence(m1_prob, m2_prob))
                spatial_sim_all.append(sim_metric(m1_prob, m2_prob))

    spatial_ceiling = {
        'method': 'spatial_split_half',
        'cc_mean': np.mean(spatial_cc_all), 'cc_std': np.std(spatial_cc_all),
        'jsd_mean': np.mean(spatial_jsd_all), 'jsd_std': np.std(spatial_jsd_all),
        'sim_mean': np.mean(spatial_sim_all), 'sim_std': np.std(spatial_sim_all),
        'n_pairs': len(spatial_cc_all),
    }
    logger.info(f"  Spatial split-half: CC={spatial_ceiling['cc_mean']:.4f}±{spatial_ceiling['cc_std']:.4f}  "
                 f"JSD={spatial_ceiling['jsd_mean']:.4f}±{spatial_ceiling['jsd_std']:.4f}  "
                 f"SIM={spatial_ceiling['sim_mean']:.4f}±{spatial_ceiling['sim_std']:.4f}")

    # Save ceiling results
    df_ceiling_noise = pd.DataFrame(ceiling_noise_results)
    df_ceiling_noise.to_csv(RESULTS_DIR / 'ceiling_noise_injection.csv', index=False)

    ceiling_summary = {
        'noise_injection': ceiling_noise_results,
        'spatial_split_half': spatial_ceiling,
        'interpretation': (
            'The noise-injection method with σ_rel=0.10 and the spatial split-half '
            'method provide complementary upper-bound estimates. The spatial method '
            'is more conservative (lower CC) because it removes half the signal.'
        ),
    }
    with open(RESULTS_DIR / 'ceiling_results.json', 'w') as f:
        json.dump(ceiling_summary, f, indent=2)

    logger.info("  Ceiling results saved.")

    # ═════════════════════════════════════════════════════════════════════════
    # STAGE 2: Extended Metrics (SIM, AUC-Top20, KL)
    # ═════════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 2: Extended Metrics (SIM, AUC-Top20, KL)")
    logger.info("=" * 80)

    # SC-TAS configurations
    sctas_nr = SCTAS(alpha=1.0, beta=0.3, tau=0.83, eta=0.9)
    sctas_fr = SCTAS(alpha=1.0, beta=0.5, tau=0.83, eta=0.9)

    # Pre-compute FR artifact maps too
    artifact_maps_fr = {}
    for c in contents:
        data = all_data[c]
        ref_img = loader.load_original_image(c, color_space='ycrcb')
        for level in data['levels']:
            img = data['images'][level]
            key = (c, level)
            if ref_img is not None:
                import cv2
                if ref_img.shape[:2] != img.shape[:2]:
                    ref_resized = cv2.resize(ref_img, (img.shape[1], img.shape[0]))
                else:
                    ref_resized = ref_img
                a_fr = artifact_gen.compute_fr_artifact(ref_resized, img, use_luminance=True)
            else:
                a_fr = artifact_gen.compute_fr_artifact(img, img, use_luminance=True)
            artifact_maps_fr[key] = artifact_gen.normalize_artifact_to_probability(a_fr)

    # LOCO evaluation with extended metrics
    ext_rows = []
    for c in contents:
        data = all_data[c]
        for level in data['levels']:
            p_free = data['saliency_freelook'][level]
            p_score = data['saliency_scoring'][level]
            if p_free is None or p_score is None:
                continue

            key = (c, level)
            a_nr = artifact_maps_nr[key]
            a_fr = artifact_maps_fr[key]

            # Generate predictions
            p_mix_nr = normalize_to_prob(0.5 * p_free + 0.5 * a_nr)
            p_mix_fr = normalize_to_prob(0.5 * p_free + 0.5 * a_fr)
            p_tas_nr = sctas_nr.predict(p_free, a_nr)
            p_tas_fr = sctas_fr.predict(p_free, a_fr)

            methods = {
                'FreeLook prior': p_free,
                'Artifact only (NR)': a_nr,
                'Artifact only (FR)': a_fr,
                'Fixed mixture (NR)': p_mix_nr,
                'Fixed mixture (FR)': p_mix_fr,
                'TAS NR': p_tas_nr,
                'TAS FR': p_tas_fr,
            }

            for method_name, pred in methods.items():
                row = {
                    'content': c, 'level': level, 'method': method_name,
                    'cc': SaliencyMetrics.pearson_correlation(pred, p_score),
                    'jsd': SaliencyMetrics.jensen_shannon_divergence(pred, p_score),
                    'sim': sim_metric(pred, p_score),
                    'kl': kl_divergence(pred, p_score),
                    'auc_judd': auc_judd(pred, p_score),
                }
                ext_rows.append(row)

    df_ext = pd.DataFrame(ext_rows)
    df_ext.to_csv(RESULTS_DIR / 'extended_metrics_all.csv', index=False)

    # Summary table
    logger.info("\n--- Extended Metrics Summary (R2, 160 samples) ---")
    ext_summary_rows = []
    for method_name in ['FreeLook prior', 'Artifact only (NR)', 'Artifact only (FR)',
                         'Fixed mixture (NR)', 'Fixed mixture (FR)', 'TAS NR', 'TAS FR']:
        sub = df_ext[df_ext['method'] == method_name]
        row = {'Method': method_name}
        for metric in ['cc', 'jsd', 'sim', 'kl', 'auc_judd']:
            row[f'{metric}_mean'] = sub[metric].mean()
            row[f'{metric}_std'] = sub[metric].std()
        ext_summary_rows.append(row)
        logger.info(f"  {method_name:25s}  CC={row['cc_mean']:.4f}±{row['cc_std']:.4f}  "
                     f"SIM={row['sim_mean']:.4f}±{row['sim_std']:.4f}  "
                     f"AUC={row['auc_judd_mean']:.4f}±{row['auc_judd_std']:.4f}  "
                     f"KL={row['kl_mean']:.4f}±{row['kl_std']:.4f}")

    df_ext_summary = pd.DataFrame(ext_summary_rows)
    df_ext_summary.to_csv(RESULTS_DIR / 'extended_metrics_summary.csv', index=False)

    # ═════════════════════════════════════════════════════════════════════════
    # STAGE 3: Large-β Stability Constraint Ablation
    # ═════════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 3: Large-β Stability Constraint Ablation")
    logger.info("=" * 80)

    beta_values = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    tau_values = ['disabled', 0.0, 0.50, 0.70, 0.83, 0.90, 0.95]
    eta = 0.9

    ablation_rows = []

    for beta in beta_values:
        for tau in tau_values:
            cc_all = []
            jsd_all = []
            sim_all_vals = []
            shrink_counts = []
            final_betas = []

            for c in contents:
                data = all_data[c]
                for level in data['levels']:
                    p_free = data['saliency_freelook'][level]
                    p_score = data['saliency_scoring'][level]
                    if p_free is None or p_score is None:
                        continue
                    a_nr = artifact_maps_nr[(c, level)]

                    if tau == 'disabled':
                        # No stability constraint: simple fusion
                        raw = 1.0 * p_free + beta * a_nr
                        raw = np.maximum(raw, 0)
                        p_hat = raw / (np.sum(raw) + 1e-12)
                        n_shrinks = 0
                        final_beta = beta
                    else:
                        model = SCTAS(alpha=1.0, beta=beta, tau=float(tau), eta=eta)
                        p_hat, n_shrinks, final_beta = model.predict_count_shrinks(p_free, a_nr)

                    cc_all.append(SaliencyMetrics.pearson_correlation(p_hat, p_score))
                    jsd_all.append(SaliencyMetrics.jensen_shannon_divergence(p_hat, p_score))
                    sim_all_vals.append(sim_metric(p_hat, p_score))
                    shrink_counts.append(n_shrinks)
                    final_betas.append(final_beta)

            # Proportion of samples where constraint activated
            activated = sum(1 for s in shrink_counts if s > 0)
            total = len(shrink_counts)

            ablation_rows.append({
                'beta': beta,
                'tau': str(tau),
                'cc_mean': np.mean(cc_all), 'cc_std': np.std(cc_all),
                'jsd_mean': np.mean(jsd_all), 'jsd_std': np.std(jsd_all),
                'sim_mean': np.mean(sim_all_vals), 'sim_std': np.std(sim_all_vals),
                'mean_shrinks': np.mean(shrink_counts),
                'mean_final_beta': np.mean(final_betas),
                'pct_activated': activated / total * 100 if total > 0 else 0,
                'n_samples': total,
            })
            logger.info(f"  β={beta:.1f}, τ={str(tau):>8s}  "
                         f"CC={np.mean(cc_all):.4f}±{np.std(cc_all):.4f}  "
                         f"JSD={np.mean(jsd_all):.4f}±{np.std(jsd_all):.4f}  "
                         f"activated={activated}/{total} ({activated/total*100:.1f}%)  "
                         f"avg_shrinks={np.mean(shrink_counts):.1f}")

    df_ablation = pd.DataFrame(ablation_rows)
    df_ablation.to_csv(RESULTS_DIR / 'ablation_beta_tau.csv', index=False)

    # Also create a "disabled vs enabled" comparison table
    logger.info("\n--- Stability constraint effect (disabled vs τ=0.83) ---")
    comparison_rows = []
    for beta in beta_values:
        row_disabled = df_ablation[(df_ablation['beta'] == beta) & (df_ablation['tau'] == 'disabled')]
        row_enabled = df_ablation[(df_ablation['beta'] == beta) & (df_ablation['tau'] == '0.83')]
        if len(row_disabled) > 0 and len(row_enabled) > 0:
            cc_disabled = row_disabled.iloc[0]['cc_mean']
            cc_enabled = row_enabled.iloc[0]['cc_mean']
            delta_cc = cc_enabled - cc_disabled
            pct_activated = row_enabled.iloc[0]['pct_activated']
            comparison_rows.append({
                'beta': beta,
                'cc_no_constraint': cc_disabled,
                'cc_with_tau_083': cc_enabled,
                'delta_cc': delta_cc,
                'pct_activated': pct_activated,
            })
            logger.info(f"  β={beta:.1f}  CC(disabled)={cc_disabled:.4f}  "
                         f"CC(τ=0.83)={cc_enabled:.4f}  ΔCC={delta_cc:+.4f}  "
                         f"activated={pct_activated:.1f}%")

    df_comparison = pd.DataFrame(comparison_rows)
    df_comparison.to_csv(RESULTS_DIR / 'constraint_effect_comparison.csv', index=False)

    # ═════════════════════════════════════════════════════════════════════════
    # FINAL: Save comprehensive results JSON
    # ═════════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("SAVING COMPREHENSIVE RESULTS")
    logger.info("=" * 80)

    # Helper to convert numpy types to native Python for JSON serialization
    def to_native(obj):
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: to_native(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [to_native(v) for v in obj]
        return obj

    final = to_native({
        'timestamp': datetime.now().isoformat(),
        'ceiling': {
            'noise_injection': ceiling_noise_results,
            'spatial_split_half': spatial_ceiling,
        },
        'extended_metrics': {
            method: {
                m: {'mean': float(df_ext[df_ext['method'] == method][m].mean()),
                     'std': float(df_ext[df_ext['method'] == method][m].std())}
                for m in ['cc', 'jsd', 'sim', 'kl', 'auc_judd']
            }
            for method in df_ext['method'].unique()
        },
        'ablation_beta_tau': {
            f'beta_{b}_tau_{t}': {
                'cc_mean': float(row['cc_mean']),
                'jsd_mean': float(row['jsd_mean']),
                'pct_activated': float(row['pct_activated']),
                'mean_shrinks': float(row['mean_shrinks']),
            }
            for _, row in df_ablation.iterrows()
            for b, t in [(row['beta'], row['tau'])]
        },
        'constraint_effect': comparison_rows,
        'runtime_seconds': time.time() - t0,
    })

    with open(RESULTS_DIR / 'supplementary_results.json', 'w') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    logger.info(f"\nAll results saved to {RESULTS_DIR}/")
    logger.info(f"Total runtime: {time.time()-t0:.1f} seconds")
    logger.info("=" * 80)
    logger.info("SUPPLEMENTARY EXPERIMENTS COMPLETED")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
