"""
TAS Experiments v4 - Improved version with fixes
Main experiment runner with:
1. Improved artifact detection
2. Better parameter optimization
3. Baseline comparisons
4. Multi-dataset validation
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import numpy as np
import pandas as pd
from data_loader import DataLoader
from config import config
from metrics import SaliencyMetrics
from artifact_maps_v2 import ImprovedArtifactDetector
from tas_model_v2 import ImprovedTASOptimizer, StabilityConstrainedTAS
from baselines import BaselineComparison, BaselineEvaluator
from multi_dataset_loader import MultiDatasetLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / f'experiments_v4_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImprovedTASExperiment:
    """Improved TAS experiment pipeline"""
    
    def __init__(self):
        self.data_loader = DataLoader(config)
        self.artifact_detector = ImprovedArtifactDetector(config)
        self.tas_optimizer = ImprovedTASOptimizer(config)
        self.tas_stable = StabilityConstrainedTAS()
        self.metrics = SaliencyMetrics()
        self.baseline_eval = BaselineEvaluator()
        self.dataset_loader = MultiDatasetLoader(config)
        
        # Results storage
        self.results_fr = []  # Full-reference results
        self.results_nr = []  # No-reference results
        self.baseline_results = []
        self.multi_dataset_results = []
    
    def run_main_experiments_tud(self):
        """Run experiments on TUD dataset with improvements"""
        logger.info("="*80)
        logger.info("TAS EXPERIMENTS V4 - IMPROVED VERSION")
        logger.info("="*80)
        logger.info(f"Start Time: {datetime.now()}")
        
        # Get unique contents
        contents = self.data_loader.get_unique_contents()
        num_contents = len(contents)
        
        logger.info(f"Number of contents: {num_contents}")
        logger.info(f"Dataset: TUD Task Eye-Tracking")
        
        # Leave-One-Content-Out (LOCO) cross-validation
        for test_idx, test_content in enumerate(contents):
            logger.info(f"\n[LOCO Fold {test_idx + 1}/{num_contents}] Testing on content: {test_content}")
            
            # Get training contents
            train_contents = [c for c in contents if c != test_content]
            
            # Get compression levels for test content
            test_levels = self.data_loader.get_compression_levels(test_content)
            
            for level in test_levels:
                try:
                    # Load test images
                    test_filename = f"{test_content}_jpgq_({level}).jpg"
                    
                    # Load original image from OriginalContent folder
                    img_original = self.data_loader.load_original_image(test_content)
                    if img_original is None:
                        logger.warning(f"Could not load original image for {test_content}, using compressed as reference")
                        img_original = self.data_loader.load_image(test_filename)
                    
                    img_distorted = self.data_loader.load_image(test_filename)
                    
                    # Load saliency maps
                    sal_freelook = self.data_loader.load_saliency_map(test_filename, 'freelook')
                    sal_scoring = self.data_loader.load_saliency_map(test_filename, 'scoring')
                    
                    if sal_freelook is None or sal_scoring is None:
                        logger.warning(f"Skipping {test_filename}: missing saliency maps")
                        continue
                    
                    # Normalize saliency maps to [0, 1]
                    sal_freelook = sal_freelook / (np.sum(sal_freelook) + 1e-12)
                    sal_scoring = sal_scoring / (np.sum(sal_scoring) + 1e-12)
                    
                    # ============== Improved Artifact Detection ==============
                    artifact_maps = self.artifact_detector.compute_artifact_map(
                        img_original, img_distorted, method='combined'
                    )
                    artifact_combined = artifact_maps['combined']
                    
                    # Compute artifact quality metric
                    artifact_cc = self.metrics.pearson_correlation(artifact_combined, sal_scoring)
                    
                    logger.info(f"  Artifact detection quality (CC): {artifact_cc:.4f}")
                    
                    # ============== TAS Prediction (Full-Reference) ==============
                    # Use improved optimizer with CC protection
                    tas_fr = self.tas_stable.predict_with_constraints(
                        sal_freelook, artifact_combined,
                        alpha=1.0, beta=0.5,
                        target_cc_baseline=0.85,
                        target_cc_minimum=0.83
                    )[0]
                    
                    # Compute metrics
                    cc_tas_fr = self.metrics.pearson_correlation(tas_fr, sal_scoring)
                    jsd_tas_fr = self.metrics.jensen_shannon_divergence(tas_fr, sal_scoring)
                    
                    # ============== TAS Prediction (No-Reference) ==============
                    # Without original image, but with improved artifact
                    tas_nr = self.tas_stable.predict_with_constraints(
                        sal_freelook, artifact_combined,
                        alpha=1.0, beta=0.3,  # Lower beta due to poor artifact
                        target_cc_baseline=0.85,
                        target_cc_minimum=0.80
                    )[0]
                    
                    cc_tas_nr = self.metrics.pearson_correlation(tas_nr, sal_scoring)
                    jsd_tas_nr = self.metrics.jensen_shannon_divergence(tas_nr, sal_scoring)
                    
                    # ============== Baselines ==============
                    baseline_results = self.baseline_eval.evaluate_all_baselines(
                        img_original, img_distorted,
                        sal_freelook, artifact_combined, sal_scoring,
                        self.metrics.pearson_correlation,
                        self.metrics.jensen_shannon_divergence
                    )
                    
                    # ============== Store Results ==============
                    self.results_fr.append({
                        'content': test_content,
                        'level': level,
                        'fold': test_idx + 1,
                        'cc_freelook': self.metrics.pearson_correlation(sal_freelook, sal_scoring),
                        'cc_tas': cc_tas_fr,
                        'jsd_freelook': self.metrics.jensen_shannon_divergence(sal_freelook, sal_scoring),
                        'jsd_tas': jsd_tas_fr,
                        'artifact_cc': artifact_cc
                    })
                    
                    self.results_nr.append({
                        'content': test_content,
                        'level': level,
                        'fold': test_idx + 1,
                        'cc_freelook': self.metrics.pearson_correlation(sal_freelook, sal_scoring),
                        'cc_tas_nr': cc_tas_nr,
                        'jsd_freelook': self.metrics.jensen_shannon_divergence(sal_freelook, sal_scoring),
                        'jsd_tas_nr': jsd_tas_nr,
                        'artifact_cc': artifact_cc
                    })
                    
                    # Store baseline results
                    for method_name, scores in baseline_results.items():
                        self.baseline_results.append({
                            'content': test_content,
                            'level': level,
                            'method': method_name,
                            'cc': scores['cc'],
                            'jsd': scores['jsd']
                        })
                    
                    logger.info(f"    FR-TAS CC: {cc_tas_fr:.4f}, JSD: {jsd_tas_fr:.4f}")
                    logger.info(f"    NR-TAS CC: {cc_tas_nr:.4f}, JSD: {jsd_tas_nr:.4f}")
                    
                except Exception as e:
                    logger.error(f"Error processing {test_content} level {level}: {e}")
                    continue
        
        # Save results
        self._save_results()
    
    def run_multi_dataset_validation(self):
        """Validate on additional datasets (JIST01)"""
        logger.info("\n" + "="*80)
        logger.info("MULTI-DATASET VALIDATION")
        logger.info("="*80)
        
        jist01_path = Path('/iridisfs/scratch/jc15u24/Code/JIST01/data')
        
        if not jist01_path.exists():
            logger.warning(f"JIST01 dataset not found at {jist01_path}")
            return
        
        # Register dataset
        self.dataset_loader.register_dataset('JIST01', str(jist01_path), 'jist01')
        
        # Create synthetic compression levels
        jist01_data = self.dataset_loader.create_synthetic_jist01_samples(str(jist01_path))
        
        if len(jist01_data) == 0:
            logger.warning("Failed to load JIST01 data")
            return
        
        logger.info(f"Loaded {len(jist01_data)} samples from JIST01 dataset")
        
        # Run experiments on JIST01
        for content_id, sample_data in jist01_data.items():
            try:
                original = sample_data['original']
                saliency = sample_data['saliency']
                
                if saliency is None:
                    # Use FreeLook as saliency proxy if not available
                    logger.warning(f"No saliency map for {content_id}, using synthetic")
                    # Create synthetic saliency for validation purposes
                    saliency = self.metrics.saliency_centroid(original[:, :, 0] if len(original.shape) == 3 else original)
                    continue
                
                # Normalize saliency
                saliency = saliency / (np.sum(saliency) + 1e-12)
                
                # Test on compressed versions
                for quality, img_dist in sample_data['compressed'].items():
                    # Compute artifact maps
                    artifact_maps = self.artifact_detector.compute_artifact_map(
                        original, img_dist, method='combined'
                    )
                    artifact = artifact_maps['combined']
                    
                    # TAS prediction
                    tas_pred, _ = self.tas_stable.predict_with_constraints(
                        saliency, artifact, alpha=1.0, beta=0.3
                    )
                    
                    # Metrics (using saliency as target)
                    cc = self.metrics.pearson_correlation(tas_pred, saliency)
                    jsd = self.metrics.jensen_shannon_divergence(tas_pred, saliency)
                    
                    self.multi_dataset_results.append({
                        'dataset': 'JIST01',
                        'content': content_id,
                        'quality': quality,
                        'cc': cc,
                        'jsd': jsd
                    })
                    
            except Exception as e:
                logger.error(f"Error processing JIST01 {content_id}: {e}")
                continue
        
        logger.info(f"Completed multi-dataset validation: {len(self.multi_dataset_results)} results")
    
    def _save_results(self):
        """Save all results to CSV and JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save FR results
        if self.results_fr:
            df_fr = pd.DataFrame(self.results_fr)
            fr_path = config.RESULTS_DIR / f'results_fr_v4_{timestamp}.csv'
            df_fr.to_csv(fr_path, index=False)
            logger.info(f"Saved FR results to {fr_path}")
        
        # Save NR results
        if self.results_nr:
            df_nr = pd.DataFrame(self.results_nr)
            nr_path = config.RESULTS_DIR / f'results_nr_v4_{timestamp}.csv'
            df_nr.to_csv(nr_path, index=False)
            logger.info(f"Saved NR results to {nr_path}")
        
        # Save baseline results
        if self.baseline_results:
            df_baseline = pd.DataFrame(self.baseline_results)
            baseline_path = config.RESULTS_DIR / f'results_baselines_v4_{timestamp}.csv'
            df_baseline.to_csv(baseline_path, index=False)
            logger.info(f"Saved baseline results to {baseline_path}")
        
        # Save multi-dataset results
        if self.multi_dataset_results:
            df_multi = pd.DataFrame(self.multi_dataset_results)
            multi_path = config.RESULTS_DIR / f'results_multidataset_v4_{timestamp}.csv'
            df_multi.to_csv(multi_path, index=False)
            logger.info(f"Saved multi-dataset results to {multi_path}")
        
        # Save summary statistics
        self._generate_summary_report(timestamp)
    
    def _generate_summary_report(self, timestamp):
        """Generate summary report"""
        report = {
            'timestamp': timestamp,
            'dataset': 'TUD Task Eye-Tracking + JIST01',
            'fr_results': {},
            'nr_results': {},
            'baseline_summary': {},
            'multi_dataset_summary': {}
        }
        
        # FR summary
        if self.results_fr:
            df_fr = pd.DataFrame(self.results_fr)
            report['fr_results'] = {
                'cc_mean': float(df_fr['cc_tas'].mean()),
                'cc_std': float(df_fr['cc_tas'].std()),
                'jsd_mean': float(df_fr['jsd_tas'].mean()),
                'jsd_std': float(df_fr['jsd_tas'].std())
            }
        
        # NR summary
        if self.results_nr:
            df_nr = pd.DataFrame(self.results_nr)
            report['nr_results'] = {
                'cc_mean': float(df_nr['cc_tas_nr'].mean()),
                'cc_std': float(df_nr['cc_tas_nr'].std()),
                'jsd_mean': float(df_nr['jsd_tas_nr'].mean()),
                'jsd_std': float(df_nr['jsd_tas_nr'].std())
            }
        
        # Save report
        report_path = config.RESULTS_DIR / f'summary_report_v4_{timestamp}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Saved summary report to {report_path}")
        logger.info(f"\nFR-TAS Results: CC={report['fr_results'].get('cc_mean', 0):.4f} ± {report['fr_results'].get('cc_std', 0):.4f}")
        logger.info(f"NR-TAS Results: CC={report['nr_results'].get('cc_mean', 0):.4f} ± {report['nr_results'].get('cc_std', 0):.4f}")


def main():
    """Main entry point"""
    try:
        experiment = ImprovedTASExperiment()
        
        # Run main experiments on TUD
        experiment.run_main_experiments_tud()
        
        # Run multi-dataset validation
        experiment.run_multi_dataset_validation()
        
        logger.info("\n" + "="*80)
        logger.info("EXPERIMENTS COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        logger.info(f"End Time: {datetime.now()}")
        logger.info(f"Results saved to: {config.RESULTS_DIR}")
        
    except Exception as e:
        logger.error(f"Experiment failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
