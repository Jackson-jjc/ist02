"""
统计测试和置信区间补充
完整的统计显著性检验和效应量计算
"""

import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import json
import logging
from typing import Dict, Tuple, List

logger = logging.getLogger(__name__)


class StatisticalTester:
    """统计测试器"""
    
    @staticmethod
    def paired_t_test(group1: np.ndarray, group2: np.ndarray, 
                     alpha: float = 0.05) -> Dict:
        """
        执行配对t检验
        
        Args:
            group1, group2: 两组数据
            alpha: 显著性水平
            
        Returns:
            检验结果字典
        """
        t_stat, p_value = stats.ttest_rel(group1, group2)
        
        # Cohen's d
        mean_diff = group1.mean() - group2.mean()
        std_pooled = np.sqrt(((len(group1)-1)*group1.std()**2 + 
                               (len(group2)-1)*group2.std()**2) / 
                              (len(group1) + len(group2) - 2))
        cohens_d = mean_diff / std_pooled if std_pooled > 0 else 0
        
        # 95%置信区间
        se_diff = stats.sem(group1 - group2)
        ci_lower = mean_diff - stats.t.ppf(1 - alpha/2, len(group1)-1) * se_diff
        ci_upper = mean_diff + stats.t.ppf(1 - alpha/2, len(group1)-1) * se_diff
        
        # 效应量解释
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            effect_size_interpretation = "negligible"
        elif abs_d < 0.5:
            effect_size_interpretation = "small"
        elif abs_d < 0.8:
            effect_size_interpretation = "medium"
        else:
            effect_size_interpretation = "large"
        
        return {
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'significant': p_value < alpha,
            'mean_difference': float(mean_diff),
            'cohens_d': float(cohens_d),
            'effect_size_interpretation': effect_size_interpretation,
            'ci_lower': float(ci_lower),
            'ci_upper': float(ci_upper),
            'n': len(group1),
            'group1_mean': float(group1.mean()),
            'group1_std': float(group1.std()),
            'group2_mean': float(group2.mean()),
            'group2_std': float(group2.std()),
        }
    
    @staticmethod
    def confidence_interval_95(data: np.ndarray) -> Tuple[float, float]:
        """计算95%置信区间"""
        mean = data.mean()
        se = stats.sem(data)
        ci = se * stats.t.ppf(1 - 0.05/2, len(data)-1)
        return (mean - ci, mean + ci)
    
    @staticmethod
    def kruskal_wallis_test(*groups) -> Dict:
        """
        执行Kruskal-Wallis H检验(非参数)
        
        用于多组比较，无需假设正态性
        """
        h_stat, p_value = stats.kruskal(*groups)
        
        # 计算eta-squared (效应量)
        n_total = sum(len(g) for g in groups)
        # 简化的eta-squared估计
        
        return {
            'h_statistic': float(h_stat),
            'p_value': float(p_value),
            'significant': p_value < 0.05,
            'n_groups': len(groups),
            'total_n': n_total,
        }
    
    @staticmethod
    def bonferroni_correction(n_comparisons: int, 
                             alpha: float = 0.05) -> float:
        """
        Bonferroni多重比较校正
        
        Returns:
            调整后的显著性水平
        """
        return alpha / n_comparisons


