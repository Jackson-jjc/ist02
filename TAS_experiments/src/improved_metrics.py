"""
改进的指标计算和统计分析
符合期刊要求的规范化指标与统计检验
"""

import numpy as np
import scipy.stats as stats
from scipy.spatial.distance import jensenshannon
from typing import Dict, Tuple, List, Optional
import pandas as pd
import logging
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class ImprovedMetrics:
    """改进的指标计算库"""
    
    @staticmethod
    def correlation_coefficient(pred: np.ndarray, target: np.ndarray,
                               method: str = 'pearson') -> float:
        """
        计算相关系数 (CC)
        
        Args:
            pred: 预测分布
            target: 目标分布
            method: 相关方法 ('pearson', 'spearman')
            
        Returns:
            相关系数 [-1, 1]
        """
        # 展平
        pred_flat = pred.flatten()
        target_flat = target.flatten()
        
        if method == 'pearson':
            corr, _ = stats.pearsonr(pred_flat, target_flat)
        elif method == 'spearman':
            corr, _ = stats.spearmanr(pred_flat, target_flat)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return float(np.nan_to_num(corr, nan=0.0))
    
    @staticmethod
    def jensen_shannon_divergence(pred: np.ndarray, target: np.ndarray) -> float:
        """
        计算Jensen-Shannon散度 (JSD)
        最小化目标，值域 [0, 1]
        
        Args:
            pred: 预测分布 (概率)
            target: 目标分布 (概率)
            
        Returns:
            JSD 值 [0, 1]
        """
        # 归一化
        pred_norm = pred.flatten() / (pred.sum() + 1e-10)
        target_norm = target.flatten() / (target.sum() + 1e-10)
        
        # 计算JSD
        jsd = jensenshannon(pred_norm, target_norm, base=2)
        
        return float(jsd)
    
    @staticmethod
    def kullback_leibler_divergence(pred: np.ndarray, target: np.ndarray) -> float:
        """
        计算Kullback-Leibler散度 (KL)
        
        Args:
            pred: 预测分布 (概率)
            target: 目标分布 (参考)
            
        Returns:
            KL(target || pred) 值
        """
        pred_norm = pred.flatten() / (pred.sum() + 1e-10)
        target_norm = target.flatten() / (target.sum() + 1e-10)
        
        # KL(target || pred)
        kl = np.sum(target_norm * np.log(target_norm / (pred_norm + 1e-10) + 1e-10))
        
        return float(np.maximum(kl, 0))
    
    @staticmethod
    def normalized_scanpath_saliency(pred: np.ndarray, fixations: np.ndarray) -> float:
        """
        计算Normalized Scanpath Saliency (NSS)
        高分表示预测在fixation处的值高
        
        Args:
            pred: 预测显著性图 (概率或log概率)
            fixations: Fixation位置 (H, W) 二值图
            
        Returns:
            NSS 值
        """
        # 标准化预测图
        pred_norm = (pred - pred.mean()) / (pred.std() + 1e-10)
        
        # 获取fixation处的值
        if fixations.sum() == 0:
            return 0.0
        
        nss = pred_norm[fixations > 0].mean()
        
        return float(nss)
    
    @staticmethod
    def similarity_metric(pred: np.ndarray, target: np.ndarray) -> float:
        """
        计算相似性度量 (SIM)
        也称为直方图交集
        
        Args:
            pred: 预测分布
            target: 目标分布
            
        Returns:
            SIM 值 [0, 1]
        """
        # 直方图化处理
        pred_hist = pred.flatten() / (pred.sum() + 1e-10)
        target_hist = target.flatten() / (target.sum() + 1e-10)
        
        # 直方图交集
        sim = np.minimum(pred_hist, target_hist).sum()
        
        return float(sim)
    
    @staticmethod
    def auc_judd(pred: np.ndarray, fixations: np.ndarray, 
                n_samples: int = 1000) -> float:
        """
        计算AUC-Judd指标
        
        Args:
            pred: 预测显著性图
            fixations: Fixation位置 (二值图)
            n_samples: 用于计算的负样本数
            
        Returns:
            AUC 值 [0, 1]
        """
        if fixations.sum() == 0:
            return 0.5
        
        # 正样本
        pos = pred[fixations > 0]
        
        # 随机采样负样本
        neg_idx = np.where(fixations == 0)
        if len(neg_idx[0]) > n_samples:
            sample_idx = np.random.choice(len(neg_idx[0]), n_samples, replace=False)
            neg = pred[neg_idx[0][sample_idx], neg_idx[1][sample_idx]]
        else:
            neg = pred[fixations == 0]
        
        # 计算AUC
        auc = (pos[:, np.newaxis] > neg[np.newaxis, :]).mean()
        
        return float(auc)


