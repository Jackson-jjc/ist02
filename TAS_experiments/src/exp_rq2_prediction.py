"""
Experiment 2: RQ2 - Saliency Prediction
Compare different methods for predicting scoring saliency from freelook + artifacts
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from scipy.stats import sem, wilcoxon

from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from tas_model import TASModel
from metrics import SaliencyMetrics

logger = logging.getLogger(__name__)

class ExperimentRQ2:
    """RQ2: Task-adaptive saliency prediction"""
    
    def __init__(self, config, tas_method: str = 'loglinear'):
        self.config = config
        self.data_loader = DataLoader(config)
        self.artifact_generator = ArtifactMapGenerator(config)
        self.tas_method = tas_method
        self.results = []
        self.trained_models = {}  # Store trained TAS models per LOCO fold
    
    def leave_one_content_out_split(self) -> List[Tuple[List[str], List[str]]]:
        """
        Create LOCO (Leave-One-Content-Out) cross-validation splits.
        
        Returns:
            List of (train_contents, test_content) tuples
        """
        contents = self.data_loader.get_unique_contents()
        splits = []
        
        for test_content in contents:
            train_contents = [c for c in contents if c != test_content]
            splits.append((train_contents, [test_content]))
        
        return splits
    
    def train_tas_on_fold(self, train_contents: List[str], 
                         use_fr_artifact: bool = True) -> TASModel:
        """
        Train TAS model on training contents.
        
        Args:
            train_contents: List of content names for training
            use_fr_artifact: Use FR-Artifact (True) or NR-Artifact (False)
        
        Returns:
            Trained TASModel
        """
        model = TASModel(self.config, method=self.tas_method)
        
        # Aggregate training data across all contents and levels
        training_data = []
        
        for content in train_contents:
            data = self.data_loader.get_data_for_content(content, preprocess_saliency=True)
            
            for level in data['levels']:
                img = data['images'][level]
                p_free = data['saliency_freelook'][level]
                p_score = data['saliency_scoring'][level]
                
                if p_free is None or p_score is None:
                    continue
                
                # Get reference image for FR artifact computation
                # For now, use the image itself as reference (would need actual reference in practice)
                if use_fr_artifact:
                    artifact_map = self.artifact_generator.compute_fr_artifact(
                        img, img, use_luminance=True
                    )
                else:
                    artifact_map = self.artifact_generator.compute_nr_artifact(
                        img, use_blockiness=True, use_ringing=False
                    )
                
                p_artifact = self.artifact_generator.normalize_artifact_to_probability(artifact_map)
                
                training_data.append({
                    'p_free': p_free,
                    'p_artifact': p_artifact,
                    'p_score': p_score,
                    'level': level,
                    'content': content,
                })
        
        # Fit model: learn parameters per compression level
        for level in sorted(set(d['level'] for d in training_data)):
            level_data = [d for d in training_data if d['level'] == level]
            
            if not level_data:
                continue
            
            # Average saliency maps for this level across contents
            p_free_avg = np.mean([d['p_free'] for d in level_data], axis=0)
            p_artifact_avg = np.mean([d['p_artifact'] for d in level_data], axis=0)
            p_score_avg = np.mean([d['p_score'] for d in level_data], axis=0)
            
            # Normalize averages
            p_free_avg /= (np.sum(p_free_avg) + 1e-12)
            p_artifact_avg /= (np.sum(p_artifact_avg) + 1e-12)
            p_score_avg /= (np.sum(p_score_avg) + 1e-12)
            
            # Fit to target
            logger.info(f"Fitting TAS for level {level} using {len(level_data)} training samples")
            
            fit_result = model.fit_to_target(
                p_free_avg, p_artifact_avg, p_score_avg,
                compression_level=level,
                use_center_prior=False,
                loss_type='combined'
            )
            
            if self.config.VERBOSE:
                print(f"Level {level} - Loss: {fit_result['loss']:.4f}, Params: {fit_result['parameters']}")
        
        return model
    
    def evaluate_method(self, test_content: str, model: TASModel,
                       use_fr_artifact: bool = True) -> List[Dict]:
        """
        Evaluate a single method on test content.
        
        Returns:
            List of per-image results
        """
        data = self.data_loader.get_data_for_content(test_content, preprocess_saliency=True)
        
        method_results = []
        
        for level in data['levels']:
            img = data['images'][level]
            p_free = data['saliency_freelook'][level]
            p_score = data['saliency_scoring'][level]
            
            if p_free is None or p_score is None:
                continue
            
            # Compute artifact map
            if use_fr_artifact:
                artifact_map = self.artifact_generator.compute_fr_artifact(
                    img, img, use_luminance=True
                )
            else:
                artifact_map = self.artifact_generator.compute_nr_artifact(
                    img, use_blockiness=True, use_ringing=False
                )
            
            p_artifact = self.artifact_generator.normalize_artifact_to_probability(artifact_map)
            
            # Predict using each method
            results = {
                'content': test_content,
                'level': level,
                'target_entropy': SaliencyMetrics.entropy(p_score),
            }
            
            # Method 1: FreeLook only (baseline)
            cc_free = SaliencyMetrics.pearson_correlation(p_free, p_score)
            jsd_free = SaliencyMetrics.jensen_shannon_divergence(p_free, p_score)
            results['freelook_cc'] = cc_free
            results['freelook_jsd'] = jsd_free
            
            # Method 2: Artifact only
            cc_art = SaliencyMetrics.pearson_correlation(p_artifact, p_score)
            jsd_art = SaliencyMetrics.jensen_shannon_divergence(p_artifact, p_score)
            results['artifact_cc'] = cc_art
            results['artifact_jsd'] = jsd_art
            
            # Method 3: Mixture baseline
            p_mix = model.mixture_tas(p_free, p_artifact, w_freelook=0.6, w_artifact=0.3)
            cc_mix = SaliencyMetrics.pearson_correlation(p_mix, p_score)
            jsd_mix = SaliencyMetrics.jensen_shannon_divergence(p_mix, p_score)
            results['mixture_cc'] = cc_mix
            results['mixture_jsd'] = jsd_mix
            
            # Method 4: TAS (trained)
            p_tas = model.predict_tas(p_free, p_artifact, compression_level=level,
                                     use_center_prior=False)
            cc_tas = SaliencyMetrics.pearson_correlation(p_tas, p_score)
            jsd_tas = SaliencyMetrics.jensen_shannon_divergence(p_tas, p_score)
            results['tas_cc'] = cc_tas
            results['tas_jsd'] = jsd_tas
            
            method_results.append(results)
        
        return method_results
    
    def run_loco_evaluation(self, use_fr_artifact: bool = True) -> pd.DataFrame:
        """
        Run complete LOCO cross-validation evaluation.
        
        Args:
            use_fr_artifact: Use FR-Artifact (True) or NR-Artifact (False)
        
        Returns:
            DataFrame with all results
        """
        splits = self.leave_one_content_out_split()
        all_results = []
        
        for fold_idx, (train_contents, test_contents) in enumerate(splits):
            test_content = test_contents[0]
            
            logger.info(f"LOCO Fold {fold_idx + 1}/{len(splits)}: Test={test_content}")
            
            # Train model on this fold
            model = self.train_tas_on_fold(train_contents, use_fr_artifact=use_fr_artifact)
            self.trained_models[test_content] = model
            
            # Evaluate on test content
            fold_results = self.evaluate_method(test_content, model, 
                                               use_fr_artifact=use_fr_artifact)
            
            all_results.extend(fold_results)
        
        return pd.DataFrame(all_results)
    
    def summarize_results(self, df: pd.DataFrame) -> Dict:
        """
        Summarize LOCO evaluation results.
        
        Returns:
            Dict with statistics per method
        """
        methods = ['freelook', 'artifact', 'mixture', 'tas']
        metrics = ['cc', 'jsd']
        
        summary = {}
        
        for method in methods:
            summary[method] = {}
            for metric in metrics:
                col_name = f"{method}_{metric}"
                if col_name in df.columns:
                    values = df[col_name]
                    summary[method][metric] = {
                        'mean': values.mean(),
                        'std': values.std(),
                        'sem': sem(values),
                        'min': values.min(),
                        'max': values.max(),
                    }
        
        return summary
    
    def run(self, use_fr_artifact: bool = True) -> Dict:
        """Run complete RQ2 analysis"""
        logger.info("=" * 60)
        logger.info(f"EXPERIMENT 2: RQ2 - Saliency Prediction ({self.tas_method})")
        logger.info("=" * 60)
        
        # Run LOCO evaluation
        logger.info(f"Running LOCO evaluation with {'FR' if use_fr_artifact else 'NR'}-Artifact...")
        df_results = self.run_loco_evaluation(use_fr_artifact=use_fr_artifact)
        
        # Summarize results
        summary = self.summarize_results(df_results)
        
        return {
            'results_df': df_results,
            'summary': summary,
            'trained_models': self.trained_models,
            'use_fr_artifact': use_fr_artifact,
        }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    from config import config
    
    exp = ExperimentRQ2(config, tas_method='loglinear')
    results = exp.run(use_fr_artifact=True)
    
    print("\nRQ2 Results Summary (FR-TAS):")
    for method, metrics in results['summary'].items():
        print(f"\n{method.upper()}:")
        for metric, stats in metrics.items():
            print(f"  {metric}: {stats['mean']:.4f} ± {stats['sem']:.4f}")
