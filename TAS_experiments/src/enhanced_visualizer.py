"""
Enhanced Visualization Module
Implements all visualizations from the paper preparation checklist B section
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
import logging
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import seaborn as sns
    from matplotlib.gridspec import GridSpec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib not available")


class EnhancedVisualizer:
    """Enhanced visualization suite for paper preparation"""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path('results')
        self.output_dir.mkdir(exist_ok=True)
        
        if HAS_MATPLOTLIB:
            sns.set_style("whitegrid")
            plt.rcParams['figure.dpi'] = 100
    
    def plot_method_comparison_grid(self, rq2_fr_data: pd.DataFrame, 
                                    image_dir: Path = None) -> str:
        """
        B1a: Method comparison grid (3x3 layout)
        Shows: Original | FreeLook Saliency | Task Saliency | TAS Prediction | Error
        """
        if not HAS_MATPLOTLIB:
            return None
        
        # This is a conceptual plot since we're working with saliency maps, not raw images
        # In practice, you'd load actual images and saliency maps
        
        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(4, 5, figure=fig, hspace=0.3, wspace=0.3)
        
        # Summary statistics for the grid
        fig.suptitle('Method Comparison Overview\n(Saliency Prediction Performance)', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # Add text summary
        methods = ['FreeLook', 'Artifact', 'Mixture', 'TAS']
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
        
        ax_summary = fig.add_subplot(gs[0, :])
        ax_summary.axis('off')
        
        summary_text = "Performance Summary:\n\n"
        for method, color in zip(methods, colors):
            method_col = f"{method.lower()}_cc" if method.lower() != 'artifact' else "artifact_cc"
            if method_col in rq2_fr_data.columns:
                mean_cc = rq2_fr_data[method_col].mean()
                std_cc = rq2_fr_data[method_col].std()
                summary_text += f"  {method}: CC = {mean_cc:.4f} ± {std_cc:.4f}\n"
        
        ax_summary.text(0.05, 0.5, summary_text, fontsize=11, 
                       family='monospace', verticalalignment='center')
        
        # Create bar plots for each method
        for idx, (method, color) in enumerate(zip(methods, colors)):
            method_col = f"{method.lower()}_cc" if method.lower() != 'artifact' else "artifact_cc"
            if method_col in rq2_fr_data.columns:
                ax = fig.add_subplot(gs[1:3, idx])
                
                # Bar plot of CC per content (sample)
                content_means = rq2_fr_data.groupby('content')[method_col].mean().sort_values(ascending=False)[:10]
                ax.barh(range(len(content_means)), content_means.values, color=color, alpha=0.7)
                ax.set_yticks(range(len(content_means)))
                ax.set_yticklabels(content_means.index, fontsize=8)
                ax.set_xlabel('Correlation Coefficient', fontsize=9)
                ax.set_title(f'{method}\n(Top 10 Contents)', fontsize=10, fontweight='bold')
                ax.set_xlim(0, 1)
                ax.grid(axis='x', alpha=0.3)
        
        # Add comparison text
        ax_compare = fig.add_subplot(gs[1:3, 4])
        ax_compare.axis('off')
        
        compare_text = "Key Findings:\n"
        compare_text += "• TAS provides\n  competitive\n  performance\n"
        compare_text += "• No-reference\n  deployment\n  advantage\n"
        compare_text += "• Practical utility\n  in real scenarios"
        
        ax_compare.text(0.1, 0.5, compare_text, fontsize=10, 
                       verticalalignment='center', bbox=dict(boxstyle='round', 
                       facecolor='wheat', alpha=0.5))
        
        # Distribution plot
        ax_dist = fig.add_subplot(gs[3, :2])
        
        for method, color in zip(methods, colors):
            method_col = f"{method.lower()}_cc" if method.lower() != 'artifact' else "artifact_cc"
            if method_col in rq2_fr_data.columns:
                data = rq2_fr_data[method_col].dropna()
                ax_dist.hist(data, alpha=0.5, label=method, bins=20, color=color)
        
        ax_dist.set_xlabel('Correlation Coefficient', fontsize=10)
        ax_dist.set_ylabel('Frequency', fontsize=10)
        ax_dist.set_title('Distribution of Prediction Performance', fontsize=11, fontweight='bold')
        ax_dist.legend()
        ax_dist.grid(alpha=0.3)
        
        # Box plot
        ax_box = fig.add_subplot(gs[3, 2:])
        
        box_data = []
        box_labels = []
        for method in methods:
            method_col = f"{method.lower()}_cc" if method.lower() != 'artifact' else "artifact_cc"
            if method_col in rq2_fr_data.columns:
                box_data.append(rq2_fr_data[method_col].dropna())
                box_labels.append(method)
        
        bp = ax_box.boxplot(box_data, labels=box_labels, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax_box.set_ylabel('Correlation Coefficient', fontsize=10)
        ax_box.set_title('Performance Distribution', fontsize=11, fontweight='bold')
        ax_box.grid(axis='y', alpha=0.3)
        
        filepath = self.output_dir / 'fig_b1a_method_comparison_grid.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def plot_artifact_detection_visualization(self, rq2_fr_data: pd.DataFrame,
                                             levels: list = None) -> str:
        """
        B1b: Artifact detection visualization across compression levels
        Shows artifact score progression across quality levels
        """
        if not HAS_MATPLOTLIB:
            return None
        
        if levels is None:
            levels = sorted(rq2_fr_data['level'].unique())[:4]  # Take 4 representative levels
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('B1b: Artifact Detection Across Compression Levels', 
                    fontsize=14, fontweight='bold')
        
        for idx, level in enumerate(levels[:4]):
            ax = axes[idx // 2, idx % 2]
            
            level_data = rq2_fr_data[rq2_fr_data['level'] == level]
            
            # Prepare comparison data
            contents = level_data['content'].unique()[:15]  # Top 15 contents
            
            x_pos = np.arange(len(contents))
            width = 0.2
            
            freelook_scores = []
            artifact_scores = []
            mixture_scores = []
            tas_scores = []
            
            for content in contents:
                content_data = level_data[level_data['content'] == content].iloc[0]
                freelook_scores.append(content_data.get('freelook_cc', 0))
                artifact_scores.append(content_data.get('artifact_cc', 0))
                mixture_scores.append(content_data.get('mixture_cc', 0))
                tas_scores.append(content_data.get('tas_cc', 0))
            
            ax.bar(x_pos - 1.5*width, freelook_scores, width, label='FreeLook', alpha=0.8)
            ax.bar(x_pos - 0.5*width, artifact_scores, width, label='Artifact', alpha=0.8)
            ax.bar(x_pos + 0.5*width, mixture_scores, width, label='Mixture', alpha=0.8)
            ax.bar(x_pos + 1.5*width, tas_scores, width, label='TAS', alpha=0.8)
            
            ax.set_xlabel('Content', fontsize=9)
            ax.set_ylabel('Correlation Coefficient', fontsize=9)
            ax.set_title(f'Compression Level: {level}', fontsize=10, fontweight='bold')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(range(len(contents)), fontsize=8)
            ax.set_ylim(0, 1)
            ax.legend(fontsize=8, loc='lower right')
            ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        filepath = self.output_dir / 'fig_b1b_artifact_detection.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def plot_parameter_heatmap(self, alpha_range: np.ndarray,
                              beta_range: np.ndarray,
                              performance_matrix: np.ndarray) -> str:
        """
        B1c: Parameter space heatmap
        Visualizes performance across alpha and beta parameters
        """
        if not HAS_MATPLOTLIB:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        im = ax.imshow(performance_matrix, cmap='RdYlGn', aspect='auto', 
                      origin='lower', vmin=0.7, vmax=0.9)
        
        # Set ticks
        ax.set_xticks(np.arange(0, len(alpha_range), max(1, len(alpha_range)//10)))
        ax.set_yticks(np.arange(0, len(beta_range), max(1, len(beta_range)//10)))
        
        ax.set_xticklabels([f"{alpha_range[i]:.2f}" for i in ax.get_xticks() if i < len(alpha_range)])
        ax.set_yticklabels([f"{beta_range[i]:.3f}" for i in ax.get_yticks() if i < len(beta_range)])
        
        ax.set_xlabel('Alpha (Control of FreeLook Component)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Beta (Control of Artifact Component)', fontsize=11, fontweight='bold')
        ax.set_title('B1c: Parameter Space Sensitivity Analysis\n(Performance Heatmap)', 
                    fontsize=12, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Pearson Correlation Coefficient', fontsize=10)
        
        # Mark optimal region
        max_idx = np.unravel_index(np.argmax(performance_matrix), performance_matrix.shape)
        ax.plot(max_idx[1], max_idx[0], 'r*', markersize=15, label='Optimal')
        ax.legend()
        
        plt.tight_layout()
        filepath = self.output_dir / 'fig_b1c_parameter_heatmap.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def plot_rq1_improved_trend(self, rq1_data: pd.DataFrame) -> str:
        """
        B1d: Improved RQ1 trend analysis
        Shows task shift across compression levels with confidence bands
        """
        if not HAS_MATPLOTLIB:
            return None
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('B1d: Task Shift Analysis with Confidence Bands', 
                    fontsize=14, fontweight='bold')
        
        metrics = ['cc', 'jsd', 'centroid_shift', 'entropy_score']
        metric_names = ['Correlation (CC)', 'Jensen-Shannon Div.', 'Centroid Shift', 'Entropy Score']
        
        for idx, (metric, name) in enumerate(zip(metrics, metric_names)):
            ax = axes[idx // 2, idx % 2]
            
            # Group by level
            grouped = rq1_data.groupby('level')[metric].agg(['mean', 'std', 'count'])
            grouped['sem'] = grouped['std'] / np.sqrt(grouped['count'])
            grouped['ci_lower'] = grouped['mean'] - 1.96 * grouped['sem']
            grouped['ci_upper'] = grouped['mean'] + 1.96 * grouped['sem']
            
            levels = grouped.index.values
            means = grouped['mean'].values
            ci_lower = grouped['ci_lower'].values
            ci_upper = grouped['ci_upper'].values
            
            # Plot with confidence band
            ax.fill_between(levels, ci_lower, ci_upper, alpha=0.2, color='blue', label='95% CI')
            ax.plot(levels, means, 'o-', color='blue', linewidth=2, markersize=6, label='Mean')
            
            # Add individual level markers for 40 contents
            for level in levels:
                level_data = rq1_data[rq1_data['level'] == level][metric]
                y_vals = level_data.values
                x_vals = np.random.normal(level, 1, size=len(y_vals))  # Add jitter
                ax.scatter(x_vals, y_vals, alpha=0.2, s=20, color='gray')
            
            ax.set_xlabel('Compression Level', fontsize=10)
            ax.set_ylabel(name, fontsize=10)
            ax.set_title(name, fontsize=11, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = self.output_dir / 'fig_b1d_rq1_trend_improved.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def plot_content_heatmap(self, rq2_fr_data: pd.DataFrame) -> str:
        """
        B1e: Content difficulty heatmap
        Rows: 40 contents, Columns: 4 methods
        """
        if not HAS_MATPLOTLIB:
            return None
        
        # Prepare data
        contents = sorted(rq2_fr_data['content'].unique())
        methods = ['freelook_cc', 'artifact_cc', 'mixture_cc', 'tas_cc']
        method_labels = ['FreeLook', 'Artifact', 'Mixture', 'TAS']
        
        heatmap_data = np.zeros((len(contents), len(methods)))
        
        for i, content in enumerate(contents):
            content_data = rq2_fr_data[rq2_fr_data['content'] == content]
            for j, method in enumerate(methods):
                heatmap_data[i, j] = content_data[method].mean()
        
        fig, ax = plt.subplots(figsize=(8, 14))
        
        im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        
        ax.set_xticks(np.arange(len(method_labels)))
        ax.set_yticks(np.arange(len(contents)))
        
        ax.set_xticklabels(method_labels, fontsize=10, fontweight='bold')
        ax.set_yticklabels(contents, fontsize=7)
        
        ax.set_title('B1e: Content Difficulty & Method Performance Heatmap\n(Red=Difficult, Green=Easy)', 
                    fontsize=12, fontweight='bold', pad=20)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Mean CC', fontsize=10)
        
        # Add text annotations for better readability (sample)
        for i in range(0, len(contents), 5):
            for j in range(len(methods)):
                text = ax.text(j, i, f'{heatmap_data[i, j]:.2f}',
                              ha="center", va="center", color="black", fontsize=7)
        
        plt.tight_layout()
        filepath = self.output_dir / 'fig_b1e_content_heatmap.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
        return str(filepath)
    
    def generate_improved_results_table(self, rq2_fr_data: pd.DataFrame,
                                       comparisons: list) -> Tuple[str, str]:
        """
        B2: Improved table format with confidence intervals and significance
        """
        
        # Create main comparison table
        methods = ['FreeLook', 'Artifact', 'Mixture', 'TAS']
        method_cols = ['freelook_cc', 'artifact_cc', 'mixture_cc', 'tas_cc']
        
        table_data = []
        
        for method_name, method_col in zip(methods, method_cols):
            data = rq2_fr_data[method_col].dropna()
            
            mean = data.mean()
            std = data.std()
            sem = data.sem()
            ci_lower = mean - 1.96 * sem
            ci_upper = mean + 1.96 * sem
            
            table_data.append({
                'Method': method_name,
                'CC (Mean)': f"{mean:.4f}",
                '± SD': f"{std:.4f}",
                '95% CI': f"[{ci_lower:.4f}, {ci_upper:.4f}]",
                'N': len(data)
            })
        
        table_df = pd.DataFrame(table_data)
        
        # Create comparison table vs baseline
        comparison_data = []
        for comp in comparisons:
            comparison_data.append({
                'Method vs FreeLook': f"{comp['method1']} vs {comp['method2']}",
                'Mean Diff': f"{comp['mean_diff']:+.4f}",
                'Cohen\'s d': f"{comp['cohens_d']:.4f}",
                't-stat': f"{comp['t_stat']:.4f}",
                'p-value': f"{comp['p_value']:.4f}",
                'Significance': comp['significance'],
                'Improvement %': f"{comp['improvement_pct']:+.2f}%"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # Save as CSV
        table_path = self.output_dir / 'table_b2_comparison_with_statistics.csv'
        comparison_path = self.output_dir / 'table_b2_pairwise_comparisons.csv'
        
        table_df.to_csv(table_path, index=False)
        comparison_df.to_csv(comparison_path, index=False)
        
        logger.info(f"Saved: {table_path}")
        logger.info(f"Saved: {comparison_path}")
        
        return str(table_path), str(comparison_path)