class CeilingCalculator:
    """计算评估上界 (Ceiling)"""
    
    @staticmethod
    def inter_observer_ceiling(observers_data: List[np.ndarray],
                               metric_func) -> Dict[str, float]:
        """
        计算观察者间一致性 (作为ceiling)
        
        Args:
            observers_data: 多个观察者的数据 (不同被试、不同扫视)
            metric_func: 指标计算函数
            
        Returns:
            指标的平均一致性值
        """
        if len(observers_data) < 2:
            logger.warning("Need at least 2 observers for ceiling calculation")
            return {}
        
        ceiling = {}
        
        # 两两计算一致性
        scores = []
        for i in range(len(observers_data)):
            for j in range(i + 1, len(observers_data)):
                score = metric_func(observers_data[i], observers_data[j])
                scores.append(score)
        
        ceiling['mean'] = float(np.mean(scores))
        ceiling['std'] = float(np.std(scores))
        ceiling['min'] = float(np.min(scores))
        ceiling['max'] = float(np.max(scores))
        ceiling['ci_95'] = (
            float(np.percentile(scores, 2.5)),
            float(np.percentile(scores, 97.5))
        )
        
        return ceiling
    
    @staticmethod
    def split_half_reliability(data: np.ndarray, 
                              metric_func, 
                              n_splits: int = 100) -> Dict[str, float]:
        """
        计算分半信度 (Split-half reliability)
        
        Args:
            data: 输入数据
            metric_func: 指标计算函数
            n_splits: 分割次数
            
        Returns:
            可靠性统计
        """
        scores = []
        
        for _ in range(n_splits):
            # 随机分割
            indices = np.arange(len(data))
            np.random.shuffle(indices)
            mid = len(indices) // 2
            
            half1 = data[indices[:mid]]
            half2 = data[indices[mid:]]
            
            # 计算指标
            score = metric_func(half1, half2)
            scores.append(score)
        
        return {
            'mean': float(np.mean(scores)),
            'std': float(np.std(scores)),
            'ci_95': (float(np.percentile(scores, 2.5)),
                     float(np.percentile(scores, 97.5))),
        }


