"""
任务9: 失败案例分析 - 识别最差表现内容的共同特征
"""

import numpy as np
import pandas as pd
from pathlib import Path
import logging
import json
from typing import Dict, List

logger = logging.getLogger(__name__)


class FailureCaseAnalyzer:
    """失败案例深度分析"""
    
    def __init__(self, results_file: str, output_dir: str):
        self.results_df = pd.read_csv(results_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"加载数据: {len(self.results_df)} 行, {self.results_df['content'].nunique()} 个内容")
    
    def identify_worst_cases(self, n_worst: int = 5) -> pd.DataFrame:
        """识别最差的N个内容"""
        
        # 按CC均值计算
        content_stats = self.results_df.groupby('content')['cc_tas_nr'].agg([
            'mean', 'std', 'min', 'max', 'count'
        ]).sort_values('mean')
        
        worst_cases = content_stats.head(n_worst)
        
        logger.info(f"\n最差表现的 {n_worst} 个内容:")
        for content, row in worst_cases.iterrows():
            logger.info(f"  {content}: CC={row['mean']:.4f} (±{row['std']:.4f}), "
                       f"范围=[{row['min']:.4f}, {row['max']:.4f}]")
        
        return worst_cases
    
    def analyze_compression_impact_on_failures(self, worst_contents: List[str]) -> Dict:
        """分析压缩级别对最差内容的影响"""
        
        logger.info(f"\n压缩级别影响分析 (最差内容):")
        
        analysis = {}
        
        for content in worst_contents:
            subset = self.results_df[self.results_df['content'] == content]
            level_stats = subset.groupby('level')['cc_tas_nr'].agg(['mean', 'std', 'count'])
            
            logger.info(f"\n{content}:")
            for level, row in level_stats.iterrows():
                logger.info(f"    Level {level}: CC={row['mean']:.4f} (±{row['std']:.4f})")
            
            # 计算压缩对性能的影响
            if len(level_stats) > 1:
                level_trend = level_stats['mean'].values
                trend_slope = np.polyfit(range(len(level_trend)), level_trend, 1)[0]
                analysis[content] = {
                    'level_means': level_stats['mean'].tolist(),
                    'level_stds': level_stats['std'].tolist(),
                    'trend_slope': float(trend_slope),
                    'degradation': f"{'增加' if trend_slope > 0 else '减少'}随压缩级别"
                }
        
        return analysis
    
    def compare_with_best_cases(self, worst_cases: pd.DataFrame, 
                                best_n: int = 3) -> Dict:
        """对比最差与最好表现的差异"""
        
        content_stats = self.results_df.groupby('content')['cc_tas_nr'].agg(['mean', 'std'])
        best_cases = content_stats.sort_values('mean', ascending=False).head(best_n)
        
        logger.info(f"\n最好与最差内容的对比:")
        logger.info(f"  最好内容 (Top {best_n}):")
        for content, row in best_cases.iterrows():
            logger.info(f"    {content}: CC={row['mean']:.4f}")
        
        logger.info(f"  最差内容 (Bottom {len(worst_cases)}):")
        for content, row in worst_cases.iterrows():
            logger.info(f"    {content}: CC={row['mean']:.4f}")
        
        # 计算差异
        best_mean = best_cases['mean'].mean()
        worst_mean = worst_cases['mean'].mean()
        gap = best_mean - worst_mean
        
        logger.info(f"\n  差异分析:")
        logger.info(f"    最好平均: {best_mean:.4f}")
        logger.info(f"    最差平均: {worst_mean:.4f}")
        logger.info(f"    差距: {gap:.4f} ({gap/best_mean*100:.1f}% 相对下降)")
        
        return {
            'best_cases': best_cases.to_dict('index'),
            'worst_cases': worst_cases.to_dict('index'),
            'best_mean': float(best_mean),
            'worst_mean': float(worst_mean),
            'gap': float(gap),
            'relative_decline_pct': float(gap/best_mean*100)
        }
    
    def identify_failure_patterns(self, worst_contents: List[str]) -> Dict:
        """识别失败内容的共同特征"""
        
        logger.info(f"\n失败模式分析:")
        
        patterns = {
            'high_variability': [],      # 高方差内容
            'poor_across_all_levels': [], # 所有压缩级别都差
            'specific_level_failures': {} # 特定压缩级别失败
        }
        
        for content in worst_contents:
            subset = self.results_df[self.results_df['content'] == content]
            
            # 1. 检查方差
            cc_std = subset['cc_tas_nr'].std()
            if cc_std > 0.1:
                patterns['high_variability'].append({
                    'content': content,
                    'std': float(cc_std),
                    'note': '内容显著性预测不稳定'
                })
            
            # 2. 检查跨压缩级别的一致性差
            level_means = subset.groupby('level')['cc_tas_nr'].mean()
            if level_means.std() > 0.05:
                patterns['poor_across_all_levels'].append({
                    'content': content,
                    'level_std': float(level_means.std()),
                    'note': '不同压缩级别表现差异大'
                })
            
            # 3. 特定级别失败
            worst_level = level_means.idxmin()
            if level_means[worst_level] < 0.3:
                if worst_level not in patterns['specific_level_failures']:
                    patterns['specific_level_failures'][worst_level] = []
                patterns['specific_level_failures'][worst_level].append({
                    'content': content,
                    'cc_at_level': float(level_means[worst_level])
                })
        
        return patterns
    
    def generate_failure_report(self) -> Dict:
        """生成完整的失败案例报告"""
        
        logger.info("\n" + "="*70)
        logger.info("执行失败案例深度分析")
        logger.info("="*70)
        
        # 1. 识别最差案例
        worst_cases = self.identify_worst_cases(n_worst=5)
        worst_contents = worst_cases.index.tolist()
        
        # 2. 压缩影响分析
        compression_impact = self.analyze_compression_impact_on_failures(worst_contents)
        
        # 3. 最好/最差对比
        comparison = self.compare_with_best_cases(worst_cases, best_n=3)
        
        # 4. 失败模式识别
        failure_patterns = self.identify_failure_patterns(worst_contents)
        
        # 生成建议
        logger.info(f"\n改进建议:")
        
        suggestions = self._generate_suggestions(failure_patterns, worst_cases)
        for i, suggestion in enumerate(suggestions, 1):
            logger.info(f"  {i}. {suggestion}")
        
        # 保存完整报告
        report = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'worst_cases': worst_cases.to_dict('index'),
            'compression_impact': compression_impact,
            'best_vs_worst_comparison': comparison,
            'failure_patterns': failure_patterns,
            'improvement_suggestions': suggestions
        }
        
        report_file = self.output_dir / 'failure_case_analysis_comprehensive.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ 完整报告: {report_file}")
        
        # 保存简明表格
        worst_table = worst_cases.reset_index()
        worst_table.columns = ['Content', 'CC Mean', 'CC Std', 'Min', 'Max', 'Samples']
        csv_file = self.output_dir / 'table_worst_cases_analysis.csv'
        worst_table.to_csv(csv_file, index=False)
        logger.info(f"✓ 最差案例表: {csv_file}")
        
        return report
    
    @staticmethod
    def _generate_suggestions(failure_patterns: Dict, worst_cases: pd.DataFrame) -> List[str]:
        """基于失败模式生成改进建议"""
        
        suggestions = []
        
        # 高变异性的改进
        if failure_patterns['high_variability']:
            suggestions.append(
                f"内容复杂性改进: {len(failure_patterns['high_variability'])} 个内容显示高变异性"
                f"（{', '.join([p['content'] for p in failure_patterns['high_variability']])}），"
                f"建议改进显著性地图的平滑性或增加样本"
            )
        
        # 压缩敏感性
        if failure_patterns['poor_across_all_levels']:
            suggestions.append(
                f"压缩鲁棒性: {len(failure_patterns['poor_across_all_levels'])} 个内容对压缩级别敏感，"
                f"建议在模型中加入压缩级别的显式表示或数据增强"
            )
        
        # 特定级别的失败
        if failure_patterns['specific_level_failures']:
            worst_level = max(failure_patterns['specific_level_failures'].keys(),
                            key=lambda k: len(failure_patterns['specific_level_failures'][k]))
            suggestions.append(
                f"极端压缩处理: 压缩级别 {worst_level} 出现 "
                f"{len(failure_patterns['specific_level_failures'][worst_level])} 个失败，"
                f"建议针对极端压缩场景的专门处理"
            )
        
        # 性能差距
        worst_mean = worst_cases['mean'].mean()
        if worst_mean < 0.5:
            suggestions.append(
                f"算法局限: 平均CC={worst_mean:.3f}提示某些场景超出当前算法能力范围，"
                f"可考虑场景分类或多任务学习方法"
            )
        
        if not suggestions:
            suggestions.append("整体表现可接受，无重大改进建议")
        
        return suggestions


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
    
    # 执行失败案例分析
    analyzer = FailureCaseAnalyzer(latest_file, str(config.RESULTS_DIR))
    report = analyzer.generate_failure_report()
    
    print("\n✓ 失败案例分析已完成!")


if __name__ == '__main__':
    main()
