"""
统一数据加载器 - 跨数据集一致的预处理
确保 R2, R1, INT 的可比性
"""

import os
import numpy as np
import cv2
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import json
import logging
from dataclasses import dataclass, field
from scipy import stats
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingConfig:
    """预处理配置 - 统一跨数据集"""
    
    # 空间配置
    target_size: int = 512  # 短边缩放目标
    maintain_aspect_ratio: bool = True
    
    # FDM (Fixation Density Map) 生成
    gaussian_sigma_pixels: float = 32.0  # 像素级高斯核
    gaussian_sigma_degrees: Optional[float] = None  # 视觉角级 (优先)
    fov_distance_mm: float = 500  # 观看距离 (毫米)
    screen_ppi: float = 96  # 屏幕DPI
    
    # 归一化
    normalize_fdm: bool = True  # FDM 归一化为概率分布
    preserve_unnormalized: bool = True  # 保留未归一化版本
    
    # 失真级别定义
    jpeg_quality_levels: List[int] = field(default_factory=lambda: [10, 15, 20, 30, 40, 50, 60, 70, 80, 90])
    distortion_types: List[str] = field(default_factory=lambda: ['jpeg', 'blur', 'noise', 'awgn'])


class UnifiedDataLoader:
    """统一数据加载器"""
    
    def __init__(self, config: PreprocessingConfig = None):
        """初始化加载器"""
        self.config = config or PreprocessingConfig()
        self.metadata = {}
        
    def load_dataset(self, dataset_path: Path, dataset_name: str,
                    task_type: str = 'quality_scoring') -> Dict:
        """
        统一加载数据集
        
        Args:
            dataset_path: 数据集根路径
            dataset_name: 数据集名称 (R2/R1/INT)
            task_type: 任务类型 (quality_scoring / free_looking)
            
        Returns:
            {
                'images': Dict[content_id, np.ndarray],
                'saliency_maps': Dict[content_id, np.ndarray],
                'metadata': Dict,
                'distortion_info': Dict,
            }
        """
        logger.info(f"Loading dataset {dataset_name} from {dataset_path}")
        
        result = {
            'images': {},
            'saliency_maps': {},
            'metadata': {
                'dataset': dataset_name,
                'task': task_type,
                'preprocessing_config': self.config.__dict__,
                'n_contents': 0,
                'n_distortion_levels': 0,
            },
            'distortion_info': {},
        }
        
        # 寻找图像文件
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.BMP', '*.JPG', '*.JPEG', '*.PNG']
        image_files = []
        for ext in image_extensions:
            image_files.extend(dataset_path.rglob(ext))
        
        logger.info(f"Found {len(image_files)} image files")
        
        # 解析图像和失真信息
        for img_path in sorted(image_files):  # 加载所有图像 (已移除100的限制)
            try:
                # 提取content ID和失真参数
                content_id, distortion_info = self._parse_filename(img_path.name)
                
                # 加载和预处理图像
                img = cv2.imread(str(img_path))
                if img is None:
                    logger.warning(f"Failed to load {img_path}")
                    continue
                
                # 转换到RGB
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # 标准化预处理
                img_processed = self._preprocess_image(img)
                
                # 组织存储
                key = f"{content_id}_{distortion_info['level']}"
                result['images'][key] = img_processed
                result['distortion_info'][key] = distortion_info
                
            except Exception as e:
                logger.debug(f"Error processing {img_path}: {e}")
                continue
        
        result['metadata']['n_contents'] = len(set(k.split('_')[0] 
                                                   for k in result['images'].keys()))
        
        logger.info(f"✓ Loaded {len(result['images'])} images, "
                   f"{result['metadata']['n_contents']} unique contents")
        
        return result
    
    def _parse_filename(self, filename: str) -> Tuple[str, Dict]:
        """
        解析文件名以提取content ID和失真信息
        
        格式示例:
        - street_greeting_jpgq_(15)_COMBINED.jpg -> content_id='street_greeting', level=15
        - image_blur_5.png -> content_id='image', type='blur', level=5
        """
        distortion_info = {
            'type': 'jpeg',  # 默认
            'level': 50,      # 默认
            'raw_filename': filename,
        }
        
        # JPEG质量格式: xxx_jpgq_(Q).jpg
        if 'jpgq_' in filename:
            parts = filename.split('_')
            try:
                quality_str = filename.split('jpgq_(')[1].split(')')[0]
                distortion_info['level'] = int(quality_str)
                distortion_info['type'] = 'jpeg'
            except:
                pass
        
        # 提取content ID (移除失真后缀)
        base = filename.split('_jpgq_')[0] if '_jpgq_' in filename else filename
        base = base.replace('_COMBINED', '').replace('.jpg', '').replace('.png', '')
        content_id = base
        
        return content_id, distortion_info
    
    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        标准化图像预处理
        
        Args:
            img: 输入图像 (H, W, 3)
            
        Returns:
            预处理后的图像 (H', W', 3)
        """
        h, w = img.shape[:2]
        
        # 计算缩放因子
        if self.config.maintain_aspect_ratio:
            scale_factor = self.config.target_size / min(h, w)
            new_h = int(h * scale_factor)
            new_w = int(w * scale_factor)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            img = cv2.resize(img, (self.config.target_size, self.config.target_size),
                           interpolation=cv2.INTER_LANCZOS4)
        
        # 记录缩放因子
        self.last_scale_factor = scale_factor if self.config.maintain_aspect_ratio else 1.0
        
        return img.astype(np.float32) / 255.0
    
    def load_saliency_maps(self, dataset_path: Path, 
                          dataset_name: str) -> Dict[str, np.ndarray]:
        """
        加载显著性图/凝视分布图
        
        Args:
            dataset_path: 显著性图存储路径
            dataset_name: 数据集名称
            
        Returns:
            {content_key: saliency_map_array}
        """
        logger.info(f"Loading saliency maps for {dataset_name}")
        
        saliency_maps = {}
        
        # 查找显著性图文件
        sal_dirs = list(dataset_path.glob('*ality*')) + list(dataset_path.glob('*alience*'))
        if not sal_dirs:
            logger.warning(f"No saliency map directory found in {dataset_path}")
            return saliency_maps
        
        sal_dir = sal_dirs[0]
        logger.info(f"Using saliency directory: {sal_dir}")
        
        for sal_file in sal_dir.glob('*.jpg') | sal_dir.glob('*.png') | sal_dir.glob('*.npy'):
            try:
                if sal_file.suffix == '.npy':
                    sal_map = np.load(sal_file)
                else:
                    sal_map = cv2.imread(str(sal_file), cv2.IMREAD_GRAYSCALE)
                    if sal_map is None:
                        continue
                
                # 标准化预处理
                sal_map = self._preprocess_saliency_map(sal_map)
                
                # 提取content ID
                content_id, _ = self._parse_filename(sal_file.name)
                saliency_maps[content_id] = sal_map
                
            except Exception as e:
                logger.debug(f"Error loading saliency map {sal_file}: {e}")
                continue
        
        logger.info(f"✓ Loaded {len(saliency_maps)} saliency maps")
        return saliency_maps
    
    def _preprocess_saliency_map(self, sal_map: np.ndarray) -> np.ndarray:
        """预处理显著性图"""
        # 确保为浮点型
        if sal_map.dtype != np.float32:
            sal_map = sal_map.astype(np.float32) / 255.0
        
        # 如果指定了目标大小，进行缩放
        if len(sal_map.shape) == 2:  # 灰度图
            h, w = sal_map.shape
            scale = self.config.target_size / min(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            sal_map = cv2.resize(sal_map, (new_w, new_h), 
                               interpolation=cv2.INTER_LINEAR)
        
        # 归一化为概率分布
        if self.config.normalize_fdm:
            sal_map_norm = sal_map / (sal_map.sum() + 1e-8)
        else:
            sal_map_norm = sal_map
        
        return sal_map_norm
    
    def generate_unified_dataset_manifest(self, 
                                        datasets: Dict[str, Dict]) -> pd.DataFrame:
        """
        生成统一的数据集清单
        
        Args:
            datasets: 加载的所有数据集
            
        Returns:
            pandas DataFrame 包含所有图像的元数据
        """
        rows = []
        for dataset_name, dataset in datasets.items():
            for img_key, img_array in dataset['images'].items():
                distortion_info = dataset['distortion_info'].get(img_key, {})
                rows.append({
                    'dataset': dataset_name,
                    'content_id': img_key.split('_')[0],
                    'distortion_level': distortion_info.get('level', -1),
                    'distortion_type': distortion_info.get('type', 'unknown'),
                    'image_shape': img_array.shape,
                    'image_key': img_key,
                })
        
        manifest = pd.DataFrame(rows)
        logger.info(f"\n✓ Dataset Manifest created with {len(manifest)} images")
        logger.info(manifest.groupby(['dataset', 'distortion_type']).size())
        
        return manifest


def verify_preprocessing_consistency(datasets: Dict[str, Dict]) -> Dict:
    """
    验证跨数据集的预处理一致性
    
    Returns:
        一致性报告
    """
    report = {
        'image_shapes': {},
        'distortion_levels': {},
        'saliency_shapes': {},
    }
    
    for ds_name, ds_data in datasets.items():
        shapes = [img.shape for img in ds_data['images'].values()]
        report['image_shapes'][ds_name] = {
            'unique_shapes': list(set(shapes)),
            'count': len(shapes),
        }
        
        levels = [info.get('level') for info in ds_data['distortion_info'].values()]
        report['distortion_levels'][ds_name] = {
            'range': (min(levels), max(levels)) if levels else None,
            'unique_levels': sorted(set(levels)) if levels else [],
        }
    
    logger.info("\n=== Preprocessing Consistency Report ===")
    logger.info(json.dumps(report, indent=2, default=str))
    
    return report


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    config = PreprocessingConfig()
    loader = UnifiedDataLoader(config)
    
    # 加载数据集
    root = Path('/iridisfs/scratch/jc15u24/Code/IST02')
    
    datasets = {}
    for ds_name, ds_path in [
        ('R2', root / 'TUD_Task_EyeTracking'),
        ('R1', root / 'TUD_LIVE_EyeTracking' / 'TUD_LIVE_EyeTracking'),
        ('INT', root / 'TUD_Interactions'),
    ]:
        if ds_path.exists():
            datasets[ds_name] = loader.load_dataset(ds_path, ds_name)
        else:
            logger.warning(f"Dataset path not found: {ds_path}")
    
    # 验证一致性
    if datasets:
        verify_preprocessing_consistency(datasets)
