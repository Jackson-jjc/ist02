"""
Experiment 1: RQ1 - Task Shift Analysis
Analyze how saliency distributions differ between free-looking and scoring tasks
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List
import logging
from scipy.stats import sem
import matplotlib.pyplot as plt

from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from metrics import SaliencyMetrics

logger = logging.getLogger(__name__)

class ExperimentRQ1:
    """RQ1: Task effect and compression-related saliency shift"""
    
    def __init__(self, config):
        self.config = config
        self.data_loader = DataLoader(config)
        self.artifact_generator = ArtifactMapGenerator(config)
        self.results = []
    
    def analyze_task_shift(self) -> pd.DataFrame:
        """
        Analyze differences between free-looking and scoring saliency across compression levels.
        
        Returns:
            DataFrame with analysis results per image
        """
        contents = self.data_loader.get_unique_contents()
        
        for content in contents:
            if self.config.VERBOSE:
                print(f"Processing content: {content}")
            
            # Load data for this content
            data = self.data_loader.get_data_for_content(content, preprocess_saliency=True)
            
            for level in data['levels']:
                # Get saliency maps
                p_free = data['saliency_freelook'][level]
                p_score = data['saliency_scoring'][level]
                
                if p_free is None or p_score is None:
                    continue
                
                # Compute metrics
                metrics = SaliencyMetrics.compute_all_metrics(p_free, p_score)
                
                # Store results
                result = {
                    'content': content,
                    'level': level,
                    'cc': metrics['cc'],  # Similarity
                    'jsd': metrics['jsd'],  # Divergence
                    'entropy_free': metrics['entropy_pred'],
                    'entropy_score': metrics['entropy_target'],
                    'centroid_shift': metrics['centroid_shift'],
                }
                
                self.results.append(result)
        
        return pd.DataFrame(self.results)
    
    def summarize_by_compression_level(self, df: pd.DataFrame) -> Dict:
        """
        Summarize metrics by compression level with confidence intervals.
        
        Returns:
            Dict with mean, std, and 95% CI for each metric per level
        """
        summary = {}
        
        for level in sorted(df['level'].unique()):
            level_data = df[df['level'] == level]
            
            summary[level] = {
                'n_contents': len(level_data),
                'cc': {
                    'mean': level_data['cc'].mean(),
                    'std': level_data['cc'].std(),
                    'sem': sem(level_data['cc']),
                },
                'jsd': {
                    'mean': level_data['jsd'].mean(),
                    'std': level_data['jsd'].std(),
                    'sem': sem(level_data['jsd']),
                },
                'entropy_diff': {
                    'mean': (level_data['entropy_score'] - level_data['entropy_free']).mean(),
                    'std': (level_data['entropy_score'] - level_data['entropy_free']).std(),
                    'sem': sem(level_data['entropy_score'] - level_data['entropy_free']),
                },
                'centroid_shift': {
                    'mean': level_data['centroid_shift'].mean(),
                    'std': level_data['centroid_shift'].std(),
                    'sem': sem(level_data['centroid_shift']),
                }
            }
        
        return summary
    
    def get_most_affected_images(self, df: pd.DataFrame, metric: str = 'jsd', 
                                 top_n: int = 6) -> List[Dict]:
        """
        Get images with largest task shift.
        
        Returns:
            List of top images sorted by metric
        """
        df_sorted = df.sort_values(metric, ascending=(metric == 'cc')).head(top_n)
        return df_sorted.to_dict('records')
    
    def run(self) -> Dict:
        """Run complete RQ1 analysis"""
        logger.info("=" * 60)
        logger.info("EXPERIMENT 1: RQ1 - Task Shift Analysis")
        logger.info("=" * 60)
        
        # Analyze task shift
        logger.info("Analyzing task shift across compression levels...")
        df_results = self.analyze_task_shift()
        
        # Summary by compression level
        summary = self.summarize_by_compression_level(df_results)
        
        # Get representative images for visualization
        high_shift = self.get_most_affected_images(df_results, metric='jsd', top_n=3)
        low_shift = self.get_most_affected_images(df_results, metric='jsd', top_n=3)[::-1]
        
        return {
            'results_df': df_results,
            'summary_by_level': summary,
            'high_shift_examples': high_shift,
            'low_shift_examples': low_shift,
        }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    from config import config
    
    exp = ExperimentRQ1(config)
    results = exp.run()
    
    print("\nRQ1 Results Summary:")
    for level, stats in results['summary_by_level'].items():
        print(f"\nCompression Level {level}:")
        print(f"  CC: {stats['cc']['mean']:.4f} ± {stats['cc']['sem']:.4f}")
        print(f"  JSD: {stats['jsd']['mean']:.4f} ± {stats['jsd']['sem']:.4f}")
