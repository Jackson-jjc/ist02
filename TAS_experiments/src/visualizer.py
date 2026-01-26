"""
Visualization and result reporting
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Try to import matplotlib; if not available, skip plots
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib not available - visualization will be skipped")

class ResultsVisualizer:
    """Create visualizations for TAS experiments"""
    
    def __init__(self, config, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or config.RESULTS_DIR
        self.output_dir.mkdir(exist_ok=True)
    
    def plot_task_shift_curves(self, df: pd.DataFrame, 
                               summary: Dict) -> str:
        """Plot RQ1: Task shift across compression levels"""
        if not HAS_MATPLOTLIB:
            logger.warning("Skipping visualization - matplotlib not available")
            return None
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('RQ1: Task Shift Analysis', fontsize=14, fontweight='bold')
        
        metrics = ['cc', 'jsd']
        
        for row, metric in enumerate(metrics):
            # Plot 1: Per-level statistics
            levels = sorted(summary.keys())
            means = [summary[l][metric]['mean'] for l in levels]
            sems = [summary[l][metric]['sem'] for l in levels]
            
            ax = axes[row, 0]
            ax.errorbar(levels, means, yerr=sems, marker='o', capsize=5, linewidth=2)
            ax.set_xlabel('Compression Level')
            ax.set_ylabel(f'{metric.upper()}')
            ax.set_title(f'{metric.upper()} vs Compression Level')
            ax.grid(True, alpha=0.3)
            
            # Plot 2: Distribution
            ax = axes[row, 1]
            for level in levels:
                level_data = df[df['level'] == level][metric]
                ax.scatter([level]*len(level_data), level_data, alpha=0.5, s=30)
            ax.set_xlabel('Compression Level')
            ax.set_ylabel(f'{metric.upper()}')
            ax.set_title(f'{metric.upper()} Distribution')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = self.output_dir / 'fig_rq1_task_shift.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def plot_prediction_comparison(self, df: pd.DataFrame,
                                   summary: Dict) -> str:
        """Plot RQ2: Saliency prediction comparison"""
        if not HAS_MATPLOTLIB:
            logger.warning("Skipping visualization - matplotlib not available")
            return None
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('RQ2: Saliency Prediction Performance', fontsize=14, fontweight='bold')
        
        methods = ['freelook', 'mixture', 'tas']
        colors = {'freelook': 'C0', 'mixture': 'C1', 'tas': 'C2'}
        
        for col, metric in enumerate(['cc', 'jsd']):
            ax = axes[col]
            
            for method in methods:
                if method in summary and metric in summary[method]:
                    stats = summary[method][metric]
                    ax.scatter(method, stats['mean'], s=200, 
                             color=colors.get(method, 'gray'), alpha=0.7)
                    ax.errorbar(method, stats['mean'], 
                               yerr=stats['sem'], fmt='none', ecolor='black', capsize=5)
            
            ax.set_ylabel(f'{metric.upper()}')
            ax.set_title(f'Method Comparison: {metric.upper()}')
            ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        filepath = self.output_dir / 'fig_rq2_prediction.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def plot_distraction_trend(self, df: pd.DataFrame,
                              summary: Dict) -> str:
        """Plot RQ3: Background distraction metric"""
        if not HAS_MATPLOTLIB:
            logger.warning("Skipping visualization - matplotlib not available")
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        levels = sorted(summary.keys())
        
        d_bg_freelook = [summary[l]['d_bg_freelook']['mean'] for l in levels]
        d_bg_scoring = [summary[l]['d_bg_scoring']['mean'] for l in levels]
        
        sem_freelook = [summary[l]['d_bg_freelook']['sem'] for l in levels]
        sem_scoring = [summary[l]['d_bg_scoring']['sem'] for l in levels]
        
        ax.errorbar(levels, d_bg_freelook, yerr=sem_freelook, 
                   marker='o', label='FreeLook', linewidth=2, capsize=5)
        ax.errorbar(levels, d_bg_scoring, yerr=sem_scoring,
                   marker='s', label='Scoring (Oracle)', linewidth=2, capsize=5)
        
        # Add TAS if available
        if any('d_bg_tas' in summary[l] for l in levels):
            d_bg_tas = [summary[l].get('d_bg_tas', {}).get('mean', np.nan) for l in levels]
            sem_tas = [summary[l].get('d_bg_tas', {}).get('sem', np.nan) for l in levels]
            ax.errorbar(levels, d_bg_tas, yerr=sem_tas,
                       marker='^', label='TAS', linewidth=2, capsize=5)
        
        ax.set_xlabel('Compression Level')
        ax.set_ylabel('Background Attention Mass D_bg')
        ax.set_title('RQ3: Background Distraction Metric')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = self.output_dir / 'fig_rq3_distraction.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def save_results_table(self, df: pd.DataFrame, name: str, 
                          summary: Dict = None) -> str:
        """Save results as CSV and LaTeX table"""
        # CSV
        csv_path = self.output_dir / f'table_{name}.csv'
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved CSV: {csv_path}")
        
        # Summary table if provided
        if summary is not None:
            summary_df = self._dict_to_dataframe(summary)
            tex_path = self.output_dir / f'table_{name}_summary.tex'
            latex_str = summary_df.to_latex(index=True, float_format='%.4f')
            with open(tex_path, 'w') as f:
                f.write(latex_str)
            logger.info(f"Saved LaTeX: {tex_path}")
        
        return str(csv_path)
    
    def _dict_to_dataframe(self, data: Dict) -> pd.DataFrame:
        """Convert nested dict to DataFrame for tabulation"""
        rows = []
        for key1, val1 in data.items():
            if isinstance(val1, dict):
                for key2, val2 in val1.items():
                    if isinstance(val2, dict):
                        row = {'group': key1, 'metric': key2}
                        row.update(val2)
                        rows.append(row)
        
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame(data)
    
    def generate_summary_report(self, results_all: Dict) -> str:
        """Generate text summary report"""
        report_path = self.output_dir / 'RESULTS_SUMMARY.txt'
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("TAS EXPERIMENTS - COMPREHENSIVE RESULTS SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            # RQ1 Summary
            if 'rq1' in results_all:
                f.write("EXPERIMENT 1: RQ1 - Task Shift Analysis\n")
                f.write("-" * 80 + "\n")
                summary = results_all['rq1'].get('summary_by_level', {})
                for level, stats in summary.items():
                    f.write(f"\nCompression Level {level}:\n")
                    f.write(f"  CC:  {stats['cc']['mean']:.4f} ± {stats['cc']['sem']:.4f}\n")
                    f.write(f"  JSD: {stats['jsd']['mean']:.4f} ± {stats['jsd']['sem']:.4f}\n")
                f.write("\n")
            
            # RQ2 Summary
            if 'rq2' in results_all:
                f.write("EXPERIMENT 2: RQ2 - Saliency Prediction\n")
                f.write("-" * 80 + "\n")
                summary = results_all['rq2'].get('summary', {})
                for method, metrics in summary.items():
                    f.write(f"\n{method.upper()}:\n")
                    for metric, stats in metrics.items():
                        f.write(f"  {metric}: {stats['mean']:.4f} ± {stats['sem']:.4f}\n")
                f.write("\n")
            
            # RQ3 Summary
            if 'rq3' in results_all:
                f.write("EXPERIMENT 3: RQ3 - Practical Value\n")
                f.write("-" * 80 + "\n")
                summary = results_all['rq3'].get('distraction_summary', {})
                for level, stats in summary.items():
                    f.write(f"\nCompression Level {level}:\n")
                    for metric, values in stats.items():
                        f.write(f"  {metric}: {values['mean']:.4f} ± {values['sem']:.4f}\n")
                f.write("\n")
            
            f.write("=" * 80 + "\n")
        
        logger.info(f"Saved report: {report_path}")
        return str(report_path)


if __name__ == '__main__':
    print("Visualization module loaded")
