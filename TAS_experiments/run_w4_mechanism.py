#!/usr/bin/env python3
"""
W4 Supplementary Experiment: Artifact Map Mechanism Validation
Produces formal statistics for paper revision.

Tests:
  1. FR-NR spatial consistency (per-sample Pearson CC)
  2. Within-content artifact energy monotonicity vs QF
  3. Artifact energy vs distortion strength (raw |Y_ref-Y_dist|)
  4. Block-boundary vs interior gradient ratio (artifact specificity test)

Author: Automated
Date: 2026-02-21
"""

import sys, os, json
import numpy as np
import pandas as pd
import cv2
from pathlib import Path
from scipy.stats import spearmanr, pearsonr

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics

RESULTS_DIR = PROJECT_ROOT / 'results' / 'w4_mechanism'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)
    contents = loader.get_unique_contents()

    rows = []

    for c in contents:
        data = loader.get_data_for_content(c, preprocess_saliency=True)
        ref_img = loader.load_original_image(c, color_space='ycrcb')
        levels = sorted(data['levels'])

        for lv in levels:
            img = data['images'][lv]
            h, w = img.shape[:2]

            # --- Raw distortion measure ---
            if ref_img is not None:
                if ref_img.shape[:2] != img.shape[:2]:
                    ref_resized = cv2.resize(ref_img, (w, h))
                else:
                    ref_resized = ref_img
                y_ref = ref_resized[:, :, 0].astype(np.float64)
                y_dist = img[:, :, 0].astype(np.float64)
                raw_mae = float(np.mean(np.abs(y_ref - y_dist)))
            else:
                raw_mae = np.nan
                ref_resized = None

            # --- NR artifact map (before probability normalization) ---
            a_nr = artifact_gen.compute_nr_artifact(
                img, use_blockiness=True, use_dct=True, use_ringing=True)
            e_nr = float(np.mean(a_nr))

            # --- FR artifact map ---
            if ref_resized is not None:
                a_fr = artifact_gen.compute_fr_artifact(
                    ref_resized, img, use_luminance=True)
                e_fr = float(np.mean(a_fr))
            else:
                a_fr = None
                e_fr = np.nan

            # --- FR-NR spatial correlation ---
            if a_fr is not None:
                a_nr_norm = a_nr / (a_nr.sum() + 1e-12)
                a_fr_norm = a_fr / (a_fr.sum() + 1e-12)
                spatial_cc = float(np.corrcoef(
                    a_nr_norm.flatten(), a_fr_norm.flatten())[0, 1])
            else:
                spatial_cc = np.nan

            # --- Block-boundary specificity test ---
            # Compare gradient energy AT block boundaries vs INTERIOR
            lum = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_YCrCb2BGR)
            lum = cv2.cvtColor(lum, cv2.COLOR_BGR2GRAY).astype(np.float64)

            grad_x = np.abs(np.diff(lum, axis=1))
            grad_y = np.abs(np.diff(lum, axis=0))

            # Block boundary mask (every 8th pixel)
            bnd_x = np.zeros(grad_x.shape, dtype=bool)
            bnd_y = np.zeros(grad_y.shape, dtype=bool)
            for i in range(8, grad_x.shape[1], 8):
                bnd_x[:, i-1] = True  # column boundary
            for j in range(8, grad_y.shape[0], 8):
                bnd_y[j-1, :] = True  # row boundary

            # Mean gradient at boundaries vs interior
            g_at_bnd = float(np.mean(np.concatenate([
                grad_x[bnd_x], grad_y[bnd_y]])))
            g_at_int = float(np.mean(np.concatenate([
                grad_x[~bnd_x], grad_y[~bnd_y]])))
            bnd_ratio = g_at_bnd / (g_at_int + 1e-12)

            rows.append({
                'content': c, 'level': lv,
                'raw_mae': raw_mae,
                'e_nr': e_nr, 'e_fr': e_fr,
                'spatial_cc_fr_nr': spatial_cc,
                'grad_at_boundary': g_at_bnd,
                'grad_at_interior': g_at_int,
                'boundary_ratio': bnd_ratio,
            })

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / 'w4_mechanism_data.csv', index=False)

    # ── Summary statistics ──
    print("=" * 60)
    print("W4 MECHANISM VALIDATION RESULTS")
    print("=" * 60)

    # Test 1: FR-NR spatial consistency
    cc_mean = df['spatial_cc_fr_nr'].mean()
    cc_min = df['spatial_cc_fr_nr'].min()
    print(f"\n[Test 1] FR-NR spatial correlation:")
    print(f"  Mean = {cc_mean:.4f}, Min = {cc_min:.4f}")

    # Test 2: Within-content energy monotonicity
    within_rhos_nr = []
    within_rhos_fr = []
    within_rhos_mae = []
    for c in contents:
        sub = df[df['content'] == c].sort_values('level')
        if len(sub) >= 3:
            rho_nr, _ = spearmanr(sub['level'], sub['e_nr'])
            rho_fr, _ = spearmanr(sub['level'], sub['e_fr'])
            rho_mae, _ = spearmanr(sub['level'], sub['raw_mae'])
            within_rhos_nr.append(rho_nr)
            within_rhos_fr.append(rho_fr)
            within_rhos_mae.append(rho_mae)

    print(f"\n[Test 2] Within-content Spearman(QF, energy):")
    print(f"  NR energy: mean ρ = {np.mean(within_rhos_nr):.4f} "
          f"({sum(1 for r in within_rhos_nr if r < 0)}/{len(within_rhos_nr)} negative)")
    print(f"  FR energy: mean ρ = {np.mean(within_rhos_fr):.4f} "
          f"({sum(1 for r in within_rhos_fr if r < 0)}/{len(within_rhos_fr)} negative)")
    print(f"  Raw MAE:   mean ρ = {np.mean(within_rhos_mae):.4f} "
          f"({sum(1 for r in within_rhos_mae if r < 0)}/{len(within_rhos_mae)} negative)")

    # Test 3: Artifact energy vs raw distortion (cross-sample)
    rho_nr_mae, p_nr_mae = spearmanr(df['e_nr'], df['raw_mae'])
    rho_fr_mae, p_fr_mae = spearmanr(df['e_fr'], df['raw_mae'])
    print(f"\n[Test 3] Cross-sample Spearman(energy, raw_MAE):")
    print(f"  NR: ρ = {rho_nr_mae:.4f}, p = {p_nr_mae:.2e}")
    print(f"  FR: ρ = {rho_fr_mae:.4f}, p = {p_fr_mae:.2e}")

    # Test 4: Block-boundary specificity
    print(f"\n[Test 4] Block-boundary gradient ratio (boundary / interior):")
    print(f"  Mean ratio = {df['boundary_ratio'].mean():.4f}")
    print(f"  Min ratio  = {df['boundary_ratio'].min():.4f}")
    print(f"  Max ratio  = {df['boundary_ratio'].max():.4f}")
    # A ratio > 1 means boundary gradients are STRONGER than interior
    # Expected for JPEG: at low QF, boundary ratio should be higher
    within_bnd_rhos = []
    for c in contents:
        sub = df[df['content'] == c].sort_values('level')
        if len(sub) >= 3:
            rho, _ = spearmanr(sub['level'], sub['boundary_ratio'])
            within_bnd_rhos.append(rho)
    print(f"  Within-content Spearman(QF, boundary_ratio): mean ρ = {np.mean(within_bnd_rhos):.4f}")
    print(f"    ({sum(1 for r in within_bnd_rhos if r < 0)}/{len(within_bnd_rhos)} negative = expected)")

    # Save summary
    summary = {
        'test1_fr_nr_spatial_cc': {'mean': cc_mean, 'min': cc_min, 'n': len(df)},
        'test2_within_content_monotonicity': {
            'nr_energy_mean_rho': float(np.mean(within_rhos_nr)),
            'nr_energy_n_negative': sum(1 for r in within_rhos_nr if r < 0),
            'fr_energy_mean_rho': float(np.mean(within_rhos_fr)),
            'raw_mae_mean_rho': float(np.mean(within_rhos_mae)),
            'raw_mae_n_negative': sum(1 for r in within_rhos_mae if r < 0),
        },
        'test3_energy_vs_distortion': {
            'nr_rho': rho_nr_mae, 'nr_p': p_nr_mae,
            'fr_rho': rho_fr_mae, 'fr_p': p_fr_mae,
        },
        'test4_boundary_specificity': {
            'mean_ratio': float(df['boundary_ratio'].mean()),
            'within_content_rho': float(np.mean(within_bnd_rhos)),
            'n_negative': sum(1 for r in within_bnd_rhos if r < 0),
        },
    }

    with open(RESULTS_DIR / 'w4_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=float)

    print(f"\nResults saved to {RESULTS_DIR}")

if __name__ == '__main__':
    main()
