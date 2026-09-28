#!/usr/bin/env python3
"""
Targeted ablation and sensitivity experiments for SC-TAS.

Outputs:
  1. Single-component ablation on R2
  2. Full-R2 alpha/beta sensitivity analysis
  3. Stability-constraint stress test
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import cv2

import sys
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics
from sctas import SCTAS


RESULTS_DIR = config.RESULTS_DIR / "ablation_sensitivity"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
SENSITIVITY_SIZE = (64, 64)

log_file = RESULTS_DIR / "ablation_sensitivity.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def normalize_to_prob(arr: np.ndarray) -> np.ndarray:
    arr = np.maximum(arr, 0).astype(np.float64)
    return arr / (np.sum(arr) + 1e-12)


def resize_prob_map(arr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    resized = cv2.resize(arr.astype(np.float32), (width, height), interpolation=cv2.INTER_LINEAR)
    return normalize_to_prob(resized)


def sim_metric(pred: np.ndarray, target: np.ndarray) -> float:
    p1 = normalize_to_prob(pred).ravel()
    p2 = normalize_to_prob(target).ravel()
    return float(np.sum(np.minimum(p1, p2)))


def kl_divergence(pred: np.ndarray, target: np.ndarray) -> float:
    eps = 1e-12
    p = normalize_to_prob(target).ravel()
    q = normalize_to_prob(pred).ravel()
    p = np.maximum(p, eps)
    q = np.maximum(q, eps)
    return float(np.sum(p * np.log(p / q)))


def auc_top20(pred: np.ndarray, target: np.ndarray) -> float:
    pred_flat = pred.ravel()
    target_flat = target.ravel()
    threshold = np.percentile(target_flat, 80)
    positives = (target_flat >= threshold).astype(np.int32)
    pos = int(np.sum(positives))
    neg = len(positives) - pos
    if pos == 0 or neg == 0:
        return 0.5
    order = np.argsort(-pred_flat)
    sorted_pos = positives[order]
    tp = np.cumsum(sorted_pos)
    fp = np.arange(1, len(order) + 1) - tp
    tpr = tp / pos
    fpr = fp / neg
    return float(np.clip(np.trapezoid(tpr, fpr), 0.0, 1.0))


def summarize_group(df: pd.DataFrame, name_col: str) -> pd.DataFrame:
    rows = []
    for name, sub in df.groupby(name_col, sort=False):
        rows.append({
            name_col: name,
            "CC_mean": sub["cc"].mean(),
            "CC_std": sub["cc"].std(),
            "JSD_mean": sub["jsd"].mean(),
            "JSD_std": sub["jsd"].std(),
            "SIM_mean": sub["sim"].mean(),
            "SIM_std": sub["sim"].std(),
            "AUC_mean": sub["auc_top20"].mean(),
            "AUC_std": sub["auc_top20"].std(),
            "KL_mean": sub["kl"].mean(),
            "KL_std": sub["kl"].std(),
            "activation_rate_pct": 100.0 * sub["activated"].mean() if "activated" in sub else np.nan,
        })
    return pd.DataFrame(rows)


def plot_component_ablation(df_summary: pd.DataFrame, save_path: Path):
    labels = df_summary["setting"].tolist()
    x = np.arange(len(labels))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].bar(x, df_summary["CC_mean"], yerr=df_summary["CC_std"], color="#4C78A8", capsize=3)
    axes[0].set_title("Component Ablation on R2: CC")
    axes[0].set_ylabel("Mean CC")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=35, ha="right")

    axes[1].bar(x, df_summary["JSD_mean"], yerr=df_summary["JSD_std"], color="#F58518", capsize=3)
    axes[1].set_title("Component Ablation on R2: JSD")
    axes[1].set_ylabel("Mean JSD")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=35, ha="right")

    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_parameter_sensitivity_curves(df_alpha: pd.DataFrame, df_beta: pd.DataFrame, save_path: Path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    ax = axes[0]
    ax2 = ax.twinx()
    ax.plot(df_alpha["alpha"], df_alpha["mean_cc"], marker="o", color="#4C78A8", linewidth=2)
    ax2.plot(df_alpha["alpha"], df_alpha["mean_jsd"], marker="s", color="#F58518", linewidth=2)
    ax.set_title(r"Full-R2 Sensitivity: $\alpha$ sweep ($\beta=0.3$)")
    ax.set_xlabel(r"$\alpha$")
    ax.set_ylabel("Mean CC", color="#4C78A8")
    ax2.set_ylabel("Mean JSD", color="#F58518")
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax2 = ax.twinx()
    ax.plot(df_beta["beta"], df_beta["mean_cc"], marker="o", color="#4C78A8", linewidth=2)
    ax2.plot(df_beta["beta"], df_beta["mean_jsd"], marker="s", color="#F58518", linewidth=2)
    ax.set_title(r"Full-R2 Sensitivity: $\beta$ sweep ($\alpha=1.0$)")
    ax.set_xlabel(r"$\beta$")
    ax.set_ylabel("Mean CC", color="#4C78A8")
    ax2.set_ylabel("Mean JSD", color="#F58518")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_stability_stress(df_summary: pd.DataFrame, save_path: Path):
    betas = df_summary["beta"].to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    axes[0].plot(betas, df_summary["activation_rate_pct"], marker="o", color="#E45756", linewidth=2)
    axes[0].set_title("Constraint Activation Rate")
    axes[0].set_xlabel(r"Initial $\beta$")
    axes[0].set_ylabel("Activation rate (%)")
    axes[0].set_ylim(0, 105)
    axes[0].grid(alpha=0.3)

    axes[1].plot(betas, df_summary["task_cc_no_constraint"], marker="o", label="No constraint", color="#72B7B2", linewidth=2)
    axes[1].plot(betas, df_summary["task_cc_with_constraint"], marker="o", label=r"With $\tau=0.83$", color="#4C78A8", linewidth=2)
    axes[1].set_title("Task CC Under Increasing Artifact Weight")
    axes[1].set_xlabel(r"Initial $\beta$")
    axes[1].set_ylabel("Mean task CC")
    axes[1].grid(alpha=0.3)
    axes[1].legend(frameon=False)

    fig.tight_layout()
    fig.savefig(save_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_component_map(components: dict, names: list[str]) -> np.ndarray:
    if not names:
        return None
    weights = {"blockiness": 0.4, "dct": 0.4, "ringing": 0.2}
    fused = np.zeros_like(components["combined"], dtype=np.float64)
    for name in names:
        fused += weights[name] * components[name]
    return normalize_to_prob(fused)


def main():
    t0 = time.time()
    logger.info("=" * 80)
    logger.info("ABLATION AND SENSITIVITY EXPERIMENTS")
    logger.info(f"Start: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)
    contents = loader.get_unique_contents()

    logger.info("Loading all R2 data and component maps...")
    samples = []
    for content in contents:
        data = loader.get_data_for_content(content, preprocess_saliency=True)
        for level in data["levels"]:
            p_free = data["saliency_freelook"][level]
            p_score = data["saliency_scoring"][level]
            if p_free is None or p_score is None:
                continue
            img = data["images"][level]
            components = artifact_gen.compute_nr_artifact_components(img)
            for key in components:
                components[key] = normalize_to_prob(components[key])
            samples.append({
                "content": content,
                "level": level,
                "p_free": p_free,
                "p_score": p_score,
                "components": components,
                "artifact_full": components["combined"],
            })
    logger.info(f"Loaded {len(samples)} R2 samples")
    for sample in samples:
        sample["p_free_sens"] = resize_prob_map(sample["p_free"], SENSITIVITY_SIZE)
        sample["p_score_sens"] = resize_prob_map(sample["p_score"], SENSITIVITY_SIZE)
        sample["artifact_full_sens"] = resize_prob_map(sample["artifact_full"], SENSITIVITY_SIZE)

    # ------------------------------------------------------------------
    # 1) Single-component ablation
    # ------------------------------------------------------------------
    ablation_all_path = RESULTS_DIR / "component_ablation_all.csv"
    ablation_summary_path = RESULTS_DIR / "component_ablation_summary.csv"
    if ablation_all_path.exists() and ablation_summary_path.exists():
        logger.info("Reusing existing single-component ablation outputs")
        df_ablation_all = pd.read_csv(ablation_all_path)
        df_ablation_summary = pd.read_csv(ablation_summary_path)
    else:
        logger.info("Running single-component ablation...")
        sctas_default = SCTAS(alpha=1.0, beta=0.3, tau=0.83, eta=0.9)
        settings = [
            ("Prior only", []),
            ("Blockiness only", ["blockiness"]),
            ("DCT only", ["dct"]),
            ("Ringing only", ["ringing"]),
            ("Blockiness + DCT", ["blockiness", "dct"]),
            ("Blockiness + Ringing", ["blockiness", "ringing"]),
            ("DCT + Ringing", ["dct", "ringing"]),
            ("SC-TAS NR (all)", ["blockiness", "dct", "ringing"]),
        ]

        ablation_rows = []
        for setting_name, component_names in settings:
            for sample in samples:
                if not component_names:
                    pred = sample["p_free"]
                    n_shrinks = 0
                    final_beta = 0.0
                    prior_cc = 1.0
                else:
                    a_map = build_component_map(sample["components"], component_names)
                    pred, n_shrinks, final_beta, prior_cc = sctas_default.predict_with_stats(sample["p_free"], a_map)

                ablation_rows.append({
                    "setting": setting_name,
                    "content": sample["content"],
                    "level": sample["level"],
                    "cc": SaliencyMetrics.pearson_correlation(pred, sample["p_score"]),
                    "jsd": SaliencyMetrics.jensen_shannon_divergence(pred, sample["p_score"]),
                    "sim": sim_metric(pred, sample["p_score"]),
                    "auc_top20": auc_top20(pred, sample["p_score"]),
                    "kl": kl_divergence(pred, sample["p_score"]),
                    "activated": int(n_shrinks > 0),
                    "final_beta": final_beta,
                    "prior_cc": prior_cc,
                })

        df_ablation_all = pd.DataFrame(ablation_rows)
        df_ablation_all.to_csv(ablation_all_path, index=False)
        df_ablation_summary = summarize_group(df_ablation_all, "setting")
        df_ablation_summary.to_csv(ablation_summary_path, index=False)
        plot_component_ablation(df_ablation_summary, RESULTS_DIR / "fig_component_ablation_r2.png")
        logger.info("Single-component ablation saved")

    # ------------------------------------------------------------------
    # 2) Full-R2 parameter sensitivity
    # ------------------------------------------------------------------
    logger.info("Running full-R2 parameter sensitivity...")
    alpha_range = np.round(np.arange(0.5, 2.51, 0.25), 2)
    beta_range = np.round(np.arange(0.0, 1.01, 0.05), 2)

    sensitivity_rows = []

    def evaluate_setting(alpha: float, beta: float, sweep_name: str):
        cc_vals = []
        jsd_vals = []
        sim_vals = []
        kl_vals = []
        prior_cc_vals = []
        for sample in samples:
            raw = np.maximum(alpha * sample["p_free_sens"] + beta * sample["artifact_full_sens"], 0)
            pred = raw / (np.sum(raw) + 1e-12)
            cc_vals.append(SaliencyMetrics.pearson_correlation(pred, sample["p_score_sens"]))
            jsd_vals.append(SaliencyMetrics.jensen_shannon_divergence(pred, sample["p_score_sens"]))
            sim_vals.append(sim_metric(pred, sample["p_score_sens"]))
            kl_vals.append(kl_divergence(pred, sample["p_score_sens"]))
            prior_cc_vals.append(float(np.corrcoef(pred.ravel(), sample["p_free_sens"].ravel())[0, 1]))
        sensitivity_rows.append({
            "sweep": sweep_name,
            "alpha": alpha,
            "beta": beta,
            "mean_cc": float(np.mean(cc_vals)),
            "mean_jsd": float(np.mean(jsd_vals)),
            "mean_sim": float(np.mean(sim_vals)),
            "mean_kl": float(np.mean(kl_vals)),
            "mean_prior_cc": float(np.mean(prior_cc_vals)),
        })

    for alpha in alpha_range:
        logger.info(f"  Alpha sweep: alpha={alpha:.2f}, beta=0.30")
        evaluate_setting(alpha=alpha, beta=0.30, sweep_name="alpha")

    for beta in beta_range:
        logger.info(f"  Beta sweep: alpha=1.00, beta={beta:.2f}")
        evaluate_setting(alpha=1.00, beta=beta, sweep_name="beta")

    df_sensitivity = pd.DataFrame(sensitivity_rows)
    df_sensitivity.to_csv(RESULTS_DIR / "parameter_sensitivity_r2.csv", index=False)

    df_alpha = df_sensitivity[df_sensitivity["sweep"] == "alpha"].copy()
    df_beta = df_sensitivity[df_sensitivity["sweep"] == "beta"].copy()

    best_alpha_jsd = df_alpha.loc[df_alpha["mean_jsd"].idxmin()]
    best_alpha_cc = df_alpha.loc[df_alpha["mean_cc"].idxmax()]
    best_beta_jsd = df_beta.loc[df_beta["mean_jsd"].idxmin()]
    best_beta_cc = df_beta.loc[df_beta["mean_cc"].idxmax()]
    default_row = df_beta[df_beta["beta"] == 0.30].iloc[0]

    df_sensitivity_summary = pd.DataFrame([
        {"setting": "Alpha sweep best JSD", **best_alpha_jsd.to_dict()},
        {"setting": "Alpha sweep best CC", **best_alpha_cc.to_dict()},
        {"setting": "Beta sweep best JSD", **best_beta_jsd.to_dict()},
        {"setting": "Beta sweep best CC", **best_beta_cc.to_dict()},
        {"setting": "Default (alpha=1.0, beta=0.3)", **default_row.to_dict()},
    ])
    df_sensitivity_summary.to_csv(RESULTS_DIR / "parameter_sensitivity_r2_summary.csv", index=False)
    plot_parameter_sensitivity_curves(df_alpha, df_beta, RESULTS_DIR / "fig_parameter_sensitivity_r2.png")
    logger.info("Full-R2 parameter sensitivity saved")

    # ------------------------------------------------------------------
    # 3) Stability stress test
    # ------------------------------------------------------------------
    logger.info("Running stability stress test...")
    beta_values = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    stress_rows = []
    default_margin_rows = []

    for beta in beta_values:
        model = SCTAS(alpha=1.0, beta=beta, tau=0.83, eta=0.9)
        no_constraint_cc = []
        no_constraint_jsd = []
        with_constraint_cc = []
        with_constraint_jsd = []
        activation_flags = []
        final_betas = []
        raw_prior_ccs = []

        for sample in samples:
            raw = np.maximum(sample["p_free"] + beta * sample["artifact_full"], 0)
            pred_raw = raw / (np.sum(raw) + 1e-12)
            raw_prior_cc = float(np.corrcoef(pred_raw.ravel(), sample["p_free"].ravel())[0, 1])

            pred_constrained, n_shrinks, final_beta, _ = model.predict_with_stats(sample["p_free"], sample["artifact_full"])

            no_constraint_cc.append(SaliencyMetrics.pearson_correlation(pred_raw, sample["p_score"]))
            no_constraint_jsd.append(SaliencyMetrics.jensen_shannon_divergence(pred_raw, sample["p_score"]))
            with_constraint_cc.append(SaliencyMetrics.pearson_correlation(pred_constrained, sample["p_score"]))
            with_constraint_jsd.append(SaliencyMetrics.jensen_shannon_divergence(pred_constrained, sample["p_score"]))
            activation_flags.append(int(n_shrinks > 0))
            final_betas.append(final_beta)
            raw_prior_ccs.append(raw_prior_cc)

            if beta == 0.3:
                default_margin_rows.append({
                    "content": sample["content"],
                    "level": sample["level"],
                    "raw_prior_cc": raw_prior_cc,
                    "below_tau_083": int(raw_prior_cc < 0.83),
                })

        stress_rows.append({
            "beta": beta,
            "raw_prior_cc_mean": float(np.mean(raw_prior_ccs)),
            "raw_prior_cc_min": float(np.min(raw_prior_ccs)),
            "raw_prior_cc_max": float(np.max(raw_prior_ccs)),
            "task_cc_no_constraint": float(np.mean(no_constraint_cc)),
            "task_jsd_no_constraint": float(np.mean(no_constraint_jsd)),
            "task_cc_with_constraint": float(np.mean(with_constraint_cc)),
            "task_jsd_with_constraint": float(np.mean(with_constraint_jsd)),
            "delta_cc": float(np.mean(with_constraint_cc) - np.mean(no_constraint_cc)),
            "delta_jsd": float(np.mean(with_constraint_jsd) - np.mean(no_constraint_jsd)),
            "activation_rate_pct": float(100.0 * np.mean(activation_flags)),
            "mean_final_beta": float(np.mean(final_betas)),
        })

    df_stress = pd.DataFrame(stress_rows)
    df_stress.to_csv(RESULTS_DIR / "stability_stress_summary.csv", index=False)

    df_default_margin = pd.DataFrame(default_margin_rows)
    df_default_margin.to_csv(RESULTS_DIR / "stability_default_margin.csv", index=False)
    plot_stability_stress(df_stress, RESULTS_DIR / "fig_stability_stress.png")
    logger.info("Stability stress test saved")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "component_ablation_best_jsd": df_ablation_summary.sort_values("JSD_mean").iloc[0].to_dict(),
        "component_ablation_best_cc": df_ablation_summary.sort_values("CC_mean", ascending=False).iloc[0].to_dict(),
        "parameter_sensitivity": {
            "alpha_sweep_best_cc": best_alpha_cc.to_dict(),
            "alpha_sweep_best_jsd": best_alpha_jsd.to_dict(),
            "beta_sweep_best_cc": best_beta_cc.to_dict(),
            "beta_sweep_best_jsd": best_beta_jsd.to_dict(),
            "default": default_row.to_dict(),
        },
        "stability_default_beta": {
            "raw_prior_cc_mean": float(df_default_margin["raw_prior_cc"].mean()),
            "raw_prior_cc_min": float(df_default_margin["raw_prior_cc"].min()),
            "activation_count": int(df_default_margin["below_tau_083"].sum()),
            "n_samples": int(len(df_default_margin)),
        },
        "stability_stress": df_stress.to_dict(orient="records"),
        "runtime_seconds": time.time() - t0,
    }
    with open(RESULTS_DIR / "ablation_sensitivity_summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"All outputs saved to {RESULTS_DIR}")
    logger.info(f"Runtime: {time.time() - t0:.1f}s")
    logger.info("=" * 80)
    logger.info("ABLATION AND SENSITIVITY EXPERIMENTS COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
