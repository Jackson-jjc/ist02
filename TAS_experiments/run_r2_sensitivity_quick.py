#!/usr/bin/env python3
import logging
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics


RESULTS_DIR = PROJECT_ROOT / "results" / "reviewer_revision_quick"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def normalize_prob(arr):
    arr = np.maximum(arr, 0).astype(np.float64)
    return arr / (np.sum(arr) + 1e-12)


def resize_prob(arr, size=(64, 64)):
    out = cv2.resize(arr.astype(np.float32), size, interpolation=cv2.INTER_LINEAR)
    return normalize_prob(out)


def main():
    loader = DataLoader(config)
    artifact_gen = ArtifactMapGenerator(config)
    contents = loader.get_unique_contents()

    logger.info("Loading R2 data for quick sensitivity sweep...")
    samples = []
    for content in contents:
        data = loader.get_data_for_content(content, preprocess_saliency=True)
        for level in data["levels"]:
            p_free = data["saliency_freelook"][level]
            p_score = data["saliency_scoring"][level]
            if p_free is None or p_score is None:
                continue
            comps = artifact_gen.compute_nr_artifact_components(data["images"][level])
            samples.append({
                "p_free": resize_prob(p_free),
                "p_score": resize_prob(p_score),
                "artifact": resize_prob(comps["combined"]),
            })
    logger.info(f"Loaded {len(samples)} samples")

    rows = []

    def eval_setting(alpha, beta, sweep):
        cc_vals, jsd_vals = [], []
        for s in samples:
            pred = normalize_prob(alpha * s["p_free"] + beta * s["artifact"])
            cc_vals.append(SaliencyMetrics.pearson_correlation(pred, s["p_score"]))
            jsd_vals.append(SaliencyMetrics.jensen_shannon_divergence(pred, s["p_score"]))
        rows.append({
            "sweep": sweep,
            "alpha": alpha,
            "beta": beta,
            "mean_cc": float(np.mean(cc_vals)),
            "mean_jsd": float(np.mean(jsd_vals)),
        })

    for alpha in np.round(np.arange(0.5, 2.51, 0.25), 2):
        logger.info(f"alpha sweep alpha={alpha:.2f}")
        eval_setting(alpha, 0.30, "alpha")

    for beta in np.round(np.arange(0.0, 1.01, 0.05), 2):
        logger.info(f"beta sweep beta={beta:.2f}")
        eval_setting(1.0, beta, "beta")

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / "parameter_sensitivity_r2_quick.csv", index=False)

    df_alpha = df[df["sweep"] == "alpha"].copy()
    df_beta = df[df["sweep"] == "beta"].copy()
    summary = pd.DataFrame([
        {"setting": "alpha_best_jsd", **df_alpha.loc[df_alpha["mean_jsd"].idxmin()].to_dict()},
        {"setting": "alpha_best_cc", **df_alpha.loc[df_alpha["mean_cc"].idxmax()].to_dict()},
        {"setting": "beta_best_jsd", **df_beta.loc[df_beta["mean_jsd"].idxmin()].to_dict()},
        {"setting": "beta_best_cc", **df_beta.loc[df_beta["mean_cc"].idxmax()].to_dict()},
        {"setting": "default", **df_beta[np.isclose(df_beta["beta"], 0.30)].iloc[0].to_dict()},
    ])
    summary.to_csv(RESULTS_DIR / "parameter_sensitivity_r2_quick_summary.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ax = axes[0]
    ax2 = ax.twinx()
    ax.plot(df_alpha["alpha"], df_alpha["mean_cc"], marker="o", color="#4C78A8")
    ax2.plot(df_alpha["alpha"], df_alpha["mean_jsd"], marker="s", color="#F58518")
    ax.set_title(r"$\alpha$ sweep on full R2")
    ax.set_xlabel(r"$\alpha$")
    ax.set_ylabel("CC", color="#4C78A8")
    ax2.set_ylabel("JSD", color="#F58518")
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax2 = ax.twinx()
    ax.plot(df_beta["beta"], df_beta["mean_cc"], marker="o", color="#4C78A8")
    ax2.plot(df_beta["beta"], df_beta["mean_jsd"], marker="s", color="#F58518")
    ax.set_title(r"$\beta$ sweep on full R2")
    ax.set_xlabel(r"$\beta$")
    ax.set_ylabel("CC", color="#4C78A8")
    ax2.set_ylabel("JSD", color="#F58518")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "fig_parameter_sensitivity_r2_quick.png", dpi=220, bbox_inches="tight")

    logger.info("Quick sensitivity sweep complete")


if __name__ == "__main__":
    main()