class TableGenerator:
    """统计表格生成器"""
    
    @staticmethod
    def generate_method_comparison_table(results_df: pd.DataFrame) -> pd.DataFrame:
        """
        生成方法对比汇总表
        
        Args:
            results_df: 包含['cc_freelook', 'cc_tas_nr', 'cc_tas_fr', ...]的数据框
            
        Returns:
            方法对比表
        """
        methods = ['FreeLook', 'TAS-NR', 'TAS-FR', 'Artifact', 'Mixture']
        column_map = {
            'FreeLook': 'cc_freelook',
            'TAS-NR': 'cc_tas_nr',
            'TAS-FR': 'cc_tas_fr' if 'cc_tas_fr' in results_df.columns else 'cc_freelook',
            'Artifact': 'artifact_cc' if 'artifact_cc' in results_df.columns else 'cc_freelook',
            'Mixture': 'mixture_cc' if 'mixture_cc' in results_df.columns else 'cc_freelook',
        }
        
        tester = StatisticalTester()
        comparison_data = []
        
        for method, col in column_map.items():
            if col in results_df.columns:
                data = results_df[col].dropna().values
                ci_lower, ci_upper = tester.confidence_interval_95(data)
                
                comparison_data.append({
                    'Method': method,
                    'Mean CC': f"{data.mean():.4f}",
                    '±SD': f"{data.std():.4f}",
                    '95% CI': f"[{ci_lower:.4f}, {ci_upper:.4f}]",
                    'N': len(data),
                    'Min': f"{data.min():.4f}",
                    'Max': f"{data.max():.4f}",
                })
        
        return pd.DataFrame(comparison_data)
    
    @staticmethod
    def generate_statistical_tests_table(results_df: pd.DataFrame) -> pd.DataFrame:
        """
        生成成对比较统计表
        """
        tester = StatisticalTester()
        
        # 获取可用列
        cc_cols = [col for col in results_df.columns if col.startswith('cc_')]
        
        test_results = []
        
        for i, col1 in enumerate(cc_cols):
            for col2 in cc_cols[i+1:]:
                group1 = results_df[col1].dropna().values
                group2 = results_df[col2].dropna().values
                
                if len(group1) > 0 and len(group2) > 0:
                    result = tester.paired_t_test(group1, group2)
                    result['comparison'] = f"{col1} vs {col2}"
                    test_results.append(result)
        
        df_tests = pd.DataFrame(test_results)
        
        # 计算Bonferroni校正
        n_tests = len(test_results)
        bonf_alpha = tester.bonferroni_correction(n_tests)
        df_tests['bonferroni_significant'] = df_tests['p_value'] < bonf_alpha
        
        return df_tests
    
    @staticmethod
    def generate_content_complexity_analysis(results_df: pd.DataFrame) -> Dict:
        """
        按内容复杂度进行亚组分析
        """
        # 按cc_tas_nr的表现分类
        tud_data = results_df.groupby('content')['cc_tas_nr'].agg(['mean', 'std', 'count']).reset_index()
        tud_data = tud_data.sort_values('mean')
        
        complexity_levels = {
            'Low (CC < 0.65)': tud_data[tud_data['mean'] < 0.65],
            'Medium (0.65 ≤ CC < 0.88)': tud_data[(tud_data['mean'] >= 0.65) & (tud_data['mean'] < 0.88)],
            'High (CC ≥ 0.88)': tud_data[tud_data['mean'] >= 0.88],
        }
        
        analysis = {}
        
        for level, data in complexity_levels.items():
            if len(data) > 0:
                contents = data['content'].tolist()
                subset = results_df[results_df['content'].isin(contents)]
                
                analysis[level] = {
                    'n_contents': len(contents),
                    'contents': contents,
                    'cc_mean': float(subset['cc_tas_nr'].mean()),
                    'cc_std': float(subset['cc_tas_nr'].std()),
                    'cc_min': float(subset['cc_tas_nr'].min()),
                    'cc_max': float(subset['cc_tas_nr'].max()),
                    'sample_size': len(subset),
                }
        
        return analysis


def generate_complete_statistical_report(results_dir: str, 
                                        results_file: str = None):
    """
    生成完整统计报告
    """
    results_path = Path(results_dir)
    
    # 加载结果
    if results_file is None:
        # 查找最新的结果文件
        nr_files = list(results_path.glob('results_nr_v4_*.csv'))
        if nr_files:
            results_file = sorted(nr_files)[-1]
        else:
            raise FileNotFoundError("找不到TUD结果文件")
    
    df = pd.read_csv(results_file)
    logger.info(f"加载结果: {results_file}")
    
    tester = StatisticalTester()
    table_gen = TableGenerator()
    
    # 生成各类表格
    print("\n=" * 70)
    print("1. 方法对比汇总表")
    print("=" * 70)
    method_table = table_gen.generate_method_comparison_table(df)
    print(method_table.to_string(index=False))
    method_table.to_csv(results_path / 'table_method_comparison.csv', index=False)
    
    print("\n" + "=" * 70)
    print("2. 成对比较统计表 (配对t检验)")
    print("=" * 70)
    stat_table = table_gen.generate_statistical_tests_table(df)
    print(stat_table[['comparison', 't_statistic', 'p_value', 'bonferroni_significant', 
                      'cohens_d', 'effect_size_interpretation']].to_string(index=False))
    stat_table.to_csv(results_path / 'table_statistical_tests.csv', index=False)
    
    print("\n" + "=" * 70)
    print("3. 内容复杂度亚组分析")
    print("=" * 70)
    complexity_analysis = table_gen.generate_content_complexity_analysis(df)
    for level, data in complexity_analysis.items():
        print(f"\n{level}:")
        print(f"  样本数: {data['n_contents']} 个内容")
        print(f"  CC: {data['cc_mean']:.4f} ± {data['cc_std']:.4f}")
        print(f"  范围: [{data['cc_min']:.4f}, {data['cc_max']:.4f}]")
        print(f"  总样本: {data['sample_size']}")
    
    # 保存分析结果
    with open(results_path / 'content_complexity_analysis.json', 'w') as f:
        json.dump(complexity_analysis, f, indent=2)
    
    print("\n✓ 统计报告已完成")
    print(f"  文件位置: {results_path}/")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    from typing import Dict, Tuple
    results_dir = '/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments/results'
    generate_complete_statistical_report(results_dir)
