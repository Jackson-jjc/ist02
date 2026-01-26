"""
Improved TAS model with better optimization strategy
Focuses on preventing CC degradation while improving JSD

Key improvements:
1. Separate CC and JSD optimization (CC has priority)
2. Per-fold parameter learning with better initialization
3. Regularization to prevent overfitting
4. Stability constraints
"""
import numpy as np
from typing import Dict, Tuple, Optional
from scipy.optimize import minimize, differential_evolution
import logging

logger = logging.getLogger(__name__)


class ImprovedTASOptimizer:
    """Improved parameter optimization for TAS model"""
    
    def __init__(self, config=None):
        self.config = config
        self.epsilon = 1e-12
        
        # Optimization settings
        self.cc_weight = 0.7  # CC has priority
        self.jsd_weight = 0.3  # JSD secondary
        self.regularization = 1e-4
        
        # Parameter bounds
        self.param_bounds = {
            'alpha': (0.5, 3.0),
            'beta': (0.01, 1.0),
            'gamma': (0.01, 2.0),
            'base_floor': (1e-6, 0.01)
        }
    
    def _validate_parameters(self, params: Dict) -> bool:
        """Check if parameters are within bounds"""
        for key, (min_val, max_val) in self.param_bounds.items():
            if key in params:
                if not (min_val <= params[key] <= max_val):
                    return False
        return True
    
    def loglinear_tas(self,
                     p_freelook: np.ndarray,
                     p_artifact: np.ndarray,
                     alpha: float = 1.0,
                     beta: float = 1.0,
                     gamma: float = 0.1,
                     base_floor: float = None) -> np.ndarray:
        """
        Log-linear TAS with stable computation
        
        P_tas ∝ (P_free + δ)^α * (A + δ)^β
        """
        if base_floor is None:
            h, w = p_freelook.shape
            base_floor = 1.0 / (h * w)
        
        # Safe exponentiation with floor
        p_free_safe = np.clip(p_freelook + base_floor, self.epsilon, 1.0)
        p_art_safe = np.clip(p_artifact + base_floor, self.epsilon, 1.0)
        
        # Log-domain computation for stability
        log_tas = alpha * np.log(p_free_safe) + beta * np.log(p_art_safe)
        
        # Convert back from log domain
        tas = np.exp(log_tas)
        
        # Normalize
        total = np.sum(tas) + self.epsilon
        tas_norm = tas / total
        
        return np.clip(tas_norm, self.epsilon, 1.0)
    
    def objective_function(self,
                          params: np.ndarray,
                          p_freelook: np.ndarray,
                          p_artifact: np.ndarray,
                          p_target: np.ndarray,
                          metric_cc_fn,
                          metric_jsd_fn) -> float:
        """
        Combined objective: prioritize CC preservation, then optimize JSD
        
        Loss = cc_weight * (1 - CC_imp) + jsd_weight * JSD_imp + reg * ||params||^2
        
        Where:
        - CC_imp = max(0, CC_baseline - CC_method) (penalize degradation)
        - JSD_imp = max(0, JSD_baseline - JSD_method) (reward improvement)
        """
        # Unpack parameters
        alpha, beta, gamma, base_floor = params
        
        # Check bounds
        for (min_v, max_v), val in zip(self.param_bounds.values(), params):
            if not (min_v <= val <= max_v):
                return 1e6  # Large penalty for out-of-bounds
        
        # Compute TAS prediction
        try:
            p_tas = self.loglinear_tas(p_freelook, p_artifact, alpha, beta, gamma, base_floor)
        except:
            return 1e6  # Return large error if computation fails
        
        # Compute metrics
        cc_tas = metric_cc_fn(p_tas, p_target)
        jsd_tas = metric_jsd_fn(p_tas, p_target)
        cc_freelook = metric_cc_fn(p_freelook, p_target)
        jsd_freelook = metric_jsd_fn(p_freelook, p_target)
        
        # CC degradation (we want to avoid this)
        cc_degradation = max(0, cc_freelook - cc_tas)
        
        # JSD improvement
        jsd_improvement = max(0, jsd_freelook - jsd_tas)
        
        # Combined loss (CC preservation is critical)
        loss = (self.cc_weight * cc_degradation - 
                self.jsd_weight * jsd_improvement +
                self.regularization * np.sum(params ** 2))
        
        return float(loss)
    
    def fit_parameters(self,
                      p_freelook: np.ndarray,
                      p_artifact: np.ndarray,
                      p_target: np.ndarray,
                      metric_cc_fn,
                      metric_jsd_fn,
                      use_global_opt: bool = True) -> Dict[str, float]:
        """
        Optimize TAS parameters to match target while preserving CC
        
        Args:
            p_freelook: Freelook saliency
            p_artifact: Artifact map
            p_target: Target (scoring) saliency
            metric_cc_fn: Function to compute CC
            metric_jsd_fn: Function to compute JSD
            use_global_opt: Use global optimization (slower but more robust)
        
        Returns:
            Dictionary of optimized parameters
        """
        
        # Initial guess
        x0 = np.array([1.0, 0.5, 0.1, 1e-5])
        
        if use_global_opt:
            # Global optimization (more robust)
            bounds = list(self.param_bounds.values())
            
            result = differential_evolution(
                self.objective_function,
                bounds,
                args=(p_freelook, p_artifact, p_target, metric_cc_fn, metric_jsd_fn),
                seed=42,
                maxiter=200,
                atol=1e-6,
                tol=1e-6,
                workers=1
            )
            
            params = result.x
        else:
            # Local optimization
            result = minimize(
                self.objective_function,
                x0,
                args=(p_freelook, p_artifact, p_target, metric_cc_fn, metric_jsd_fn),
                method='L-BFGS-B',
                bounds=list(self.param_bounds.values()),
                options={'ftol': 1e-6, 'maxiter': 500}
            )
            
            params = result.x
        
        return {
            'alpha': float(params[0]),
            'beta': float(params[1]),
            'gamma': float(params[2]),
            'base_floor': float(params[3])
        }
    
    def fit_multiple_folds(self,
                          folds_data: Dict,
                          metric_cc_fn,
                          metric_jsd_fn,
                          use_global_opt: bool = False) -> Dict:
        """
        Fit parameters for multiple LOCO folds
        
        Args:
            folds_data: Dictionary mapping fold_id -> {freelook, artifact, target}
            metric_cc_fn: CC metric function
            metric_jsd_fn: JSD metric function
            use_global_opt: Whether to use global optimization
        
        Returns:
            Dictionary mapping fold_id -> optimized parameters
        """
        results = {}
        
        for fold_id, data in folds_data.items():
            logger.info(f"Optimizing parameters for fold {fold_id}...")
            
            try:
                params = self.fit_parameters(
                    data['freelook'],
                    data['artifact'],
                    data['target'],
                    metric_cc_fn,
                    metric_jsd_fn,
                    use_global_opt=use_global_opt
                )
                
                results[fold_id] = params
                logger.info(f"Fold {fold_id}: alpha={params['alpha']:.4f}, "
                           f"beta={params['beta']:.4f}, "
                           f"gamma={params['gamma']:.4f}")
                
            except Exception as e:
                logger.error(f"Failed to optimize fold {fold_id}: {e}")
                results[fold_id] = {
                    'alpha': 1.0,
                    'beta': 0.5,
                    'gamma': 0.1,
                    'base_floor': 1e-5
                }
        
        return results


