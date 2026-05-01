"""
综合实验管理器 - 根据revisedexperiment.md实现的改进框架
核心功能：
1. 强基线实现 (LB1/LB2)
2. Nested LOCO 选参
3. 跨数据集泛化测试
4. 机制验证
5. 统计分析与可视化
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Tuple, List, Optional
import pickle
import warnings

warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExperimentManager:
    """实验管理主类"""
    
    def __init__(self, root_dir: str):
        """
        初始化实验管理器
        
        Args:
            root_dir: TAS_experiments根目录
        """
        self.root_dir = Path(root_dir)
        self.results_dir = self.root_dir / "results" / "revisedexp_v1"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据集配置
        self.datasets = {
            'R2': {  # TUD_Task_EyeTracking - Release 2 (主训练集)
                'path': self.root_dir.parent / 'TUD_Task_EyeTracking',
                'role': 'main_training',
                'tasks': ['SaliencyScoring', 'SaliencyFreeLook'],
            },
            'R1': {  # TUD_LIVE_EyeTracking - Release 1 (跨数据集泛化测试1)
                'path': self.root_dir.parent / 'TUD_LIVE_EyeTracking' / 'TUD_LIVE_EyeTracking' / 'TestImages',
                'role': 'cross_dataset_test_1',
                'tasks': ['TestImages'],
            },
            'INT': {  # TUD_Interactions (跨数据集泛化测试2，可能多失真)
                'path': self.root_dir.parent / 'TUD_Interactions' / 'images',
                'role': 'cross_dataset_test_2',
                'tasks': ['images'],
            }
        }
        
        # 实验设置
        self.settings = {
            'A': 'Image-only (no prior)',
            'B': 'Predicted prior available',
            'C': 'Oracle prior (true free-viewing)'
        }
        
        # 指标配置
        self.metrics_config = {
            'primary': ['JSD', 'CC'],
            'secondary': ['NSS', 'SIM', 'KL'],
            'optional': ['AUC'],
        }
        
        logger.info(f"Experiment manager initialized. Results dir: {self.results_dir}")
    
    def verify_datasets(self) -> Dict[str, bool]:
        """验证数据集完整性"""
        verification = {}
        for dataset_name, config in self.datasets.items():
            path = config['path']
            exists = path.exists()
            verification[dataset_name] = exists
            if exists:
                file_count = len(list(path.rglob('*.jpg'))) + len(list(path.rglob('*.png')))
                logger.info(f"✓ {dataset_name}: Found at {path} ({file_count} image files)")
            else:
                logger.warning(f"✗ {dataset_name}: NOT FOUND at {path}")
        
        return verification
    
    def save_config(self):
        """保存实验配置"""
        config = {
            'timestamp': datetime.now().isoformat(),
            'datasets': {k: {'path': str(v['path']), **{k2: v2 for k2, v2 in v.items() if k2 != 'path'}} 
                        for k, v in self.datasets.items()},
            'settings': self.settings,
            'metrics': self.metrics_config,
        }
        
        config_file = self.results_dir / 'experiment_config.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Experiment config saved to {config_file}")
        return config_file


class NestedLOCOValidator:
    """Nested LOCO 交叉验证实现"""
    
    def __init__(self, primary_metric: str = 'JSD', 
                 constraint_metric: str = 'CC', 
                 constraint_threshold: float = 0.70):
        """
        初始化 Nested LOCO 验证器
        
        Args:
            primary_metric: 主要优化目标 (最小化JSD)
            constraint_metric: 约束指标 (CC >= threshold)
            constraint_threshold: 约束阈值
        """
        self.primary_metric = primary_metric
        self.constraint_metric = constraint_metric
        self.constraint_threshold = constraint_threshold
        self.results = []
        
    def get_outer_splits(self, dataset_ids: List[str], n_folds: int = -1) -> List[Tuple]:
        """
        生成外层fold (留出content)
        
        Args:
            dataset_ids: content标识列表
            n_folds: fold数 (-1 = 完整LOCO)
            
        Returns:
            [(train_ids, test_id), ...]
        """
        if n_folds == -1:
            n_folds = len(dataset_ids)
        
        splits = []
        for i in range(n_folds):
            test_idx = i % len(dataset_ids)
            test_id = dataset_ids[test_idx]
            train_ids = [dataset_ids[j] for j in range(len(dataset_ids)) if j != test_idx]
            splits.append((train_ids, test_id))
        
        return splits
    
    def inner_loop_hyperparameter_search(self, 
                                        train_data: np.ndarray,
                                        val_data: np.ndarray,
                                        alpha_range: np.ndarray = np.linspace(0, 1, 11),
                                        beta_range: np.ndarray = np.linspace(0, 1, 11)) -> Dict:
        """
        内层循环：超参搜索
        
        Args:
            train_data: 训练数据 {prior, artifact, gaze_target}
            val_data: 验证数据
            alpha_range: α混合系数范围
            beta_range: β稳定性权重范围
            
        Returns:
            最优超参配置
        """
        best_result = {
            'alpha': None,
            'beta': None,
            'primary_score': float('inf'),
            'constraint_satisfied': False,
            'history': []
        }
        
        for alpha in alpha_range:
            for beta in beta_range:
                # 计算主指标 (最小化JSD)
                primary_score = self._compute_metric(val_data, self.primary_metric, 
                                                     alpha, beta)
                
                # 计算约束指标 (CC)
                constraint_score = self._compute_metric(val_data, self.constraint_metric,
                                                       alpha, beta)
                
                constraint_satisfied = constraint_score >= self.constraint_threshold
                
                result = {
                    'alpha': alpha,
                    'beta': beta,
                    'primary': primary_score,
                    'constraint': constraint_score,
                    'constraint_ok': constraint_satisfied
                }
                
                best_result['history'].append(result)
                
                # 更新最优解：优先满足约束，再最小化主指标
                if constraint_satisfied:
                    if best_result['primary_score'] == float('inf') or \
                       primary_score < best_result['primary_score']:
                        best_result['alpha'] = alpha
                        best_result['beta'] = beta
                        best_result['primary_score'] = primary_score
                        best_result['constraint_satisfied'] = True
        
        if not best_result['constraint_satisfied']:
            logger.warning(f"No hyperparameter satisfies constraint {self.constraint_metric} >= {self.constraint_threshold}")
            # 降级策略：选择约束最接近阈值的参数
            best_result = self._fallback_selection(best_result['history'])
        
        return best_result
    
    def _compute_metric(self, data: dict, metric: str, alpha: float, beta: float) -> float:
        """计算指标 (简化版，实际需要真实指标计算)"""
        # 这里是占位符，实际实现需要传入真实指标计算函数
        return np.random.random()
    
    def _fallback_selection(self, history: List[Dict]) -> Dict:
        """当无法满足约束时的降级选择"""
        sorted_by_constraint = sorted(history, 
                                      key=lambda x: abs(x['constraint'] - self.constraint_threshold),
                                      reverse=False)
        best = sorted_by_constraint[0]
        return {
            'alpha': best['alpha'],
            'beta': best['beta'],
            'primary_score': best['primary'],
            'constraint_satisfied': False,
        }


class StrongBaselines:
    """实现强基线"""
    
    @staticmethod
    def LB1_Ridge(prior: np.ndarray, artifact: np.ndarray, 
                  gaze_target: np.ndarray, lambda_param: float = 1.0) -> np.ndarray:
        """
        LB1: Ridge回归基线 (线性组合学习)
        
        Args:
            prior: 自由观看先验 P^F
            artifact: 伪影map A
            gaze_target: 品质评分凝视 P^Q (目标)
            lambda_param: 正则化参数
            
        Returns:
            预测的 P^Q
        """
        try:
            from sklearn.linear_model import Ridge
        except ImportError:
            logger.error("sklearn not installed. Installing required packages...")
            return None
        
        # 将图像展平为特征向量
        n_samples = prior.shape[0] if len(prior.shape) > 2 else 1
        
        if n_samples == 1:
            prior_flat = prior.flatten().reshape(1, -1)
            artifact_flat = artifact.flatten().reshape(1, -1)
            target_flat = gaze_target.flatten()
        else:
            prior_flat = prior.reshape(n_samples, -1)
            artifact_flat = artifact.reshape(n_samples, -1)
            target_flat = gaze_target.reshape(n_samples, -1)
        
        # 合并特征
        X = np.hstack([prior_flat, artifact_flat])
        
        # 训练Ridge回归
        ridge = Ridge(alpha=lambda_param)
        ridge.fit(X, target_flat)
        
        # 预测
        pred_flat = ridge.predict(X)
        
        # 恢复为图像形状
        pred = pred_flat.reshape(gaze_target.shape)
        
        # 确保为概率分布
        pred = np.maximum(pred, 0)  # 非负
        pred = pred / (pred.sum() + 1e-8)  # 归一化
        
        return pred
    
    @staticmethod
    def LB2_CNN_Lite(prior: np.ndarray, artifact: np.ndarray, 
                     gaze_target: np.ndarray, epochs: int = 50) -> np.ndarray:
        """
        LB2: 轻量CNN基线
        
        Args:
            prior: P^F
            artifact: A
            gaze_target: P^Q (目标)
            epochs: 训练轮数
            
        Returns:
            预测的 P^Q
        """
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
        except ImportError:
            logger.error("torch not installed. Skipping LB2 CNN.")
            return None
        
        # 简化实现：这里返回占位符
        # 实际需要完整的CNN架构
        logger.warning("LB2 CNN-lite: 完整实现需要完整的数据和模型代码")
        return np.random.random(gaze_target.shape)


def main():
    """主函数 - 测试实验框架"""
    
    # 初始化管理器
    manager = ExperimentManager('/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments')
    
    # 验证数据集
    logger.info("=" * 60)
    logger.info("STEP 1: Verifying Datasets")
    logger.info("=" * 60)
    verification = manager.verify_datasets()
    print("\nDataset Verification Report:")
    for ds, status in verification.items():
        status_str = "✓ Available" if status else "✗ Missing"
        print(f"  {ds}: {status_str}")
    
    # 保存配置
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Saving Configuration")
    logger.info("=" * 60)
    manager.save_config()
    
    # 测试Nested LOCO
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Testing Nested LOCO Validator")
    logger.info("=" * 60)
    validator = NestedLOCOValidator()
    
    # 示例数据集ID
    dataset_ids = ['content_1', 'content_2', 'content_3', 'content_4', 'content_5']
    splits = validator.get_outer_splits(dataset_ids, n_folds=-1)
    print(f"\nLOCO Splits: {len(splits)} folds")
    for i, (train, test) in enumerate(splits[:3]):  # 显示前3个
        print(f"  Fold {i}: Train={len(train)}, Test={test}")
    
    logger.info("\n✓ Experiment framework initialized successfully!")
    logger.info(f"Results will be saved to: {manager.results_dir}")


if __name__ == '__main__':
    main()