class StatisticalAnalyzer:
    """统计分析"""
    
    @staticmethod
    def paired_comparison(method_a_scores: np.ndarray,
                         method_b_scores: np.ndarray,
                         metric_name: str = 'Metric') -> Dict:
        """
        配对比较 (Paired t-test 或 Wilcoxon signed-rank)
        
        Args:
            method_a_scores: 方法A的分数 (每个content一个)
            method_b_scores: 方法B的分数
            metric_name: 指标名称
            
        Returns:
            统计检验结果
        """
        # 检查正态性
        _, p_norm_a = stats.shapiro(method_a_scores)
        _, p_norm_b = stats.shapiro(method_b_scores)
        
        is_normal = (p_norm_a > 0.05) and (p_norm_b > 0.05)
        
        if is_normal:
            # 配对t检验
            t_stat, p_value = stats.ttest_rel(method_a_scores, method_b_scores)
            test_name = "Paired t-test"
        else:
            # Wilcoxon signed-rank检验
            w_stat, p_value = stats.wilcoxon(method_a_scores, method_b_scores)
            t_stat = w_stat
            test_name = "Wilcoxon signed-rank"
        
        # 效应量: Cohen's d
        mean_diff = method_a_scores.mean() - method_b_scores.mean()
        pooled_std = np.sqrt((method_a_scores.std()**2 + method_b_scores.std()**2) / 2)
        cohens_d = mean_diff / (pooled_std + 1e-10)
        
        # 效应大小解释
        if abs(cohens_d) < 0.2:
            effect_size = 'negligible'
        elif abs(cohens_d) < 0.5:
            effect_size = 'small'
        elif abs(cohens_d) < 0.8:
            effect_size = 'medium'
        else:
            effect_size = 'large'
        
        return {
            'metric': metric_name,
            'test': test_name,
            'statistic': float(t_stat),
            'p_value': float(p_value),
            'cohens_d': float(cohens_d),
            'effect_size': effect_size,
            'is_significant': p_value < 0.05,
            'mean_A': float(method_a_scores.mean()),
            'mean_B': float(method_b_scores.mean()),
            'mean_diff': float(mean_diff),
            'ci_95': StatisticalAnalyzer._bootstrap_ci(method_a_scores - method_b_scores),
        }
    
    @staticmethod
    def _bootstrap_ci(differences: np.ndarray, 
                     n_bootstrap: int = 10000,
                     ci: float = 0.95) -> Tuple[float, float]:
        """Bootstrap置信区间"""
        bootstrap_means = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(differences, len(differences), replace=True)
            bootstrap_means.append(sample.mean())
        
        alpha = (1 - ci) / 2
        lower = np.percentile(bootstrap_means, alpha * 100)
        upper = np.percentile(bootstrap_means, (1 - alpha) * 100)
        
        return (float(lower), float(upper))
    
    @staticmethod
    def holm_bonferroni_correction(p_values: np.ndarray,
                                   alpha: float = 0.05) -> Dict:
        """
        Holm-Bonferroni多重比较校正
        
        Args:
            p_values: p值数组
            alpha: 显著性水平
            
        Returns:
            校正后的结果
        """
        n_tests = len(p_values)
        sorted_idx = np.argsort(p_values)
        sorted_p = p_values[sorted_idx]
        
        corrected_p = np.zeros_like(sorted_p)
        for i, p in enumerate(sorted_p):
            corrected_p[i] = p * (n_tests - i)
            corrected_p[i] = min(corrected_p[i], 1.0)
        
        # 恢复原始顺序
        original_corrected = np.zeros_like(corrected_p)
        original_corrected[sorted_idx] = corrected_p
        
        return {
            'original_p': p_values,
            'corrected_p': original_corrected,
            'is_significant': original_corrected < alpha,
        }
    
    @staticmethod
    def generate_statistical_report(results_df: pd.DataFrame,
                                   metric_columns: List[str]) -> str:
        """
        生成统计报告
        
        Args:
            results_df: 结果DataFrame
            metric_columns: 指标列名
            
        Returns:
            格式化的报告字符串
        """
        report = "=== Statistical Summary Report ===\n\n"
        
        for metric in metric_columns:
            if metric in results_df.columns:
                data = results_df[metric].dropna()
                report += f"{metric}:\n"
                report += f"  Mean ± Std: {data.mean():.4f} ± {data.std():.4f}\n"
                report += f"  Range: [{data.min():.4f}, {data.max():.4f}]\n"
                report += f"  95% CI: [{np.percentile(data, 2.5):.4f}, {np.percentile(data, 97.5):.4f}]\n"
                report += f"  Median: {data.median():.4f}\n\n"
        
        return report


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    # 生成示例数据
    np.random.seed(42)
    pred = np.random.random((256, 256))
    target = np.random.random((256, 256))
    
    metrics = ImprovedMetrics()
    
    print("Testing Metrics:")
    print(f"CC: {metrics.correlation_coefficient(pred, target):.4f}")
    print(f"JSD: {metrics.jensen_shannon_divergence(pred, target):.4f}")
    print(f"KL: {metrics.kullback_leibler_divergence(pred, target):.4f}")
    print(f"SIM: {metrics.similarity_metric(pred, target):.4f}")
    
    # 测试统计
    print("\nTesting Statistics:")
    scores_a = np.random.normal(0.7, 0.1, 20)
    scores_b = np.random.normal(0.72, 0.1, 20)
    
    analyzer = StatisticalAnalyzer()
    result = analyzer.paired_comparison(scores_a, scores_b, "Test Metric")
    print(f"Paired comparison result: p={result['p_value']:.4f}")
