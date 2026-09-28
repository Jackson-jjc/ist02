"""Canonical implementation of Stability-Constrained Task-Adaptive Saliency."""

from __future__ import annotations

import numpy as np


class SCTAS:
    """Prior-dominated linear fusion with a correlation stability constraint."""

    def __init__(self, alpha: float = 1.0, beta: float = 0.3,
                 tau: float = 0.83, eta: float = 0.9):
        self.alpha = alpha
        self.beta = beta
        self.tau = tau
        self.eta = eta

    def predict(self, p_free: np.ndarray, a_map: np.ndarray) -> np.ndarray:
        """Predict scoring saliency using the paper's shrinkage rule."""
        p_hat, _, _ = self.predict_count_shrinks(p_free, a_map)
        return p_hat

    def predict_count_shrinks(self, p_free: np.ndarray, a_map: np.ndarray):
        """Return prediction, shrink count, and the effective artifact weight."""
        alpha, beta = self.alpha, self.beta
        eps = 1e-12
        n_shrinks = 0
        for _ in range(50):
            raw = np.maximum(alpha * p_free + beta * a_map, 0)
            p_hat = raw / (np.sum(raw) + eps)
            prior_cc = float(np.corrcoef(p_hat.ravel(), p_free.ravel())[0, 1])
            if np.isnan(prior_cc) or prior_cc >= self.tau:
                break
            beta *= self.eta
            n_shrinks += 1
        return p_hat, n_shrinks, beta

    def predict_with_stats(self, p_free: np.ndarray, a_map: np.ndarray):
        """Return prediction and diagnostic values used by the stress test."""
        prediction, n_shrinks, final_beta = self.predict_count_shrinks(
            p_free, a_map)
        if n_shrinks == 50:
            raw = np.maximum(self.alpha * p_free + final_beta * a_map, 0)
            prediction = raw / (np.sum(raw) + 1e-12)
        prior_cc = float(np.corrcoef(
            prediction.ravel(), p_free.ravel())[0, 1])
        return prediction, n_shrinks, final_beta, prior_cc
