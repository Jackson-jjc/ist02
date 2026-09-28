#!/usr/bin/env python3
"""Data-free smoke test for the public SC-TAS implementation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from artifact_maps import ArtifactMapGenerator
from config import config
from data_loader import DataLoader
from metrics import SaliencyMetrics
from sctas import SCTAS


def normalise(array: np.ndarray) -> np.ndarray:
    array = np.maximum(array.astype(np.float64), 0)
    return array / (array.sum() + 1e-12)


def main() -> int:
    rng = np.random.RandomState(42)
    height, width = 64, 64
    reference = rng.randint(0, 256, (height, width, 3)).astype(np.float32)
    distorted = reference.copy()
    distorted[:, 31:33, 0] = np.clip(distorted[:, 31:33, 0] + 24, 0, 255)

    generator = ArtifactMapGenerator(config)
    nr_map = generator.compute_nr_artifact(distorted)
    fr_map = generator.compute_fr_artifact(reference, distorted)
    nr_prob = generator.normalize_artifact_to_probability(nr_map)
    fr_prob = generator.normalize_artifact_to_probability(fr_map)

    for name, array in (("NR", nr_prob), ("FR", fr_prob)):
        assert array.shape == (height, width), f"{name} shape mismatch: {array.shape}"
        assert np.isfinite(array).all(), f"{name} contains non-finite values"
        assert np.isclose(array.sum(), 1.0, atol=1e-6), f"{name} is not normalised"

    prior = normalise(rng.random((height, width)))
    prediction = SCTAS(alpha=1.0, beta=0.3, tau=0.83, eta=0.9).predict(
        prior, nr_prob)
    assert np.isfinite(SaliencyMetrics.pearson_correlation(prediction, prior))
    assert SaliencyMetrics.jensen_shannon_divergence(prior, prior) < 1e-12

    loader = DataLoader(config)
    content, level = loader.extract_content_and_level("arab_mountain_jpgq_(18).jpg")
    assert (content, level) == ("arab_mountain", 18)

    print("SC-TAS data-free smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
