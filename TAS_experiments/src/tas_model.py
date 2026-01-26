"""
Task-Adaptive Saliency (TAS) models and fusion methods
"""
import numpy as np
from typing import Dict, Tuple, Optional
from scipy.optimize import minimize, differential_evolution
import logging

logger = logging.getLogger(__name__)

class TASModel:
    """Task-Adaptive Saliency model implementation"""
    
    def __init__(self, config=None, method: str = 'loglinear'):
        """
        Args:
            config: Configuration object
            method: 'loglinear' or 'mixture'
        """
        self.config = config
        self.method = method
        self.parameters = {}  # Store learned parameters
        self.epsilon = 1e-12
    
    def loglinear_tas(self, 
                     p_freelook: np.ndarray,
                     p_artifact: np.ndarray,
                     p_center: Optional[np.ndarray] = None,
                     alpha: float = 1.0,
                     beta: float = 1.0,
                     gamma: float = 0.1,
                     base_floor: Optional[float] = None) -> np.ndarray:
        """
        Log-linear TAS with base floor to prevent zero-killing.
        
        Formula:
        P_tas ∝ (P_free + δ)^α * (A + δ)^β * (P_C + δ)^γ
        
        Args:
            p_freelook: Freelook saliency probability map
            p_artifact: Artifact probability map
            p_center: Optional center prior (bias toward center)
            alpha: Exponent for freelook component
            beta: Exponent for artifact component
            gamma: Exponent for center prior
            base_floor: Base probability floor (default: 1/(H*W))
        
        Returns:
            Normalized TAS probability map
        """
        h, w = p_freelook.shape
        
        # Set default floor
        if base_floor is None:
            base_floor = 1.0 / (h * w)
        
        # Compute log-linear components with floor
        p_fl_with_floor = p_freelook + base_floor
        p_art_with_floor = p_artifact + base_floor
        
        # Compute base TAS
        tas = np.power(p_fl_with_floor, alpha) * np.power(p_art_with_floor, beta)
        
        # Add center prior if provided
        if p_center is not None:
            p_center_with_floor = p_center + base_floor
            tas *= np.power(p_center_with_floor, gamma)
        
        # Normalize to probability
        total = np.sum(tas) + self.epsilon
        tas_normalized = tas / total
        
        return tas_normalized
    
    def mixture_tas(self,
                   p_freelook: np.ndarray,
                   p_artifact: np.ndarray,
                   p_center: Optional[np.ndarray] = None,
                   w_freelook: float = 0.6,
                   w_artifact: float = 0.3,
                   w_center: float = 0.1) -> np.ndarray:
        """
        Mixture TAS using additive fusion of probability maps.
        
        Formula:
        P_mix = norm(w1*P_free + w2*P_A + w3*P_C)
        
        Args:
            p_freelook: Freelook saliency probability map
            p_artifact: Artifact probability map
            p_center: Optional center prior
            w_freelook: Weight for freelook
            w_artifact: Weight for artifact
            w_center: Weight for center prior
        
        Returns:
            Normalized mixture probability map
        """
        # Ensure weights sum to 1
        total_weight = w_freelook + w_artifact + w_center
        w_freelook /= total_weight
        w_artifact /= total_weight
        w_center /= total_weight if p_center is not None else total_weight
        
        # Weighted combination
        mixture = w_freelook * p_freelook + w_artifact * p_artifact
        
        if p_center is not None:
            mixture += w_center * p_center
        
        # Normalize to probability
        total = np.sum(mixture) + self.epsilon
        mixture_normalized = mixture / total
        
        return mixture_normalized
    
    def compute_center_prior(self, shape: Tuple) -> np.ndarray:
        """
        Compute center bias prior (Gaussian centered at image center).
        
        Args:
            shape: (height, width)
        
        Returns:
            Center prior probability map
        """
        h, w = shape
        y = np.arange(h)
        x = np.arange(w)
        xx, yy = np.meshgrid(x, y)
        
        # Gaussian centered at (w/2, h/2)
        sigma = max(h, w) / 6  # Controls width of Gaussian
        center_prior = np.exp(-((xx - w/2)**2 + (yy - h/2)**2) / (2 * sigma**2))
        
        # Normalize to probability
        total = np.sum(center_prior) + self.epsilon
        center_prior = center_prior / total
        
        return center_prior
    
    def predict_tas(self, 
                   p_freelook: np.ndarray,
                   p_artifact: np.ndarray,
                   compression_level: Optional[int] = None,
                   use_center_prior: bool = False) -> np.ndarray:
        """
        Predict TAS using learned parameters or defaults.
        
        Args:
            p_freelook: Freelook saliency
            p_artifact: Artifact map
            compression_level: Optional JPEG compression level for conditional parameters
            use_center_prior: Whether to use center prior
        
        Returns:
            Predicted saliency map
        """
        shape = p_freelook.shape
        p_center = self.compute_center_prior(shape) if use_center_prior else None
        
        if self.method == 'loglinear':
            # Get parameters (per-level or shared)
            if compression_level is not None and compression_level in self.parameters:
                params = self.parameters[compression_level]
            else:
                params = self.parameters.get('shared', 
                    {'alpha': 1.0, 'beta': 1.0, 'gamma': 0.1})
            
            return self.loglinear_tas(
                p_freelook, p_artifact, p_center,
                alpha=params['alpha'],
                beta=params['beta'],
                gamma=params.get('gamma', 0.1)
            )
        
        elif self.method == 'mixture':
            # Get parameters
            if compression_level is not None and compression_level in self.parameters:
                params = self.parameters[compression_level]
            else:
                params = self.parameters.get('shared',
                    {'w_freelook': 0.6, 'w_artifact': 0.3, 'w_center': 0.1})
            
            return self.mixture_tas(
                p_freelook, p_artifact, p_center,
                w_freelook=params['w_freelook'],
                w_artifact=params['w_artifact'],
                w_center=params.get('w_center', 0.1)
            )
        
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    def fit_to_target(self,
                     p_freelook: np.ndarray,
                     p_artifact: np.ndarray,
                     p_target: np.ndarray,
                     compression_level: Optional[int] = None,
                     use_center_prior: bool = False,
                     loss_type: str = 'combined') -> Dict:
        """
        Fit TAS parameters to match target saliency.
        
        Args:
            p_freelook: Freelook saliency
            p_artifact: Artifact map
            p_target: Target saliency (usually scoring saliency)
            compression_level: Compression level (for per-level learning)
            use_center_prior: Use center prior
            loss_type: 'correlation', 'jsd', 'mse', 'combined'
        
        Returns:
            Dict with optimized parameters and loss value
        """
        shape = p_freelook.shape
        p_center = self.compute_center_prior(shape) if use_center_prior else None
        
        def loss_function(params):
            if self.method == 'loglinear':
                alpha, beta = params[0], params[1]
                gamma = params[2] if len(params) > 2 else 0.1
                p_pred = self.loglinear_tas(p_freelook, p_artifact, p_center,
                                           alpha=alpha, beta=beta, gamma=gamma)
            else:  # mixture
                w1, w2 = params[0], params[1]
                w3 = params[2] if len(params) > 2 else 0.1
                p_pred = self.mixture_tas(p_freelook, p_artifact, p_center,
                                         w_freelook=w1, w_artifact=w2, w_center=w3)
            
            return self._compute_loss(p_pred, p_target, loss_type)
        
        # Optimization bounds
        if self.method == 'loglinear':
            bounds = [(0.01, 3.0), (0.01, 3.0), (0.0, 3.0)]
            x0 = [1.0, 1.0, 0.1]
        else:  # mixture
            bounds = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]
            x0 = [0.6, 0.3, 0.1]
        
        # Use differential evolution for global optimization
        result = differential_evolution(loss_function, bounds, seed=42, maxiter=500,
                                       workers=1, updating='immediate')
        
        # Store optimized parameters
        param_names = ['alpha', 'beta', 'gamma'] if self.method == 'loglinear' \
                     else ['w_freelook', 'w_artifact', 'w_center']
        params_dict = {name: val for name, val in zip(param_names, result.x)}
        
        if compression_level is not None:
            self.parameters[compression_level] = params_dict
        else:
            self.parameters['shared'] = params_dict
        
        return {
            'parameters': params_dict,
            'loss': result.fun,
            'success': result.success
        }
    
    def _compute_loss(self, p_pred: np.ndarray, p_target: np.ndarray, 
                     loss_type: str) -> float:
        """Compute loss between predicted and target saliency"""
        from scipy.spatial.distance import jensenshannon
        
        # Flatten for comparison
        p_pred_flat = p_pred.flatten() + self.epsilon
        p_target_flat = p_target.flatten() + self.epsilon
        
        if loss_type == 'correlation':
            # Maximize correlation = minimize negative correlation
            cc = np.corrcoef(p_pred_flat, p_target_flat)[0, 1]
            return -cc if not np.isnan(cc) else 1.0
        
        elif loss_type == 'jsd':
            # Jensen-Shannon divergence
            return jensenshannon(p_pred_flat, p_target_flat)
        
        elif loss_type == 'mse':
            return np.mean((p_pred - p_target)**2)
        
        elif loss_type == 'combined':
            # Combination of correlation and JSD
            cc = np.corrcoef(p_pred_flat, p_target_flat)[0, 1]
            cc_loss = (1 - cc) if not np.isnan(cc) else 1.0
            jsd_loss = jensenshannon(p_pred_flat, p_target_flat)
            return 0.5 * cc_loss + 0.5 * jsd_loss
        
        else:
            raise ValueError(f"Unknown loss type: {loss_type}")


if __name__ == '__main__':
    print("TAS model module loaded")
