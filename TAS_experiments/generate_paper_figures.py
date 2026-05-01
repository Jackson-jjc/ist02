#!/usr/bin/env python3
"""
Generate all paper figures (Fig.3–Fig.7) from real experimental CSV data.
CGI 2026 — SC-TAS Paper

Figures:
  Fig.3: Parameter sensitivity heatmap (α vs β, CC on 10 high-distortion samples)
  Fig.4: RQ1 task shift trends (CC, JSD, centroid shift, entropy vs QF level)
  Fig.5: (A) RQ2 method comparison bar chart (B) RQ3 Dbg across compression levels
  Fig.6: Qualitative case study (best/median/worst by JSD improvement)
  Fig.7: Content-level heatmap (40 contents × methods)

Author: Automated
Date: 2026-02-21
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from scipy.stats import sem

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
RESULTS_MAIN  = PROJECT_ROOT / 'results' / 'revised_real'
RESULTS_CROSS = PROJECT_ROOT / 'results' / 'crossdataset_baselines'
RESULTS_SUPP  = PROJECT_ROOT / 'results' / 'supplementary'
OUTPUT_DIR    = PROJECT_ROOT.parent / 'paper' / 'TUDpaper' / 'cgi2018_latex' / 'images'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# For qualitative figure, we need the experiment source code
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

# ─── Shared style ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'font.family': 'sans-serif',
})

# ═══════════════════════════════════════════════════════════════════════════════
# Fig.3 — Parameter Sensitivity Heatmap
# ═══════════════════════════════════════════════════════════════════════════════
def generate_fig3():
    """Parameter sensitivity heatmap: α vs β, CC on high-distortion subset."""
    print("Generating Fig.3: Parameter sensitivity heatmap...")

    df = pd.read_csv(RESULTS_MAIN / 'parameter_sensitivity.csv')

    alphas = sorted(df['alpha'].unique())
    betas  = sorted(df['beta'].unique())

    # Build 2D grid
    cc_grid = np.full((len(betas), len(alphas)), np.nan)
    for _, row in df.iterrows():
        ai = alphas.index(row['alpha'])
        bi = betas.index(row['beta'])
        cc_grid[bi, ai] = row['mean_cc']

    # Find best point
    best_idx = df['mean_cc'].idxmax()
    best = df.loc[best_idx]
    best_ai = alphas.index(best['alpha'])
    best_bi = betas.index(best['beta'])

    fig, ax = plt.subplots(figsize=(7, 5))

    im = ax.imshow(cc_grid, aspect='auto', origin='lower',
                   cmap='RdYlGn', interpolation='bilinear',
                   vmin=cc_grid[~np.isnan(cc_grid)].min(),
                   vmax=cc_grid[~np.isnan(cc_grid)].max())

    # Axis ticks — show every other label to avoid crowding
    tick_step_a = max(1, len(alphas) // 10)
    tick_step_b = max(1, len(betas) // 10)
    ax.set_xticks(range(0, len(alphas), tick_step_a))
    ax.set_xticklabels([f'{alphas[i]:.1f}' for i in range(0, len(alphas), tick_step_a)])
    ax.set_yticks(range(0, len(betas), tick_step_b))
    ax.set_yticklabels([f'{betas[i]:.2f}' for i in range(0, len(betas), tick_step_b)])

    ax.set_xlabel(r'$\alpha$ (free-viewing weight)')
    ax.set_ylabel(r'$\beta$ (artifact weight)')

    # Best point marker
    ax.plot(best_ai, best_bi, marker='*', markersize=18, color='white',
            markeredgecolor='black', markeredgewidth=1.5, zorder=10)
    ax.annotate(f'CC={best["mean_cc"]:.3f}\n'
                f'$\\alpha$={best["alpha"]:.1f}, $\\beta$={best["beta"]:.2f}',
                xy=(best_ai, best_bi), xytext=(best_ai + 3, best_bi + 3),
                fontsize=9, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='black', lw=1.2),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='black', alpha=0.9))

    # Add contour lines
    X, Y = np.meshgrid(range(len(alphas)), range(len(betas)))
    contour = ax.contour(X, Y, cc_grid, levels=8, colors='black', linewidths=0.5, alpha=0.4)
    ax.clabel(contour, inline=True, fontsize=7, fmt='%.3f')

    cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cbar.set_label('Mean Pearson Correlation (CC)', fontsize=11)

    ax.set_title('Parameter Sensitivity on 10 High-Distortion Samples', fontsize=13)

    fig.savefig(OUTPUT_DIR / 'fig_b1c_parameter_heatmap_REAL.png')
    plt.close(fig)
    print(f"  Saved: {OUTPUT_DIR / 'fig_b1c_parameter_heatmap_REAL.png'}")


# ═══════════════════════════════════════════════════════════════════════════════
# Fig.4 — RQ1 Task Shift Trends
# ═══════════════════════════════════════════════════════════════════════════════
def generate_fig4():
    """RQ1 task shift: CC, JSD, centroid shift, entropy vs compression level."""
    print("Generating Fig.4: RQ1 task shift trends...")

    df = pd.read_csv(RESULTS_MAIN / 'rq1_task_shift.csv')

    # Group by level
    levels = sorted(df['level'].unique())

    # Compute per-level statistics
    stats = []
    for lv in levels:
        sub = df[df['level'] == lv]
        n = len(sub)
        stats.append({
            'level': lv, 'n': n,
            'cc_mean': sub['cc'].mean(), 'cc_sem': sem(sub['cc']) if n > 1 else 0,
            'jsd_mean': sub['jsd'].mean(), 'jsd_sem': sem(sub['jsd']) if n > 1 else 0,
            'centroid_mean': sub['centroid_shift'].mean(), 'centroid_sem': sem(sub['centroid_shift']) if n > 1 else 0,
            'entropy_free_mean': sub['entropy_free'].mean(),
            'entropy_score_mean': sub['entropy_score'].mean(),
            'entropy_sem_f': sem(sub['entropy_free']) if n > 1 else 0,
            'entropy_sem_s': sem(sub['entropy_score']) if n > 1 else 0,
        })
    sdf = pd.DataFrame(stats)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    level_arr = sdf['level'].values
    z = 1.96  # 95% CI

    # Panel A: CC
    ax = axes[0, 0]
    ax.fill_between(level_arr,
                    sdf['cc_mean'] - z * sdf['cc_sem'],
                    sdf['cc_mean'] + z * sdf['cc_sem'],
                    alpha=0.25, color='tab:blue')
    ax.plot(level_arr, sdf['cc_mean'], 'o-', color='tab:blue', markersize=3, linewidth=1.2)
    # Individual samples as gray dots
    for lv in levels:
        sub = df[df['level'] == lv]
        ax.scatter([lv] * len(sub), sub['cc'], color='gray', alpha=0.15, s=8, zorder=1)
    ax.set_xlabel('JPEG Quality Factor')
    ax.set_ylabel('Pearson Correlation (CC)')
    ax.set_title('(a) Task Shift: CC between Free-looking and Scoring')
    ax.axhline(y=df['cc'].mean(), ls='--', color='red', alpha=0.5, linewidth=0.8,
               label=f'Overall mean = {df["cc"].mean():.3f}')
    ax.legend(loc='lower right', fontsize=8)
    ax.set_ylim(0.55, 1.0)
    ax.grid(True, alpha=0.3)

    # Panel B: JSD
    ax = axes[0, 1]
    ax.fill_between(level_arr,
                    sdf['jsd_mean'] - z * sdf['jsd_sem'],
                    sdf['jsd_mean'] + z * sdf['jsd_sem'],
                    alpha=0.25, color='tab:orange')
    ax.plot(level_arr, sdf['jsd_mean'], 's-', color='tab:orange', markersize=3, linewidth=1.2)
    for lv in levels:
        sub = df[df['level'] == lv]
        ax.scatter([lv] * len(sub), sub['jsd'], color='gray', alpha=0.15, s=8, zorder=1)
    ax.set_xlabel('JPEG Quality Factor')
    ax.set_ylabel('Jensen–Shannon Divergence (JSD)')
    ax.set_title('(b) Task Shift: JSD between Free-looking and Scoring')
    ax.axhline(y=df['jsd'].mean(), ls='--', color='red', alpha=0.5, linewidth=0.8,
               label=f'Overall mean = {df["jsd"].mean():.3f}')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel C: Centroid Shift
    ax = axes[1, 0]
    ax.fill_between(level_arr,
                    sdf['centroid_mean'] - z * sdf['centroid_sem'],
                    sdf['centroid_mean'] + z * sdf['centroid_sem'],
                    alpha=0.25, color='tab:green')
    ax.plot(level_arr, sdf['centroid_mean'], '^-', color='tab:green', markersize=3, linewidth=1.2)
    for lv in levels:
        sub = df[df['level'] == lv]
        ax.scatter([lv] * len(sub), sub['centroid_shift'], color='gray', alpha=0.15, s=8, zorder=1)
    ax.set_xlabel('JPEG Quality Factor')
    ax.set_ylabel('Centroid Shift (pixels)')
    ax.set_title('(c) Spatial Centroid Shift')
    ax.axhline(y=df['centroid_shift'].mean(), ls='--', color='red', alpha=0.5, linewidth=0.8,
               label=f'Overall mean = {df["centroid_shift"].mean():.1f} px')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel D: Entropy
    ax = axes[1, 1]
    ax.fill_between(level_arr,
                    sdf['entropy_free_mean'] - z * sdf['entropy_sem_f'],
                    sdf['entropy_free_mean'] + z * sdf['entropy_sem_f'],
                    alpha=0.2, color='tab:blue')
    ax.plot(level_arr, sdf['entropy_free_mean'], 'o-', color='tab:blue',
            markersize=3, linewidth=1.2, label='Free-looking')
    ax.fill_between(level_arr,
                    sdf['entropy_score_mean'] - z * sdf['entropy_sem_s'],
                    sdf['entropy_score_mean'] + z * sdf['entropy_sem_s'],
                    alpha=0.2, color='tab:orange')
    ax.plot(level_arr, sdf['entropy_score_mean'], 's-', color='tab:orange',
            markersize=3, linewidth=1.2, label='Scoring')
    ax.set_xlabel('JPEG Quality Factor')
    ax.set_ylabel('Shannon Entropy')
    ax.set_title('(d) Attention Entropy')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.suptitle('RQ1: Task Shift Analysis across JPEG Compression Levels', fontsize=14, y=1.01)
    fig.tight_layout()

    fig.savefig(OUTPUT_DIR / 'fig_b1d_rq1_trend_improved.png')
    plt.close(fig)
    print(f"  Saved: {OUTPUT_DIR / 'fig_b1d_rq1_trend_improved.png'}")


# ═══════════════════════════════════════════════════════════════════════════════
# Fig.5 — RQ2 Method Comparison + RQ3 Dbg
# ═══════════════════════════════════════════════════════════════════════════════
def generate_fig5():
    """(A) RQ2 bar chart with CI; (B) RQ3 Dbg across compression levels."""
    print("Generating Fig.5: RQ2 prediction + RQ3 Dbg...")

    # ── Load data ──
    rq2 = pd.read_csv(RESULTS_MAIN / 'rq2_prediction_all.csv')
    rq1 = pd.read_csv(RESULTS_MAIN / 'rq1_task_shift.csv')

    # Also load learning baselines
    lb = pd.read_csv(RESULTS_CROSS / 'learning_baselines_r2.csv')

    # Load U-Net-lite baseline
    unet_lb = pd.read_csv(PROJECT_ROOT / 'results' / 'unet_lite_baseline' / 'unet_lite_r2_loco.csv')

    # ── Panel A: Method comparison ──
    methods_cc = {
        'Free-look\nprior':       rq2['freelook_cc'].values,
        'Artifact\nonly (FR)':    rq2['artifact_fr_cc'].values,
        'Artifact\nonly (NR)':    rq2['artifact_nr_cc'].values,
        'Fixed mix\n(FR)':        rq2['mixture_fr_cc'].values,
        'Fixed mix\n(NR)':        rq2['mixture_nr_cc'].values,
        'SC-TAS\nFR':             rq2['tas_fr_cc'].values,
        'SC-TAS\nNR':             rq2['tas_nr_cc'].values,
        'LB1\n(Ridge)':           lb['ridge_cc'].values,
        'LB2\n(MLP)':             lb['mlp_cc'].values,
        'LB3\n(U-Net)':           unet_lb['unet_cc'].values,
    }

    methods_jsd = {
        'Free-look\nprior':       rq2['freelook_jsd'].values,
        'Artifact\nonly (FR)':    rq2['artifact_fr_jsd'].values,
        'Artifact\nonly (NR)':    rq2['artifact_nr_jsd'].values,
        'Fixed mix\n(FR)':        rq2['mixture_fr_jsd'].values,
        'Fixed mix\n(NR)':        rq2['mixture_nr_jsd'].values,
        'SC-TAS\nFR':             rq2['tas_fr_jsd'].values,
        'SC-TAS\nNR':             rq2['tas_nr_jsd'].values,
        'LB1\n(Ridge)':           lb['ridge_jsd'].values,
        'LB2\n(MLP)':             lb['mlp_jsd'].values,
        'LB3\n(U-Net)':           unet_lb['unet_jsd'].values,
    }

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 5.5))

    # --- Panel A: CC bar chart ---
    names = list(methods_cc.keys())
    cc_means = [np.mean(v) for v in methods_cc.values()]
    cc_cis = [1.96 * sem(v) for v in methods_cc.values()]

    colors_cc = ['#4e79a7', '#e15759', '#e15759', '#f28e2b', '#f28e2b',
                 '#59a14f', '#59a14f', '#b07aa1', '#b07aa1', '#b07aa1']

    bars1 = ax1.bar(range(len(names)), cc_means, yerr=cc_cis,
                    capsize=3, color=colors_cc, edgecolor='black', linewidth=0.5,
                    error_kw={'linewidth': 1})
    # Highlight TAS NR
    bars1[6].set_edgecolor('red')
    bars1[6].set_linewidth(2)

    ax1.set_xticks(range(len(names)))
    ax1.set_xticklabels(names, fontsize=8, ha='center')
    ax1.set_ylabel('Pearson Correlation (CC)')
    ax1.set_title('(A) RQ2: Method Comparison — CC ↑')
    ax1.set_ylim(0, 1.0)
    ax1.axhline(y=0.990, ls=':', color='gray', alpha=0.6, linewidth=1)
    ax1.annotate('Ceiling (0.990)', xy=(0.5, 0.990), fontsize=7, color='gray', va='bottom')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for i, (m, e) in enumerate(zip(cc_means, cc_cis)):
        ax1.text(i, m + e + 0.015, f'{m:.3f}', ha='center', va='bottom', fontsize=7, fontweight='bold')

    # --- Panel B: JSD bar chart ---
    jsd_means = [np.mean(v) for v in methods_jsd.values()]
    jsd_cis = [1.96 * sem(v) for v in methods_jsd.values()]

    colors_jsd = ['#4e79a7', '#e15759', '#e15759', '#f28e2b', '#f28e2b',
                  '#59a14f', '#59a14f', '#b07aa1', '#b07aa1', '#b07aa1']

    bars2 = ax2.bar(range(len(names)), jsd_means, yerr=jsd_cis,
                    capsize=3, color=colors_jsd, edgecolor='black', linewidth=0.5,
                    error_kw={'linewidth': 1})
    bars2[6].set_edgecolor('red')
    bars2[6].set_linewidth(2)

    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels(names, fontsize=8, ha='center')
    ax2.set_ylabel('Jensen–Shannon Divergence (JSD)')
    ax2.set_title('(B) RQ2: Method Comparison — JSD ↓')
    ax2.set_ylim(0, 0.65)
    ax2.axhline(y=0.040, ls=':', color='gray', alpha=0.6, linewidth=1)
    ax2.annotate('Ceiling (0.040)', xy=(0.5, 0.040), fontsize=7, color='gray', va='bottom')
    ax2.grid(axis='y', alpha=0.3)

    for i, (m, e) in enumerate(zip(jsd_means, jsd_cis)):
        ax2.text(i, m + e + 0.008, f'{m:.3f}', ha='center', va='bottom', fontsize=7, fontweight='bold')

    # --- Panel C: RQ3 Dbg across compression levels ---
    levels = sorted(rq1['level'].unique())
    dbg_stats = []
    for lv in levels:
        sub = rq1[rq1['level'] == lv]
        dbg_stats.append({
            'level': lv,
            'dbg_free_mean': sub['dbg_free'].mean(),
            'dbg_free_sem': sem(sub['dbg_free']) if len(sub) > 1 else 0,
            'dbg_score_mean': sub['dbg_score'].mean(),
            'dbg_score_sem': sem(sub['dbg_score']) if len(sub) > 1 else 0,
        })
    dbg_df = pd.DataFrame(dbg_stats)

    ax3.fill_between(dbg_df['level'],
                     dbg_df['dbg_free_mean'] - 1.96 * dbg_df['dbg_free_sem'],
                     dbg_df['dbg_free_mean'] + 1.96 * dbg_df['dbg_free_sem'],
                     alpha=0.2, color='tab:blue')
    ax3.plot(dbg_df['level'], dbg_df['dbg_free_mean'], 'o-', color='tab:blue',
             markersize=3, linewidth=1.2, label='Free-looking')
    ax3.fill_between(dbg_df['level'],
                     dbg_df['dbg_score_mean'] - 1.96 * dbg_df['dbg_score_sem'],
                     dbg_df['dbg_score_mean'] + 1.96 * dbg_df['dbg_score_sem'],
                     alpha=0.2, color='tab:orange')
    ax3.plot(dbg_df['level'], dbg_df['dbg_score_mean'], 's-', color='tab:orange',
             markersize=3, linewidth=1.2, label='Scoring')

    ax3.set_xlabel('JPEG Quality Factor')
    ax3.set_ylabel(r'$D_{bg}$ (background mass)')
    ax3.set_title('(C) RQ3: Background Distraction')
    ax3.legend(loc='best', fontsize=9)
    ax3.grid(True, alpha=0.3)

    # Add overall means as dashed lines
    ax3.axhline(y=rq1['dbg_free'].mean(), ls='--', color='tab:blue', alpha=0.4,
                linewidth=0.8)
    ax3.axhline(y=rq1['dbg_score'].mean(), ls='--', color='tab:orange', alpha=0.4,
                linewidth=0.8)
    ax3.annotate(f'Free mean={rq1["dbg_free"].mean():.3f}',
                 xy=(levels[-1], rq1['dbg_free'].mean()), fontsize=7, color='tab:blue')
    ax3.annotate(f'Score mean={rq1["dbg_score"].mean():.3f}',
                 xy=(levels[-1], rq1['dbg_score'].mean()), fontsize=7, color='tab:orange')

    fig.suptitle('RQ2: Task-Aware Saliency Prediction & RQ3: Background Distraction', fontsize=14, y=1.02)
    fig.tight_layout()

    fig.savefig(OUTPUT_DIR / 'fig_rq2_prediction.png')
    plt.close(fig)
    print(f"  Saved: {OUTPUT_DIR / 'fig_rq2_prediction.png'}")


# ═══════════════════════════════════════════════════════════════════════════════
# Fig.6 — Qualitative Case Study
# ═══════════════════════════════════════════════════════════════════════════════
def generate_fig6():
    """Qualitative examples: best, median, worst by JSD improvement."""
    print("Generating Fig.6: Qualitative case study...")

    from config import config
    from data_loader import DataLoader
    from artifact_maps import ArtifactMapGenerator
    from metrics import SaliencyMetrics

    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)

    # Normalization helper
    def normalize_to_prob(m):
        m = np.maximum(m, 0).astype(np.float64)
        s = np.sum(m) + 1e-12
        return m / s

    # SC-TAS predict
    def sctas_predict(p_free, a_map, alpha=1.0, beta=0.3, tau=0.83, eta=0.9):
        for _ in range(50):
            raw = alpha * p_free + beta * a_map
            raw = np.maximum(raw, 0)
            total = np.sum(raw) + 1e-12
            p_hat = raw / total
            cc = np.corrcoef(p_hat.flatten(), p_free.flatten())[0, 1]
            if np.isnan(cc) or cc >= tau:
                break
            beta *= eta
        return p_hat

    # Case study contents (from content_level_analysis ranked by jsd_improvement)
    cases = {
        'Best (dog)': 'dog',
        'Median (tourist_shore)': 'tourist_shore',
        'Worst (swan_ice)': 'swan_ice',
    }

    # We need RGB images for display — load them separately
    # But we also need YCrCb images for artifact computation (which DataLoader default provides)
    import cv2

    # For each case, pick the lowest QF (most distorted)
    fig, axes = plt.subplots(3, 5, figsize=(18, 10.5))

    for row_idx, (label, content) in enumerate(cases.items()):
        data = loader.get_data_for_content(content, preprocess_saliency=True)
        levels = sorted(data['levels'])
        # Pick lowest QF = most distorted
        lv = levels[0]

        img_ycrcb = data['images'][lv]
        p_free = data['saliency_freelook'][lv]
        p_score = data['saliency_scoring'][lv]

        # Compute NR artifact map and TAS NR prediction
        a_nr = artifact_gen.compute_nr_artifact(img_ycrcb, use_blockiness=True, use_dct=True, use_ringing=True)
        a_nr_prob = normalize_to_prob(a_nr)
        p_tas_nr = sctas_predict(p_free, a_nr_prob)

        # Error map: |prediction - ground truth|
        error = np.abs(p_tas_nr - p_score)

        # Compute metrics
        cc_val = SaliencyMetrics.pearson_correlation(p_tas_nr, p_score)
        jsd_val = SaliencyMetrics.jensen_shannon_divergence(p_tas_nr, p_score)

        # Convert YCrCb → BGR → RGB for display
        img_bgr = cv2.cvtColor(img_ycrcb.astype(np.float32), cv2.COLOR_YCrCb2BGR)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_rgb = np.clip(img_rgb, 0, 255).astype(np.uint8)

        # Column 0: Compressed stimulus
        ax = axes[row_idx, 0]
        ax.imshow(img_rgb)
        ax.set_title(f'{label}\nQF={lv}', fontsize=10, fontweight='bold')
        ax.axis('off')

        # Column 1: FreeLook prior P^F
        ax = axes[row_idx, 1]
        ax.imshow(p_free, cmap='jet', interpolation='bilinear')
        ax.set_title('Free-looking prior $P^F$', fontsize=9)
        ax.axis('off')

        # Column 2: Scoring ground truth P^Q
        ax = axes[row_idx, 2]
        ax.imshow(p_score, cmap='jet', interpolation='bilinear')
        ax.set_title('Scoring GT $P^Q$', fontsize=9)
        ax.axis('off')

        # Column 3: TAS NR prediction
        ax = axes[row_idx, 3]
        ax.imshow(p_tas_nr, cmap='jet', interpolation='bilinear')
        ax.set_title(f'SC-TAS NR\nCC={cc_val:.3f}, JSD={jsd_val:.3f}', fontsize=9)
        ax.axis('off')

        # Column 4: Error map
        ax = axes[row_idx, 4]
        im = ax.imshow(error, cmap='hot', interpolation='bilinear')
        ax.set_title('|Prediction − GT|', fontsize=9)
        ax.axis('off')

    # Add column labels at top
    col_titles = ['Stimulus', 'Free-look prior', 'Scoring GT', 'SC-TAS NR prediction', 'Absolute error']
    for j, title in enumerate(col_titles):
        axes[0, j].annotate(title, xy=(0.5, 1.15), xycoords='axes fraction',
                           fontsize=10, ha='center', va='bottom', fontweight='bold')

    fig.suptitle('Qualitative Examples: Best, Median, Worst by JSD Improvement of TAS NR',
                 fontsize=14, y=1.02)
    fig.tight_layout()

    fig.savefig(OUTPUT_DIR / 'fig_qualitative_cases.png')
    plt.close(fig)
    print(f"  Saved: {OUTPUT_DIR / 'fig_qualitative_cases.png'}")


# ═══════════════════════════════════════════════════════════════════════════════
# Fig.7 — Content-Level Heatmap
# ═══════════════════════════════════════════════════════════════════════════════
def generate_fig7():
    """Content-level heatmap: 40 contents × methods (CC)."""
    print("Generating Fig.7: Content-level heatmap...")

    cl = pd.read_csv(RESULTS_MAIN / 'content_level_analysis.csv')
    lb = pd.read_csv(RESULTS_CROSS / 'learning_baselines_r2.csv')

    # Load U-Net-lite R2 results
    unet_lb = pd.read_csv(PROJECT_ROOT / 'results' / 'unet_lite_baseline' / 'unet_lite_r2_loco.csv')

    # Add LB1/LB2 per-content means to content_level
    lb_content = lb.groupby('content').agg({
        'ridge_cc': 'mean',
        'mlp_cc': 'mean',
    }).reset_index()

    # Add LB3 per-content means
    unet_content = unet_lb.groupby('content').agg({
        'unet_cc': 'mean',
    }).reset_index()

    cl = cl.merge(lb_content, on='content', how='left')
    cl = cl.merge(unet_content, on='content', how='left')

    # Sort by TAS NR CC
    cl = cl.sort_values('tas_nr_cc', ascending=True).reset_index(drop=True)

    # Build matrix: contents × methods
    method_cols = {
        'Free-look':    'freelook_cc',
        'Art. (FR)':    'artifact_fr_cc',
        'Art. (NR)':    'artifact_nr_cc',
        'Mix (FR)':     'mixture_fr_cc',
        'Mix (NR)':     'mixture_nr_cc',
        'TAS FR':       'tas_fr_cc',
        'TAS NR':       'tas_nr_cc',
        'LB1 (Ridge)':  'ridge_cc',
        'LB2 (MLP)':    'mlp_cc',
        'LB3 (U-Net)':  'unet_cc',
    }

    data_matrix = np.zeros((len(cl), len(method_cols)))
    for j, (name, col) in enumerate(method_cols.items()):
        if col in cl.columns:
            data_matrix[:, j] = cl[col].values
        else:
            data_matrix[:, j] = np.nan

    fig, ax = plt.subplots(figsize=(11, 14))

    # Custom colormap: red for low, white for mid, green for high
    cmap = LinearSegmentedColormap.from_list('rg',
           [(0.8, 0.2, 0.2), (1.0, 1.0, 0.8), (0.2, 0.7, 0.3)], N=256)

    im = ax.imshow(data_matrix, aspect='auto', cmap=cmap,
                   vmin=-0.15, vmax=1.0, interpolation='nearest')

    # Axis labels
    ax.set_xticks(range(len(method_cols)))
    ax.set_xticklabels(list(method_cols.keys()), rotation=45, ha='right', fontsize=9)
    ax.set_yticks(range(len(cl)))
    ax.set_yticklabels(cl['content'].values, fontsize=7)
    ax.set_xlabel('Method', fontsize=11)
    ax.set_ylabel('Content (sorted by TAS NR CC)', fontsize=11)

    # Add text annotations
    for i in range(len(cl)):
        for j in range(len(method_cols)):
            val = data_matrix[i, j]
            if np.isnan(val):
                continue
            color = 'white' if val < 0.2 or val > 0.85 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=5, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('Mean CC (per content, averaged over 4 QF levels)', fontsize=10)

    ax.set_title('Content Difficulty and Method Robustness\n(40 contents, sorted by SC-TAS NR performance)',
                 fontsize=13)

    fig.tight_layout()

    fig.savefig(OUTPUT_DIR / 'fig_b1e_content_heatmap.png')
    plt.close(fig)
    print(f"  Saved: {OUTPUT_DIR / 'fig_b1e_content_heatmap.png'}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=" * 70)
    print("PAPER FIGURE GENERATION — FROM REAL EXPERIMENTAL DATA")
    print("=" * 70)

    generate_fig3()
    generate_fig4()
    generate_fig5()
    generate_fig6()
    generate_fig7()

    print("\n" + "=" * 70)
    print("ALL FIGURES GENERATED SUCCESSFULLY")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)
