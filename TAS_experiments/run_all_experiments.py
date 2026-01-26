#!/usr/bin/env python3
"""
Main script to run all TAS experiments (RQ1, RQ2, RQ3)
This is the entry point for SLURM job submission.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src directory to path
SRC_DIR = Path(__file__).parent / 'src'
sys.path.insert(0, str(SRC_DIR))

# Import modules
from config import config
from data_loader import DataLoader
from artifact_maps import ArtifactMapGenerator
from tas_model import TASModel
from metrics import SaliencyMetrics
from exp_rq1_task_shift import ExperimentRQ1
from exp_rq2_prediction import ExperimentRQ2
from exp_rq3_practical import ExperimentRQ3
from visualizer import ResultsVisualizer

# Extract config variables
LOGS_DIR = config.LOGS_DIR
RESULTS_DIR = config.RESULTS_DIR
DATA_ROOT = config.DATA_ROOT
VERBOSE = config.VERBOSE

# Configure logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(LOGS_DIR / f'tas_experiments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for all experiments"""
    
    logger.info("=" * 80)
    logger.info("STARTING TAS EXPERIMENTS PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Data root: {DATA_ROOT}")
    logger.info(f"Results dir: {RESULTS_DIR}")
    logger.info(f"Verbose: {VERBOSE}")
    
    # Initialize results dict
    all_results = {}
    
    try:
        # Experiment 1: RQ1 - Task Shift Analysis
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 1: Experiment RQ1 - Task Shift Analysis")
        logger.info("=" * 80)
        
        exp_rq1 = ExperimentRQ1(config)
        results_rq1 = exp_rq1.run()
        all_results['rq1'] = results_rq1
        
        # Save RQ1 results
        results_rq1['results_df'].to_csv(RESULTS_DIR / 'rq1_task_shift_results.csv', index=False)
        logger.info(f"RQ1 Results saved: {RESULTS_DIR / 'rq1_task_shift_results.csv'}")
        
        # Print RQ1 summary
        logger.info("\n--- RQ1 Summary ---")
        for level, stats in results_rq1['summary_by_level'].items():
            logger.info(f"Level {level}:")
            logger.info(f"  CC:  {stats['cc']['mean']:.4f} ± {stats['cc']['sem']:.4f}")
            logger.info(f"  JSD: {stats['jsd']['mean']:.4f} ± {stats['jsd']['sem']:.4f}")
        
        # Experiment 2: RQ2 - Saliency Prediction (FR-TAS)
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2a: Experiment RQ2 - Saliency Prediction (FR-TAS)")
        logger.info("=" * 80)
        
        exp_rq2_fr = ExperimentRQ2(config, tas_method='loglinear')
        results_rq2_fr = exp_rq2_fr.run(use_fr_artifact=True)
        all_results['rq2_fr'] = results_rq2_fr
        
        # Save RQ2-FR results
        results_rq2_fr['results_df'].to_csv(RESULTS_DIR / 'rq2_prediction_fr_results.csv', index=False)
        logger.info(f"RQ2-FR Results saved: {RESULTS_DIR / 'rq2_prediction_fr_results.csv'}")
        
        # Print RQ2-FR summary
        logger.info("\n--- RQ2-FR (Full-Reference) Summary ---")
        for method, metrics in results_rq2_fr['summary'].items():
            logger.info(f"{method.upper()}:")
            for metric, stats in metrics.items():
                logger.info(f"  {metric}: {stats['mean']:.4f} ± {stats['sem']:.4f}")
        
        # Experiment 2b: RQ2 - Saliency Prediction (NR-TAS)
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2b: Experiment RQ2 - Saliency Prediction (NR-TAS)")
        logger.info("=" * 80)
        
        exp_rq2_nr = ExperimentRQ2(config, tas_method='loglinear')
        results_rq2_nr = exp_rq2_nr.run(use_fr_artifact=False)
        all_results['rq2_nr'] = results_rq2_nr
        
        # Save RQ2-NR results
        results_rq2_nr['results_df'].to_csv(RESULTS_DIR / 'rq2_prediction_nr_results.csv', index=False)
        logger.info(f"RQ2-NR Results saved: {RESULTS_DIR / 'rq2_prediction_nr_results.csv'}")
        
        # Print RQ2-NR summary
        logger.info("\n--- RQ2-NR (No-Reference) Summary ---")
        for method, metrics in results_rq2_nr['summary'].items():
            logger.info(f"{method.upper()}:")
            for metric, stats in metrics.items():
                logger.info(f"  {metric}: {stats['mean']:.4f} ± {stats['sem']:.4f}")
        
        # Experiment 3: RQ3 - Practical Value
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: Experiment RQ3 - Practical Value (Track B)")
        logger.info("=" * 80)
        
        exp_rq3 = ExperimentRQ3(config, trained_models=results_rq2_nr.get('trained_models'))
        results_rq3 = exp_rq3.run()
        all_results['rq3'] = results_rq3
        
        # Save RQ3 results
        results_rq3['consistency_df'].to_csv(RESULTS_DIR / 'rq3_consistency_results.csv', index=False)
        results_rq3['distraction_df'].to_csv(RESULTS_DIR / 'rq3_distraction_results.csv', index=False)
        logger.info(f"RQ3 Results saved: {RESULTS_DIR / 'rq3_*.csv'}")
        
        # Visualization
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4: Generating Visualizations and Report")
        logger.info("=" * 80)
        
        visualizer = ResultsVisualizer(config)
        
        # RQ1 plots
        if 'rq1' in all_results:
            result = visualizer.plot_task_shift_curves(
                all_results['rq1']['results_df'],
                all_results['rq1']['summary_by_level']
            )
            if result:
                logger.info(f"RQ1 plot saved: {result}")
        
        # RQ2 plots
        if 'rq2_fr' in all_results:
            result = visualizer.plot_prediction_comparison(
                all_results['rq2_fr']['results_df'],
                all_results['rq2_fr']['summary']
            )
            if result:
                logger.info(f"RQ2 plot saved: {result}")
        
        # RQ3 plots
        if 'rq3' in all_results:
            result = visualizer.plot_distraction_trend(
                all_results['rq3']['distraction_df'],
                all_results['rq3']['distraction_summary']
            )
            if result:
                logger.info(f"RQ3 plot saved: {result}")
        
        # Generate final report
        visualizer.generate_summary_report(all_results)
        
        logger.info("\n" + "=" * 80)
        logger.info("ALL EXPERIMENTS COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Results saved to: {RESULTS_DIR}")
        logger.info(f"Logs saved to: {LOGS_DIR}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in experiment pipeline: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
