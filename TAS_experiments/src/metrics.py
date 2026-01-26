"""
Metrics for saliency evaluation and analysis
"""
import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import pearsonr, spearmanr
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SaliencyMetrics:
    """Compute saliency metrics for analysis"""
    
    @staticmethod
    def pearson_correlation(map1: np.ndarray, map2: np.ndarray) -> float:
        """
        Pearson correlation coefficient (CC) between two maps.
        Higher is better (range: [-1, 1], ideal: 1)
        """
        flat1 = map1.flatten()
        flat2 = map2.flatten()
        cc, _ = pearsonr(flat1, flat2)
        return cc if not np.isnan(cc) else 0.0
    
    @staticmethod
    def spearman_correlation(map1: np.ndarray, map2: np.ndarray) -> float:
        """
        Spearman rank correlation coefficient between two maps.
        Higher is better (range: [-1, 1], ideal: 1)
        """
        flat1 = map1.flatten()
        flat2 = map2.flatten()
        srcc, _ = spearmanr(flat1, flat2)
        return srcc if not np.isnan(srcc) else 0.0
    
    @staticmethod
    def jensen_shannon_divergence(map1: np.ndarray, map2: np.ndarray) -> float:
        """
        Jensen-Shannon divergence between two probability distributions.
        Lower is better (range: [0, 1], ideal: 0)
        
        Maps are treated as probability distributions.
        """
        flat1 = map1.flatten()
        flat2 = map2.flatten()
        
        # Normalize to ensure they're valid probability distributions
        flat1 = np.maximum(flat1, 0)
        flat2 = np.maximum(flat2, 0)
        
        sum1 = np.sum(flat1) + 1e-12
        sum2 = np.sum(flat2) + 1e-12
        
        p1 = flat1 / sum1
        p2 = flat2 / sum2
        
        return jensenshannon(p1, p2)
    
    @staticmethod
    def entropy(prob_map: np.ndarray) -> float:
        """
        Shannon entropy of a probability distribution.
        Higher entropy = more dispersed attention.
        """
        flat = prob_map.flatten()
        flat = np.maximum(flat, 1e-12)
        
        # Normalize
        total = np.sum(flat) + 1e-12
        p = flat / total
        
        # Compute entropy: H = -sum(p * log(p))
        entropy = -np.sum(p * np.log(p))
        
        return entropy
    
    @staticmethod
    def saliency_centroid(prob_map: np.ndarray) -> Tuple[float, float]:
        """
        Compute center of mass (centroid) of saliency map.
        Returns (centroid_x, centroid_y) as fractions of image dimensions.
        """
        h, w = prob_map.shape
        
        # Create coordinate grids
        y = np.arange(h)
        x = np.arange(w)
        xx, yy = np.meshgrid(x, y)
        
        # Compute weighted average
        total = np.sum(prob_map) + 1e-12
        centroid_x = np.sum(prob_map * xx) / total
        centroid_y = np.sum(prob_map * yy) / total
        
        return centroid_x, centroid_y
    
    @staticmethod
    def centroid_shift(map1: np.ndarray, map2: np.ndarray) -> float:
        """
        Euclidean distance between centroids of two maps.
        Lower is better (spatial attention stability).
        """
        cx1, cy1 = SaliencyMetrics.saliency_centroid(map1)
        cx2, cy2 = SaliencyMetrics.saliency_centroid(map2)
        
        shift = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
        
        return shift
    
    @staticmethod
    def nss(pred_map: np.ndarray, fixation_map: np.ndarray) -> float:
        """
        Normalized Scanpath Saliency (NSS).
        Measures how well predictions align with fixation points.
        
        Higher is better (typical range: [-2, 3], good: > 1.5)
        """
        # Normalize prediction to zero mean and unit standard deviation
        flat_pred = pred_map.flatten()
        pred_norm = (flat_pred - np.mean(flat_pred)) / (np.std(flat_pred) + 1e-12)
        pred_norm = pred_norm.reshape(pred_map.shape)
        
        # Apply to fixation locations
        nss = np.mean(pred_norm[fixation_map > 0.5])
        
        return nss if not np.isnan(nss) else 0.0
    
    @staticmethod
    def auc_judd(pred_map: np.ndarray, fixation_map: np.ndarray) -> float:
        """
        Area Under Curve using Judd's method.
        Binary classification metric for fixation prediction.
        
        Higher is better (range: [0, 1], ideal: 1)
        """
        # Normalize prediction to [0, 1]
        flat_pred = pred_map.flatten()
        if flat_pred.max() > flat_pred.min():
            pred_norm = (flat_pred - flat_pred.min()) / (flat_pred.max() - flat_pred.min())
        else:
            pred_norm = flat_pred
        
        # Binary fixation map
        fixation_flat = (fixation_map.flatten() > 0.5).astype(int)
        
        # Sort by prediction scores
        sorted_indices = np.argsort(-pred_norm)
        
        # Compute AUC
        pos_count = np.sum(fixation_flat)
        neg_count = len(fixation_flat) - pos_count
        
        if pos_count == 0 or neg_count == 0:
            return 0.5
        
        # Number of positives before each threshold
        tp = np.cumsum(fixation_flat[sorted_indices])
        fp = np.arange(1, len(sorted_indices) + 1) - tp
        
        # AUC computation
        auc = np.sum(tp) / (pos_count * neg_count)
        
        return min(auc, 1.0)
    
    @staticmethod
    def compute_all_metrics(pred_map: np.ndarray, target_map: np.ndarray,
                           compute_nss: bool = False,
                           fixation_map: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Compute all saliency metrics at once.
        
        Args:
            pred_map: Predicted saliency map
            target_map: Target/reference saliency map
            compute_nss: Whether to compute NSS
            fixation_map: Binary fixation map for NSS computation
        
        Returns:
            Dict with all metric values
        """
        metrics = {
            'cc': SaliencyMetrics.pearson_correlation(pred_map, target_map),
            'srcc': SaliencyMetrics.spearman_correlation(pred_map, target_map),
            'jsd': SaliencyMetrics.jensen_shannon_divergence(pred_map, target_map),
            'entropy_pred': SaliencyMetrics.entropy(pred_map),
            'entropy_target': SaliencyMetrics.entropy(target_map),
            'centroid_shift': SaliencyMetrics.centroid_shift(pred_map, target_map),
        }
        
        if compute_nss and fixation_map is not None:
            metrics['nss'] = SaliencyMetrics.nss(pred_map, fixation_map)
            metrics['auc'] = SaliencyMetrics.auc_judd(pred_map, fixation_map)
        
        return metrics


if __name__ == '__main__':
    # Test with random maps
    map1 = np.random.rand(100, 100)
    map1 /= np.sum(map1)
    
    map2 = np.random.rand(100, 100)
    map2 /= np.sum(map2)
    
    metrics = SaliencyMetrics.compute_all_metrics(map1, map2)
    print("Sample metrics:")
    for key, val in metrics.items():
        print(f"  {key}: {val:.4f}")
