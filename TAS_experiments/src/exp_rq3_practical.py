"""
Experiment 3: RQ3 - Practical Value
Track B (No MOS available): Consistency metrics and ROI-background risk analysis
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from scipy.stats import sem

from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from tas_model import TASModel
from metrics import SaliencyMetrics

logger = logging.getLogger(__name__)

class ExperimentRQ3:
    """RQ3: Practical downstream value (Track B - consistency and risk metrics)"""
    
    def __init__(self, config, trained_models: Dict = None):
        self.config = config
        self.data_loader = DataLoader(config)
        self.artifact_generator = ArtifactMapGenerator(config)
        self.trained_models = trained_models or {}
    
    def compute_error_map(self, img_reference: np.ndarray, 
                         img_distorted: np.ndarray) -> np.ndarray:
        """
        Compute pixel-wise error map.
        Uses luminance (Y channel) for JPEG artifacts.
        """
        if len(img_reference.shape) == 3:
            ref_lum = img_reference[:, :, 0]
            dist_lum = img_distorted[:, :, 0]
        else:
            ref_lum = img_reference
            dist_lum = img_distorted
        
        error_map = np.abs(ref_lum - dist_lum).astype(np.float32)
        
        return error_map
    
    def compute_sw_psnr(self, p_saliency: np.ndarray,
                       img_reference: np.ndarray,
                       img_distorted: np.ndarray,
                       max_val: float = 255.0) -> float:
        """
        Compute saliency-weighted PSNR.
        
        Formula:
        SW-PSNR = 10 * log10(MAX^2 / MSE_w)
        where MSE_w = sum(P(x) * error(x)^2)
        """
        error_map = self.compute_error_map(img_reference, img_distorted)
        
        # Weighted MSE
        mse_weighted = np.sum(p_saliency * (error_map ** 2))
        
        if mse_weighted <= 0:
            return 100.0  # Max PSNR for zero error
        
        sw_psnr = 10.0 * np.log10((max_val ** 2) / mse_weighted)
        
        return sw_psnr
    
    def define_roi_from_freelook(self, p_freelook: np.ndarray, 
                                k_percent: float = 0.3) -> np.ndarray:
        """
        Define ROI based on top k% mass from freelook saliency.
        
        Args:
            p_freelook: Freelook saliency probability map
            k_percent: Fraction of mass to include in ROI (default: 30%)
        
        Returns:
            Binary ROI mask
        """
        flat = p_freelook.flatten()
        sorted_indices = np.argsort(-flat)
        
        # Find threshold to include k% of total mass
        cumsum = np.cumsum(flat[sorted_indices])
        total_mass = cumsum[-1]
        target_mass = k_percent * total_mass
        
        threshold_idx = np.searchsorted(cumsum, target_mass)
        threshold_value = flat[sorted_indices[threshold_idx]]
        
        # Create binary ROI mask
        roi_mask = (p_freelook >= threshold_value).astype(np.float32)
        
        return roi_mask
    
    def compute_roi_bg_statistics(self, p_saliency: np.ndarray,
                                 roi_mask: np.ndarray,
                                 error_map: np.ndarray) -> Dict:
        """
        Compute statistics for ROI vs background regions.
        
        Args:
            p_saliency: Saliency probability map
            roi_mask: Binary ROI mask
            error_map: Pixel-wise error map
        
        Returns:
            Dict with ROI and background statistics
        """
        # Attention mass in ROI and BG
        roi_attention = np.sum(p_saliency * roi_mask)
        bg_attention = 1.0 - roi_attention
        
        # Error statistics
        roi_error = np.sum(p_saliency * error_map * roi_mask) / (np.sum(roi_mask) + 1e-12)
        bg_error = np.sum(p_saliency * error_map * (1 - roi_mask)) / (np.sum(1 - roi_mask) + 1e-12)
        
        return {
            'roi_attention': roi_attention,
            'bg_attention': bg_attention,
            'roi_error': roi_error,
            'bg_error': bg_error,
        }
    
    def run_consistency_analysis(self, content_name: str, 
                                model: TASModel = None) -> List[Dict]:
        """
        Analyze SW-PSNR monotonicity and sensitivity across compression levels.
        """
        data = self.data_loader.get_data_for_content(content_name, preprocess_saliency=True)
        
        results = []
        
        for level in sorted(data['levels']):
            img = data['images'][level]
            p_free = data['saliency_freelook'][level]
            p_score = data['saliency_scoring'][level]
            
            if p_free is None or p_score is None:
                continue
            
            # Compute SW-PSNR for different saliency priors
            sw_psnr_uniform = self.compute_sw_psnr(
                np.ones_like(p_free) / np.sum(np.ones_like(p_free)),
                img, img
            )
            
            sw_psnr_free = self.compute_sw_psnr(p_free, img, img)
            sw_psnr_score = self.compute_sw_psnr(p_score, img, img)
            
            # TAS if model provided
            sw_psnr_tas = None
            if model is not None:
                artifact_map = self.artifact_generator.compute_nr_artifact(img)
                p_artifact = self.artifact_generator.normalize_artifact_to_probability(artifact_map)
                p_tas = model.predict_tas(p_free, p_artifact, compression_level=level)
                sw_psnr_tas = self.compute_sw_psnr(p_tas, img, img)
            
            result = {
                'content': content_name,
                'level': level,
                'sw_psnr_uniform': sw_psnr_uniform,
                'sw_psnr_freelook': sw_psnr_free,
                'sw_psnr_scoring': sw_psnr_score,
                'sw_psnr_tas': sw_psnr_tas,
            }
            
            results.append(result)
        
        return results
    
    def check_monotonicity(self, results: List[Dict]) -> Dict:
        """
        Check if SW-PSNR decreases monotonically with compression level.
        
        Returns:
            Dict with violation rate and statistics
        """
        # Sort by level
        sorted_results = sorted(results, key=lambda x: x['level'])
        
        methods = ['freelook', 'scoring', 'tas']
        violations = {m: 0 for m in methods}
        
        for i in range(len(sorted_results) - 1):
            current = sorted_results[i]
            next_item = sorted_results[i + 1]
            
            for method in methods:
                key_current = f"sw_psnr_{method}"
                key_next = f"sw_psnr_{method}"
                
                if key_current in current and key_next in next_item:
                    # SW-PSNR should decrease (as compression increases)
                    if current[key_current] < next_item[key_next]:
                        violations[method] += 1
        
        violation_rate = {m: v / (len(sorted_results) - 1) 
                         for m, v in violations.items()}
        
        return {
            'violations': violations,
            'violation_rate': violation_rate,
        }
    
    def run_distraction_analysis(self, use_trained_models: bool = False) -> pd.DataFrame:
        """
        Analyze background distraction metric D_bg across compression levels.
        """
        contents = self.data_loader.get_unique_contents()
        all_results = []
        
        for content in contents:
            if self.config.VERBOSE:
                print(f"Analyzing distraction for: {content}")
            
            data = self.data_loader.get_data_for_content(content, preprocess_saliency=True)
            
            # Get model for this content if available
            model = self.trained_models.get(content) if use_trained_models else None
            
            # Define ROI from freelook at lowest compression
            if data['levels']:
                lowest_level = min(data['levels'])
                p_free_ref = data['saliency_freelook'][lowest_level]
                roi_mask = self.define_roi_from_freelook(p_free_ref, k_percent=0.3)
            else:
                continue
            
            for level in data['levels']:
                p_free = data['saliency_freelook'][level]
                p_score = data['saliency_scoring'][level]
                
                if p_free is None or p_score is None:
                    continue
                
                # Background attention mass
                d_bg_free = np.sum(p_free * (1 - roi_mask))
                d_bg_score = np.sum(p_score * (1 - roi_mask))
                
                result = {
                    'content': content,
                    'level': level,
                    'd_bg_freelook': d_bg_free,
                    'd_bg_scoring': d_bg_score,
                }
                
                # TAS distraction if model available
                if model is not None:
                    img = data['images'][level]
                    artifact_map = self.artifact_generator.compute_nr_artifact(img)
                    p_artifact = self.artifact_generator.normalize_artifact_to_probability(artifact_map)
                    p_tas = model.predict_tas(p_free, p_artifact, compression_level=level)
                    d_bg_tas = np.sum(p_tas * (1 - roi_mask))
                    result['d_bg_tas'] = d_bg_tas
                
                all_results.append(result)
        
        return pd.DataFrame(all_results)
    
    def summarize_distraction(self, df: pd.DataFrame) -> Dict:
        """Summarize distraction metrics by compression level"""
        summary = {}
        
        for level in sorted(df['level'].unique()):
            level_data = df[df['level'] == level]
            
            summary[level] = {
                'd_bg_freelook': {
                    'mean': level_data['d_bg_freelook'].mean(),
                    'std': level_data['d_bg_freelook'].std(),
                    'sem': sem(level_data['d_bg_freelook']),
                },
                'd_bg_scoring': {
                    'mean': level_data['d_bg_scoring'].mean(),
                    'std': level_data['d_bg_scoring'].std(),
                    'sem': sem(level_data['d_bg_scoring']),
                }
            }
            
            if 'd_bg_tas' in level_data.columns:
                summary[level]['d_bg_tas'] = {
                    'mean': level_data['d_bg_tas'].mean(),
                    'std': level_data['d_bg_tas'].std(),
                    'sem': sem(level_data['d_bg_tas']),
                }
        
        return summary
    
    def run(self) -> Dict:
        """Run complete RQ3 analysis (Track B)"""
        logger.info("=" * 60)
        logger.info("EXPERIMENT 3: RQ3 - Practical Value (Track B)")
        logger.info("=" * 60)
        
        # Consistency analysis
        logger.info("Analyzing SW-PSNR monotonicity...")
        contents = self.data_loader.get_unique_contents()
        consistency_results = []
        
        for content in contents[:10]:  # Sample 10 contents for efficiency
            res = self.run_consistency_analysis(content)
            consistency_results.extend(res)
        
        df_consistency = pd.DataFrame(consistency_results)
        
        # Distraction analysis
        logger.info("Analyzing background distraction...")
        df_distraction = self.run_distraction_analysis(use_trained_models=False)
        summary_distraction = self.summarize_distraction(df_distraction)
        
        return {
            'consistency_df': df_consistency,
            'distraction_df': df_distraction,
            'distraction_summary': summary_distraction,
        }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    from config import config
    
    exp = ExperimentRQ3(config)
    results = exp.run()
    
    print("\nRQ3 Results Summary:")
    print(f"Consistency samples: {len(results['consistency_df'])}")
    print(f"Distraction samples: {len(results['distraction_df'])}")
