"""
任务8: 亚组分析 - 按内容复杂度分层统计
"""

import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


class SubgroupAnalyzer:
    """内容复杂度亚组分析"""
    
    def __init__(self, results_file: str, output_dir: str):
        self.results_df = pd.read_csv(results_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"加载数据: {len(self.results_df)} 行")
    
    def classify_contents_by_cc(self) -> dict:
        """按CC性能分类内容"""
        
        # 计算每个内容的CC均值
        content_cc = self.results_df.groupby('content')['cc_tas_nr'].agg(['mean', 'std', 'count'])
        content_cc = content_cc.sort_values('mean')
        
        logger.info(f"\n内容CC分布:")
        logger.info(f"  最小: {content_cc['mean'].min():.4f}")
        logger.info(f"  25%位: {content_cc['mean'].quantile(0.25):.4f}")
        logger.info(f"  中位: {content_cc['mean'].median():.4f}")
        logger.info(f"  75%位: {content_cc['mean'].quantile(0.75):.4f}")
        logger.info(f"  最大: {content_cc['mean'].max():.4f}")
        
        # 分类阈值
        q33 = content_cc['mean'].quantile(0.33)
        q67 = content_cc['mean'].quantile(0.67)
        
        # 分类
        groups = {
            'Low': content_cc[content_cc['mean'] <= q33].index.tolist(),
            'Medium': content_cc[(content_cc['mean'] > q33) & (content_cc['mean'] <= q67)].index.tolist(),
            'High': content_cc[content_cc['mean'] > q67].index.tolist()
        }
        
        logger.info(f"\n分类结果:")
        logger.info(f"  Low (≤{q33:.4f}): {len(groups['Low'])} 个内容")
        logger.info(f"  Medium ({q33:.4f}-{q67:.4f}): {len(groups['Medium'])} 个内容")
        logger.info(f"  High (>{q67:.4f}): {len(groups['High'])} 个内容")
        
        return groups, content_cc
    
    def compute_subgroup_statistics(self, groups: dict) -> pd.DataFrame:
        """计算各亚组的统计"""
        
        rows = []
        
        for group_name, contents in groups.items():
            subset = self.results_df[self.results_df['content'].isin(contents)]
            cc_values = subset['cc_tas_nr'].values
            
            # 计算统计量
            mean = cc_values.mean()
            std = cc_values.std()
            se = std / np.sqrt(len(cc_values))
            
            # 95% 置信区间
            ci = stats.t.interval(0.95, len(cc_values)-1, loc=mean, scale=se)
            
            rows.append({
                'Group': group_name,
                'N Contents': len(contents),
                'N Samples': len(subset),
                'CC Mean': mean,
                'CC Std': std,
                'SE': se,
                'CI Lower': ci[0],
                'CI Upper': ci[1],
                'Min': cc_values.min(),
                'Max': cc_values.max(),
                'Median': np.median(cc_values),
                'Skewness': stats.skew(cc_values),
                'Kurtosis': stats.kurtosis(cc_values)
            })
        
        df = pd.DataFrame(rows)
        
        # 保存
        output_file = self.output_dir / 'table_subgroup_statistics.csv'
        df.to_csv(output_file, index=False)
        logger.info(f"\n✓ 亚组统计表: {output_file}")
        
        return df
    
    def perform_kruskal_wallis_test(self, groups: dict) -> dict:
        """执行Kruskal-Wallis H检验"""
        
        logger.info("\n执行Kruskal-Wallis H检验:")
        
        # 提取各组数据
        group_data = []
        group_labels = []
        
        for group_name, contents in groups.items():
            subset = self.results_df[self.results_df['content'].isin(contents)]
            group_data.append(subset['cc_tas_nr'].values)
            group_labels.append(group_name)
        
        # 执行H检验
        h_stat, p_value = stats.kruskal(*group_data)
        
        logger.info(f"  H-statistic: {h_stat:.4f}")
        logger.info(f"  p-value: {p_value:.4e}")
        logger.info(f"  显著: {'✓' if p_value < 0.05 else '✗'}")
        
        # 计算效应量 (Epsilon-squared)
        n = len(self.results_df)
        k = len(groups)
        epsilon_sq = (h_stat - k + 1) / (n - k)
        
        logger.info(f"  Epsilon-squared: {epsilon_sq:.4f}")
        logger.info(f"  效应量解释: {self._interpret_epsilon(epsilon_sq)}")
        
        # 配对比较 (Mann-Whitney U test)
        logger.info("\n配对比较 (Mann-Whitney U):")
        pairwise_results = []
        
        group_names = list(groups.keys())
        for i in range(len(group_names)):
            for j in range(i+1, len(group_names)):
                name1, name2 = group_names[i], group_names[j]
                data1 = group_data[i]
                data2 = group_data[j]
                
                u_stat, p_val = stats.mannwhitneyu(data1, data2, alternative='two-sided')
                
                logger.info(f"  {name1} vs {name2}: U={u_stat:.2f}, p={p_val:.4e}")
                
                pairwise_results.append({
                    'Group1': name1,
                    'Group2': name2,
                    'U-statistic': u_stat,
                    'p-value': p_val,
                    'Significant': 'Yes' if p_val < 0.05 else 'No'
                })
        
        return {
            'h_statistic': h_stat,
            'p_value': p_value,
            'epsilon_squared': epsilon_sq,
            'pairwise': pairwise_results
        }
    
    @staticmethod
    def _interpret_epsilon(eps_sq: float) -> str:
        """解释Epsilon-squared效应量"""
        if eps_sq < 0.01:
            return "小效应"
        elif eps_sq < 0.06:
            return "中等效应"
        else:
            return "大效应"
    
    def generate_comprehensive_report(self) -> dict:
        """生成完整的亚组分析报告"""
        
        logger.info("\n" + "="*70)
        logger.info("执行亚组分析")
        logger.info("="*70)
        
        # 分类
        groups, content_cc = self.classify_contents_by_cc()
        
        # 统计
        subgroup_stats = self.compute_subgroup_statistics(groups)
        logger.info("\n亚组统计:")
        logger.info(subgroup_stats.to_string())
        
        # 假设检验
        kw_results = self.perform_kruskal_wallis_test(groups)
        
        # 生成汇总JSON
        summary = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'subgroup_statistics': subgroup_stats.to_dict('records'),
            'kruskal_wallis_test': {
                'h_statistic': float(kw_results['h_statistic']),
                'p_value': float(kw_results['p_value']),
                'epsilon_squared': float(kw_results['epsilon_squared']),
                'interpretation': self._interpret_epsilon(kw_results['epsilon_squared'])
            },
            'pairwise_comparisons': kw_results['pairwise'],
            'group_definitions': {
                'Low': f"CC <= {content_cc['mean'].quantile(0.33):.4f}",
                'Medium': f"{content_cc['mean'].quantile(0.33):.4f} < CC <= {content_cc['mean'].quantile(0.67):.4f}",
                'High': f"CC > {content_cc['mean'].quantile(0.67):.4f}"
            }
        }
        
        # 保存JSON
        json_file = self.output_dir / 'subgroup_analysis_comprehensive.json'
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"✓ 完整报告: {json_file}")
        
        return summary


def main():
    """主函数"""
    import sys
    sys.path.insert(0, '/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments')
    from src.config import Config
    
    logging.basicConfig(level=logging.INFO)
    config = Config()
    
    # 找最新结果文件
    import glob
    result_files = glob.glob(str(config.RESULTS_DIR / 'results_nr_v4_*.csv'))
    if not result_files:
        print("❌ 未找到结果文件!")
        return
    
    latest_file = sorted(result_files)[-1]
    print(f"使用结果文件: {latest_file}")
    
    # 执行亚组分析
    analyzer = SubgroupAnalyzer(latest_file, str(config.RESULTS_DIR))
    report = analyzer.generate_comprehensive_report()
    
    print("\n✓ 亚组分析已完成!")


if __name__ == '__main__':
    main()
