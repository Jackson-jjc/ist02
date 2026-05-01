"""
可视化模块 - 生成论文级别的图表
包括：表格、条形图、Pareto曲线、热力图等
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 设置风格
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class PaperVisualizer:
    """论文级别的可视化"""
    
    def __init__(self, output_dir: Path, dpi: int = 300):
        """初始化可视化器"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
    
    def plot_main_results_table(self, results: pd.DataFrame,
                               save_name: str = 'table_main_results.pdf') -> Path:
        """
        绘制主结果表格
        
        Args:
            results: 结果DataFrame，行为方法，列为指标
            save_name: 保存文件名
            
        Returns:
            保存路径
        """
        # 创建表格图
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axis('tight')
        ax.axis('off')
        
        # 格式化数据
        display_data = results.copy()
        for col in display_data.columns:
            if col not in ['Method', 'Dataset']:
                display_data[col] = display_data[col].apply(lambda x: f'{x:.4f}' if isinstance(x, float) else x)
        
        # 创建表格
        table = ax.table(cellText=display_data.values,
                        colLabels=display_data.columns,
                        cellLoc='center',
                        loc='center',
                        colWidths=[0.15] + [0.1] * (len(display_data.columns) - 1))
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # 美化表头
        for i in range(len(display_data.columns)):
            table[(0, i)].set_facecolor('#40466e')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # 交替行颜色
        for i in range(1, len(display_data) + 1):
            for j in range(len(display_data.columns)):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#f0f0f0')
        
        plt.title('Main Results Table (R2 Dataset)', fontsize=14, fontweight='bold', pad=20)
        
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"✓ Saved main results table to {save_path}")
        plt.close()
        
        return save_path
    
    def plot_cross_dataset_comparison(self, results: Dict[str, pd.DataFrame],
                                     metric: str = 'JSD',
                                     save_name: str = 'fig_cross_dataset.pdf') -> Path:
        """
        绘制跨数据集性能对比
        
        Args:
            results: {dataset_name: results_df}
            metric: 要绘制的指标
            save_name: 保存文件名
            
        Returns:
            保存路径
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        datasets = list(results.keys())
        methods = list(results[datasets[0]].index) if len(datasets) > 0 else []
        
        x = np.arange(len(methods))
        width = 0.25
        
        colors = plt.cm.Set2(np.linspace(0, 1, len(datasets)))
        
        for i, dataset in enumerate(datasets):
            values = [results[dataset].loc[method, metric] for method in methods]
            ax.bar(x + i * width, values, width, label=dataset, color=colors[i])
        
        ax.set_xlabel('Method', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{metric} (lower is better)', fontsize=12, fontweight='bold')
        ax.set_title(f'Cross-Dataset Comparison: {metric}', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels(methods, rotation=45, ha='right')
        ax.legend(title='Dataset', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        
        save_path = self.output_dir / save_name
        plt.tight_layout()
        plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"✓ Saved cross-dataset comparison to {save_path}")
        plt.close()
        
        return save_path
    
    def plot_pareto_curve(self, methods_data: Dict[str, np.ndarray],
                         x_metric: str = 'JSD',
                         y_metric: str = 'CC',
                         save_name: str = 'fig_pareto.pdf') -> Path:
        """
        绘制Pareto曲线 (多目标权衡)
        
        Args:
            methods_data: {method_name: {x_metric: scores, y_metric: scores}}
            x_metric: X轴指标 (最小化)
            y_metric: Y轴指标 (最大化)
            save_name: 保存文件名
            
        Returns:
            保存路径
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(methods_data)))
        
        for idx, (method, data) in enumerate(methods_data.items()):
            x_vals = data.get(x_metric, [])
            y_vals = data.get(y_metric, [])
            
            if isinstance(x_vals, (list, np.ndarray)) and len(x_vals) > 0:
                ax.scatter(x_vals, y_vals, s=100, label=method, 
                          color=colors[idx], alpha=0.7, edgecolors='black', linewidth=1.5)
        
        ax.set_xlabel(f'{x_metric} (↓ better)', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{y_metric} (↑ better)', fontsize=12, fontweight='bold')
        ax.set_title(f'Multi-Objective Trade-off: {x_metric} vs {y_metric}',
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)
        
        save_path = self.output_dir / save_name
        plt.tight_layout()
        plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"✓ Saved Pareto curve to {save_path}")
        plt.close()
        
        return save_path
    
    def plot_case_study_visualization(self, 
                                     original_img: np.ndarray,
                                     gaze_target: np.ndarray,
                                     gaze_prior: np.ndarray,
                                     artifact_map: np.ndarray,
                                     predictions: Dict[str, np.ndarray],
                                     case_id: str = 'case_1',
                                     save_name: Optional[str] = None) -> Path:
        """
        绘制Case Study可视化 (包含所有中间步骤)
        
        Args:
            original_img: 原始图像
            gaze_target: 目标凝视分布
            gaze_prior: 先验凝视分布
            artifact_map: 伪影图
            predictions: {method_name: predicted_gaze}
            case_id: 案例ID
            save_name: 保存文件名
            
        Returns:
            保存路径
        """
        n_methods = len(predictions)
        n_cols = 5 + n_methods  # img, prior, target, artifact, + methods
        
        fig = plt.figure(figsize=(4 * n_cols, 8))
        gs = GridSpec(2, n_cols, figure=fig, hspace=0.3, wspace=0.3)
        
        # 第1行：输入与目标
        ax_img = fig.add_subplot(gs[0, 0])
        ax_img.imshow(original_img)
        ax_img.set_title('Input Image', fontweight='bold')
        ax_img.axis('off')
        
        ax_prior = fig.add_subplot(gs[0, 1])
        im = ax_prior.imshow(gaze_prior, cmap='hot')
        ax_prior.set_title('Prior P^F', fontweight='bold')
        ax_prior.axis('off')
        plt.colorbar(im, ax=ax_prior, fraction=0.046)
        
        ax_artifact = fig.add_subplot(gs[0, 2])
        im = ax_artifact.imshow(artifact_map, cmap='gray')
        ax_artifact.set_title('Artifact Map A', fontweight='bold')
        ax_artifact.axis('off')
        plt.colorbar(im, ax=ax_artifact, fraction=0.046)
        
        ax_target = fig.add_subplot(gs[0, 3:5])
        im = ax_target.imshow(gaze_target, cmap='hot')
        ax_target.set_title('Target P^Q (Ground Truth)', fontweight='bold')
        ax_target.axis('off')
        plt.colorbar(im, ax=ax_target, fraction=0.046)
        
        # 第2行：预测结果
        for idx, (method_name, pred) in enumerate(predictions.items()):
            ax = fig.add_subplot(gs[1, idx])
            im = ax.imshow(pred, cmap='hot')
            ax.set_title(f'{method_name}', fontweight='bold', fontsize=9)
            ax.axis('off')
            plt.colorbar(im, ax=ax, fraction=0.046)
        
        fig.suptitle(f'Case Study: {case_id}', fontsize=16, fontweight='bold', y=0.98)
        
        if save_name is None:
            save_name = f'case_{case_id}.pdf'
        
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"✓ Saved case study visualization to {save_path}")
        plt.close()
        
        return save_path
    
    def plot_ablation_study(self, ablation_results: pd.DataFrame,
                           metric: str = 'JSD',
                           save_name: str = 'fig_ablation.pdf') -> Path:
        """
        绘制消融实验结果
        
        Args:
            ablation_results: DataFrame with columns [component, metric_values]
            metric: 要绘制的指标
            save_name: 保存文件名
            
        Returns:
            保存路径
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # 条形图
        components = ablation_results['component'].tolist()
        values = ablation_results[metric].tolist()
        
        colors = plt.cm.RdYlGn_r(np.linspace(0.3, 0.7, len(components)))
        ax1.bar(components, values, color=colors, edgecolor='black', linewidth=1.5)
        ax1.set_ylabel(f'{metric}', fontsize=12, fontweight='bold')
        ax1.set_title(f'Ablation Study: {metric}', fontsize=12, fontweight='bold')
        ax1.set_xticklabels(components, rotation=45, ha='right')
        ax1.grid(axis='y', alpha=0.3)
        
        # 改进百分比
        baseline = values[0]
        improvements = [(baseline - v) / baseline * 100 if baseline > 0 else 0 for v in values]
        
        colors_imp = ['red' if x < 0 else 'green' for x in improvements]
        ax2.bar(components, improvements, color=colors_imp, edgecolor='black', linewidth=1.5, alpha=0.7)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_ylabel('Improvement (%)', fontsize=12, fontweight='bold')
        ax2.set_title('Improvement vs Baseline', fontsize=12, fontweight='bold')
        ax2.set_xticklabels(components, rotation=45, ha='right')
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"✓ Saved ablation study to {save_path}")
        plt.close()
        
        return save_path
    
    def plot_distortion_analysis(self, results_by_distortion: Dict[str, pd.DataFrame],
                                metric: str = 'CC',
                                save_name: str = 'fig_distortion.pdf') -> Path:
        """
        按失真类型分析性能
        
        Args:
            results_by_distortion: {distortion_type: results_df}
            metric: 要绘制的指标
            save_name: 保存文件名
            
        Returns:
            保存路径
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        for idx, (dist_type, results) in enumerate(results_by_distortion.items()):
            if idx >= 4:
                break
            
            methods = results.index.tolist()
            values = results[metric].tolist()
            
            axes[idx].bar(methods, values, color='skyblue', edgecolor='black', linewidth=1.5)
            axes[idx].set_title(f'Distortion Type: {dist_type}', fontweight='bold')
            axes[idx].set_ylabel(metric, fontweight='bold')
            axes[idx].set_xticklabels(methods, rotation=45, ha='right')
            axes[idx].grid(axis='y', alpha=0.3)
        
        plt.suptitle(f'Performance by Distortion Type', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"✓ Saved distortion analysis to {save_path}")
        plt.close()
        
        return save_path
    
    def plot_ceiling_comparison(self, method_scores: Dict[str, np.ndarray],
                               ceiling_value: float,
                               save_name: str = 'fig_ceiling.pdf') -> Path:
        """
        绘制与ceiling的对比
        
        Args:
            method_scores: {method_name: scores_array}
            ceiling_value: ceiling值
            save_name: 保存文件名
            
        Returns:
            保存路径
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        methods = list(method_scores.keys())
        means = [np.mean(scores) for scores in method_scores.values()]
        stds = [np.std(scores) for scores in method_scores.values()]
        
        x = np.arange(len(methods))
        colors = plt.cm.Set3(np.linspace(0, 1, len(methods)))
        
        # 条形图加误差条
        ax.bar(x, means, yerr=stds, capsize=5, color=colors, 
              edgecolor='black', linewidth=1.5, alpha=0.8)
        
        # 添加ceiling线
        ax.axhline(y=ceiling_value, color='red', linestyle='--', linewidth=2.5, 
                  label=f'Ceiling: {ceiling_value:.4f}')
        
        ax.set_ylabel('Score', fontsize=12, fontweight='bold')
        ax.set_title('Performance vs Ceiling (Upper Bound)', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(methods, rotation=45, ha='right')
        ax.legend(fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        
        save_path = self.output_dir / save_name
        plt.tight_layout()
        plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        logger.info(f"✓ Saved ceiling comparison to {save_path}")
        plt.close()
        
        return save_path


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    viz = PaperVisualizer(Path('/tmp/test_viz'))
    
    # 生成示例数据
    np.random.seed(42)
    
    # 示例表格
    results = pd.DataFrame({
        'Method': ['Our SC-TAS', 'LB1-Ridge', 'LB2-CNN', 'Prior-only', 'Artifact-only'],
        'JSD': np.random.random(5) * 0.3,
        'CC': np.random.random(5) * 0.4 + 0.5,
        'NSS': np.random.random(5) * 2,
    })
    results = results.set_index('Method')
    
    viz.plot_main_results_table(results)
    print("✓ Test visualization completed")
