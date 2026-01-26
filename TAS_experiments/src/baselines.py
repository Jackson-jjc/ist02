"""
Baseline comparison methods for TAS evaluation

Three baselines to demonstrate TAS superiority:
1. Saliency-weighted SSIM: SSIM weighted by saliency importance
2. BRISQUE-based weighting: General image quality based weighting
3. Simple linear regression: Lightweight baseline
"""
import numpy as np
from typing import Tuple
import cv2
import logging

logger = logging.getLogger(__name__)


class BaselineComparison:
    """Implement comparison baselines"""
    
    @staticmethod
    def saliency_weighted_ssim(img_reference: np.ndarray,
                              img_distorted: np.ndarray,
                              saliency_map: np.ndarray,
                              win_size: int = 11) -> np.ndarray:
        """
        Baseline 1: Saliency-Weighted SSIM
        
        Compute SSIM and weight by saliency importance.
        Higher saliency regions have higher weights.
        
        Prediction = weighted_SSIM (as proxy for perceived quality)
        """
        # Extract luminance
        if len(img_reference.shape) == 3:
            ref = cv2.cvtColor(img_reference.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
            dist = cv2.cvtColor(img_distorted.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            ref = img_reference.astype(np.float32)
            dist = img_distorted.astype(np.float32)
        
        ref = ref / 255.0 if ref.max() > 1 else ref
        dist = dist / 255.0 if dist.max() > 1 else dist
        
        # Compute SSIM
        window = cv2.getGaussianKernel(win_size, 1.5)
        window = window @ window.T
        
        mu1 = cv2.filter2D(ref, -1, window)
        mu2 = cv2.filter2D(dist, -1, window)
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        
        sigma1_sq = cv2.filter2D(ref ** 2, -1, window) - mu1_sq
        sigma2_sq = cv2.filter2D(dist ** 2, -1, window) - mu2_sq
        sigma12 = cv2.filter2D(ref * dist, -1, window) - mu1_mu2
        
        c1 = (0.01 * 255) ** 2
        c2 = (0.03 * 255) ** 2
        
        ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / \
                   ((mu1_sq + mu2_sq + c1) * (sigma2_sq + sigma2_sq + c2))
        
        # Normalize saliency to [0, 1]
        sal_norm = saliency_map / (np.sum(saliency_map) + 1e-12)
        
        # Weight SSIM by saliency: higher saliency regions matter more
        # Convert SSIM to quality metric (higher SSIM = better)
        ssim_quality = np.clip((ssim_map + 1) / 2, 0, 1)  # Map [-1, 1] to [0, 1]
        
        # Saliency-weighted quality
        weighted_quality = ssim_quality * sal_norm
        
        # Normalize as probability distribution
        prediction = weighted_quality / (np.sum(weighted_quality) + 1e-12)
        
        return np.clip(prediction, 0, 1)
    
    @staticmethod
    def brisque_weighting(img_distorted: np.ndarray) -> np.ndarray:
        """
        Baseline 2: BRISQUE-based Weighting
        
        Simple approximation: distortion patterns similar to BRISQUE
        High distortion regions → low saliency (attention avoidance)
        
        This is a simplified version using gradient statistics
        """
        # Extract luminance
        if len(img_distorted.shape) == 3:
            lum = cv2.cvtColor(img_distorted.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            lum = img_distorted.astype(np.float32)
        
        # Compute local variance (BRISQUE uses MSCN coefficients, we simplify)
        kernel = cv2.getGaussianKernel(7, 1.0)
        kernel_2d = kernel @ kernel.T
        
        mean = cv2.filter2D(lum, -1, kernel_2d)
        mean_sq = cv2.filter2D(lum ** 2, -1, kernel_2d)
        variance = mean_sq - mean ** 2
        variance = np.maximum(variance, 0)  # Ensure non-negative
        std = np.sqrt(variance)
        
        # Distortion metric: normalized standard deviation
        distortion = std / (np.mean(std) + 1e-12)
        
        # Convert distortion to quality metric (inverse relationship)
        # High distortion → low quality → avoid (lower saliency)
        quality = 1.0 / (1.0 + distortion)
        
        # Normalize as probability distribution
        prediction = quality / (np.sum(quality) + 1e-12)
        
        return np.clip(prediction, 0, 1)
    
    @staticmethod
    def linear_regression_baseline(p_freelook: np.ndarray,
                                  p_artifact: np.ndarray,
                                  weights: Tuple[float, float, float] = (0.7, 0.2, 0.1)) -> np.ndarray:
        """
        Baseline 3: Simple Linear Regression
        
        Weighted linear combination: P_lin = w1*P_free + w2*P_art + w3*center_bias
        
        Simplest possible fusion method for comparison.
        """
        h, w = p_freelook.shape
        
        # Unpack weights
        w1, w2, w3 = weights
        
        # Center bias (simpler than full prior)
        y = np.arange(h)
        x = np.arange(w)
        xx, yy = np.meshgrid(x, y)
        
        sigma = max(h, w) / 6
        center_prior = np.exp(-((xx - w/2)**2 + (yy - h/2)**2) / (2 * sigma**2))
        center_prior = center_prior / (np.sum(center_prior) + 1e-12)
        
        # Linear combination
        linear = w1 * p_freelook + w2 * p_artifact + w3 * center_prior
        
        # Normalize
        prediction = linear / (np.sum(linear) + 1e-12)
        
        return np.clip(prediction, 0, 1)


class BaselineEvaluator:
    """Evaluate baseline methods"""
    
    @staticmethod
    def evaluate_all_baselines(img_ref: np.ndarray,
                              img_dist: np.ndarray,
                              p_freelook: np.ndarray,
                              p_artifact: np.ndarray,
                              p_target: np.ndarray,
                              metric_cc_fn,
                              metric_jsd_fn) -> dict:
        """
        Evaluate all baseline methods on a single sample
        
        Returns dictionary with CC and JSD for each baseline
        """
        results = {
            'freelook': {},
            'artifact': {},
            'linear': {},
            'ssim_weighted': {},
            'brisque_weighted': {}
        }
        
        # Baseline 0: FreeLook (no adjustment)
        results['freelook']['cc'] = metric_cc_fn(p_freelook, p_target)
        results['freelook']['jsd'] = metric_jsd_fn(p_freelook, p_target)
        
        # Baseline 1: Artifact only (no fusion)
        results['artifact']['cc'] = metric_cc_fn(p_artifact, p_target)
        results['artifact']['jsd'] = metric_jsd_fn(p_artifact, p_target)
        
        # Baseline 2: Linear regression
        p_linear = BaselineComparison.linear_regression_baseline(p_freelook, p_artifact)
        results['linear']['cc'] = metric_cc_fn(p_linear, p_target)
        results['linear']['jsd'] = metric_jsd_fn(p_linear, p_target)
        
        # Baseline 3: Saliency-weighted SSIM
        try:
            p_ssim_weighted = BaselineComparison.saliency_weighted_ssim(
                img_ref, img_dist, p_target
            )
            results['ssim_weighted']['cc'] = metric_cc_fn(p_ssim_weighted, p_target)
            results['ssim_weighted']['jsd'] = metric_jsd_fn(p_ssim_weighted, p_target)
        except Exception as e:
            logger.warning(f"Failed to compute saliency-weighted SSIM: {e}")
            results['ssim_weighted']['cc'] = 0.0
            results['ssim_weighted']['jsd'] = 1.0
        
        # Baseline 4: BRISQUE-based weighting
        try:
            p_brisque = BaselineComparison.brisque_weighting(img_dist)
            results['brisque_weighted']['cc'] = metric_cc_fn(p_brisque, p_target)
            results['brisque_weighted']['jsd'] = metric_jsd_fn(p_brisque, p_target)
        except Exception as e:
            logger.warning(f"Failed to compute BRISQUE weighting: {e}")
            results['brisque_weighted']['cc'] = 0.0
            results['brisque_weighted']['jsd'] = 1.0
        
        return results
    
    @staticmethod
    def summary_statistics(all_results: dict) -> dict:
        """Compute summary statistics across all samples"""
        summary = {}
        
        for method_name in all_results[0].keys():
            cc_values = [r[method_name]['cc'] for r in all_results if method_name in r]
            jsd_values = [r[method_name]['jsd'] for r in all_results if method_name in r]
            
            summary[method_name] = {
                'cc_mean': np.mean(cc_values),
                'cc_std': np.std(cc_values),
                'jsd_mean': np.mean(jsd_values),
                'jsd_std': np.std(jsd_values)
            }
        
        return summary
