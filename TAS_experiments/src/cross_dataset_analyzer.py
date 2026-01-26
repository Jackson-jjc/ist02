"""
跨数据集分析框架
支持TUD和JIST01的统一分析
"""

import os
import numpy as np
import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error
import scipy.io as sio

logger = logging.getLogger(__name__)


class CrossDatasetAnalyzer:
    """跨数据集分析器"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"初始化跨数据集分析器: {output_dir}")
    
    def load_jist01_data(self, data_root: str, 
                        transformations: List[str] = None) -> Dict:
        """
        加载JIST01数据 - 支持多种变换
        
        Args:
            data_root: JIST01数据根目录
            transformations: 要加载的变换列表 (None=全部)
            
        Returns:
            {transformation: {gaze_maps, n_images}}
        """
        fixation_dir = Path(data_root) / 'fixation' / 'fixation'
        mat_files = list(fixation_dir.glob('*.mat'))
        
        available_transforms = sorted([f.stem for f in mat_files])
        logger.info(f"JIST01找到{len(available_transforms)}种变换")
        
        if transformations is None:
            # 默认加载关键变换: Reference + 关键影响因素
            transformations = [
                'Reference',
                'MotionBlur_1', 'MotionBlur_2',
                'Noise_1', 'Noise_2',
                'Compression_1', 'Compression_2',
                'ContrastChange_1', 'ContrastChange_2'
            ]
            transformations = [t for t in transformations if t in available_transforms]
        
        results = {}
        
        for trans in transformations:
            try:
                mat_file = fixation_dir / f"{trans}.mat"
                data = sio.loadmat(str(mat_file), squeeze_me=True)
                fixation_vec = data['fixation_vec']
                
                # fixation_vec 包含100个注视点图 (1080x1920)
                gaze_maps = []
                for i, fmap in enumerate(fixation_vec):
                    # 归一化到[0, 1]
                    if isinstance(fmap, np.ndarray):
                        if fmap.max() > 1:
                            fmap_norm = fmap.astype(np.float32) / 255.0
                        else:
                            fmap_norm = fmap.astype(np.float32)
                        gaze_maps.append(fmap_norm)
                
                results[trans] = {
                    'gaze_maps': np.array(gaze_maps),  # shape: (100, 1080, 1920)
                    'n_images': len(gaze_maps),
                    'resolution': (1920, 1080)
                }
                logger.info(f"  ✓ {trans}: {len(gaze_maps)} 张显著性图")
                
            except Exception as e:
                logger.error(f"  ✗ {trans}: {e}")
                continue
        
        return results
    
    def compute_gaze_statistics(self, gaze_maps: np.ndarray) -> Dict:
        """
        计算注视点图的统计特征
        
        Args:
            gaze_maps: shape (n_maps, H, W) 的显著性图
            
        Returns:
            统计字典
        """
        return {
            'mean_saliency': float(gaze_maps.mean()),
            'std_saliency': float(gaze_maps.std()),
            'max_saliency': float(gaze_maps.max()),
            'entropy': float(stats.entropy(gaze_maps.flatten() + 1e-8)),
            'sparsity': float((gaze_maps < 0.1).sum() / gaze_maps.size),
        }
    
    def compare_transformations(self, jist01_data: Dict) -> pd.DataFrame:
        """
        对比不同变换对显著性的影响
        
        Args:
            jist01_data: JIST01数据
            
        Returns:
            对比表
        """
        comparisons = []
        reference_maps = None
        
        for trans, data in jist01_data.items():
            gaze_maps = data['gaze_maps']
            stats_dict = self.compute_gaze_statistics(gaze_maps)
            stats_dict['transformation'] = trans
            stats_dict['n_images'] = data['n_images']
            
            if trans == 'Reference':
                reference_maps = gaze_maps
            
            comparisons.append(stats_dict)
        
        df = pd.DataFrame(comparisons)
        
        # 计算与Reference的差异
        if reference_maps is not None:
            ref_stats = self.compute_gaze_statistics(reference_maps)
            df['delta_saliency'] = df['mean_saliency'] - ref_stats['mean_saliency']
            df['delta_entropy'] = df['entropy'] - ref_stats['entropy']
        
        return df
    
    def generate_cross_dataset_summary(self, tud_results: pd.DataFrame,
                                       jist01_results: Dict) -> Dict:
        """
        生成跨数据集对比汇总
        
        Args:
            tud_results: TUD实验结果
            jist01_results: JIST01数据统计
            
        Returns:
            汇总字典
        """
        summary = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'datasets': {
                'TUD': {
                    'dataset_name': 'TUD Task Eye-Tracking',
                    'type': '动态视频',
                    'n_contents': 40,
                    'total_samples': len(tud_results),
                    'resolution': '1920×1080',
                    'sampling_rate': '250Hz',
                    'metric': 'CC (Correlation Coefficient)',
                    'nr_tas_performance': {
                        'mean_cc': float(tud_results['cc_tas_nr'].mean()),
                        'std_cc': float(tud_results['cc_tas_nr'].std()),
                        'min_cc': float(tud_results['cc_tas_nr'].min()),
                        'max_cc': float(tud_results['cc_tas_nr'].max()),
                    },
                    'fr_tas_performance': {
                        'mean_cc': float(tud_results['cc_freelook'].mean()),
                        'std_cc': float(tud_results['cc_freelook'].std()),
                        'min_cc': float(tud_results['cc_freelook'].min()),
                        'max_cc': float(tud_results['cc_freelook'].max()),
                    },
                    'effect_size': {
                        'cohens_d': float((tud_results['cc_tas_nr'].mean() - 
                                          tud_results['cc_freelook'].mean()) / 
                                         tud_results['cc_freelook'].std()),
                    }
                },
                'JIST01': {
                    'dataset_name': 'Transformed Saliency Dataset',
                    'type': '静态图像+变换',
                    'n_transformations': len(jist01_results),
                    'total_images': sum(d.get('n_images', 0) for d in jist01_results.values()),
                    'resolution': '1920×1080',
                    'observers_per_image': 10,
                    'transformation_types': list(jist01_results.keys()),
                }
            },
            'comparative_analysis': {
                'domain_shift': 'TUD(动态) vs JIST01(静态)',
                'recommendation': '使用JIST01验证变换鲁棒性',
                'notes': [
                    'TUD用于基础性能评估',
                    'JIST01用于变换鲁棒性验证',
                    '两个数据集的高度互补性'
                ]
            }
        }
        
        return summary


def main():
    """主测试函数"""
    import sys
    sys.path.insert(0, '/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments')
    
    from src.config import Config
    
    config = Config()
    analyzer = CrossDatasetAnalyzer(str(config.RESULTS_DIR))
    
    # 加载JIST01数据
    print("\n加载JIST01数据...")
    jist01_data = analyzer.load_jist01_data(
        '/iridisfs/scratch/jc15u24/Code/JIST01/data',
        transformations=['Reference', 'MotionBlur_1', 'Compression_1']
    )
    
    # 对比变换
    print("\n对比变换影响...")
    trans_comparison = analyzer.compare_transformations(jist01_data)
    print(trans_comparison)
    
    # 保存对比表
    trans_comparison.to_csv(
        f"{analyzer.output_dir}/jist01_transformation_comparison.csv",
        index=False
    )
    print(f"✓ 对比表已保存")
    
    # 生成汇总
    print("\n生成跨数据集汇总...")
    
    # 这里需要加载TUD结果
    tud_results_file = f"{analyzer.output_dir}/results_nr_v4_20260125_032248.csv"
    if os.path.exists(tud_results_file):
        tud_results = pd.read_csv(tud_results_file)
        
        summary = analyzer.generate_cross_dataset_summary(tud_results, jist01_data)
        
        with open(f"{analyzer.output_dir}/cross_dataset_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ 跨数据集汇总已保存")
        print(json.dumps(summary, indent=2)[:500] + "...")
    else:
        print(f"⚠ TUD结果文件不存在: {tud_results_file}")
        print(f"  请先运行TUD实验")
        print(f"\n✓ JIST01变换对比已完成")
        print(f"  文件: jist01_transformation_comparison.csv")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