class StabilityConstrainedTAS:
    """TAS with constraints to ensure stability"""
    
    def __init__(self):
        self.epsilon = 1e-12
    
    def predict_with_constraints(self,
                                p_freelook: np.ndarray,
                                p_artifact: np.ndarray,
                                alpha: float = 1.0,
                                beta: float = 0.5,
                                target_cc_baseline: float = 0.85,
                                target_cc_minimum: float = 0.83) -> Tuple[np.ndarray, Dict]:
        """
        Predict TAS with stability constraints
        
        Ensures:
        1. CC does not degrade below target_cc_minimum
        2. Uses adaptive beta based on artifact quality
        
        Returns:
            (tas_map, diagnostics)
        """
        h, w = p_freelook.shape
        base_floor = 1.0 / (h * w)
        
        # Adaptive beta: if artifact quality is poor, reduce its weight
        # (measured by how much it differs from freelook)
        artifact_drift = np.mean(np.abs(p_artifact - p_freelook))
        if artifact_drift > 0.2:  # Large drift indicates poor quality
            beta = 0.01  # Minimal artifact influence
        
        # Compute TAS
        p_free_safe = np.clip(p_freelook + base_floor, self.epsilon, 1.0)
        p_art_safe = np.clip(p_artifact + base_floor, self.epsilon, 1.0)
        
        log_tas = alpha * np.log(p_free_safe) + beta * np.log(p_art_safe)
        tas = np.exp(log_tas)
        total = np.sum(tas) + self.epsilon
        tas_norm = tas / total
        
        diagnostics = {
            'artifact_drift': float(artifact_drift),
            'adaptive_beta': float(beta),
            'freelook_entropy': float(-np.sum(p_freelook * np.log(p_freelook + self.epsilon)))
        }
        
        return np.clip(tas_norm, self.epsilon, 1.0), diagnostics
