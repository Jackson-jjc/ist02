"""
JIST01 Dataset Loader
加载和处理Transformed Saliency Dataset (JIST01)
支持.mat格式的眼动数据和图像刺激
"""

import os
import numpy as np
import scipy.io as sio
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class JIST01Loader:
    """JIST01数据集加载器"""
    
    # JIST01中的变换类型
    TRANSFORMATION_TYPES = {
        'Reference': '原始图像',
        'MotionBlur_1': '运动模糊1级',
        'MotionBlur_2': '运动模糊2级',
        'Noise_1': '高斯噪声1级',
        'Noise_2': '高斯噪声2级',
        'Compression_1': 'JPEG压缩1级',
        'Compression_2': 'JPEG压缩2级',
        'ContrastChange_1': '对比度变化1级',
        'ContrastChange_2': '对比度变化2级',
        'Rotation_1': '旋转1级',
        'Rotation_2': '旋转2级',
        'Shearing_1': '剪切变换1级',
        'Shearing_2': '剪切变换2级',
        'Shearing_3': '剪切变换3级',
        'Cropping_1': '裁剪1级',
        'Cropping_2': '裁剪2级',
        'Mirroring': '镜像翻转',
        'Inversion': '反色变换',
        'LineDraw': '线条绘图',
        'Boundary': '边界变换',
    }
    
    def __init__(self, data_root: str, resolution: Tuple[int, int] = (1920, 1080)):
        """
        初始化JIST01加载器
        
        Args:
            data_root: 数据集根目录
            resolution: 图像分辨率 (width, height)
        """
        self.data_root = Path(data_root)
        self.resolution = resolution
        self.fixation_dir = self.data_root / 'fixation' / 'fixation'
        
        if not self.fixation_dir.exists():
            raise ValueError(f"Fixation目录不存在: {self.fixation_dir}")
        
        logger.info(f"初始化JIST01加载器: {self.data_root}")
        logger.info(f"分辨率: {resolution}")
        
    def list_transformations(self) -> List[str]:
        """列出所有可用的变换类型"""
        mat_files = list(self.fixation_dir.glob('*.mat'))
        transformations = sorted([f.stem for f in mat_files])
        logger.info(f"找到{len(transformations)}种变换类型")
        return transformations
    
    def load_fixation(self, transformation: str) -> np.ndarray:
        """
        加载特定变换的注视点数据
        
        Args:
            transformation: 变换类型名称 (e.g., 'Reference', 'MotionBlur_1')
            
        Returns:
            注视点数组 shape: (n_subjects, max_n_fixations, 2) 或 (n_images, ...)
        """
        mat_file = self.fixation_dir / f"{transformation}.mat"
        
        if not mat_file.exists():
            raise FileNotFoundError(f"注视点文件不存在: {mat_file}")
        
        try:
            data = sio.loadmat(str(mat_file), squeeze_me=True)
            
            # 移除MATLAB特殊字段
            fixation_data = {}
            for key, val in data.items():
                if not key.startswith('__'):
                    fixation_data[key] = val
            
            logger.info(f"成功加载 {transformation}: 字段={list(fixation_data.keys())}")
            return fixation_data
            
        except Exception as e:
            logger.error(f"加载 {transformation} 失败: {e}")
            raise
    
    def extract_gaze_maps(self, fixation_data: Dict, 
                         transformation: str) -> np.ndarray:
        """
        从预计算的注视点图中提取显著性数据
        
        JIST01数据格式: fixation_vec是长度100的对象数组，
        每个元素是一个(1080, 1920)的uint8注视点图
        
        Args:
            fixation_data: 从.mat加载的数据字典
            transformation: 变换类型
            
        Returns:
            显著性图数组 shape: (n_images, 1080, 1920)
        """
        if 'fixation_vec' not in fixation_data:
            logger.warning(f"无法找到 fixation_vec in {transformation}")
            return None
        
        fixation_vec = fixation_data['fixation_vec']
        
        # fixation_vec 是长度100的对象数组
        if not isinstance(fixation_vec, np.ndarray):
            logger.warning(f"{transformation}: fixation_vec 类型错误")
            return None
        
        # 提取所有图像的注视点图
        gaze_maps = []
        for i, fmap in enumerate(fixation_vec):
            if isinstance(fmap, np.ndarray):
                # 将uint8转换为float32 (0-255 -> 0-1)
                fmap_norm = fmap.astype(np.float32) / 255.0 if fmap.max() > 1 else fmap.astype(np.float32)
                gaze_maps.append(fmap_norm)
        
        if len(gaze_maps) == 0:
            logger.warning(f"{transformation}: 无法提取任何注视点图")
            return None
        
        return np.array(gaze_maps)
    
    def generate_gaze_map(self, fixation_points: np.ndarray,
                         sigma: float = 25.0) -> np.ndarray:
        """
        从注视点生成高斯平滑的显著性图
        
        Args:
            fixation_points: 注视点数组 shape: (n_fixations, 2)
            sigma: 高斯核标准差 (像素)
            
        Returns:
            显著性图 shape: (height, width)
        """
        from scipy.ndimage import gaussian_filter
        
        height, width = self.resolution[1], self.resolution[0]
        gaze_map = np.zeros((height, width), dtype=np.float32)
        
        if fixation_points is None or len(fixation_points) == 0:
            return gaze_map
        
        # 将注视点映射到图像坐标
        for x, y in fixation_points:
            x_int = int(np.clip(x, 0, width - 1))
            y_int = int(np.clip(y, 0, height - 1))
            gaze_map[y_int, x_int] += 1.0
        
        # 应用高斯平滑
        if np.sum(gaze_map) > 0:
            gaze_map = gaussian_filter(gaze_map, sigma=sigma)
            # 归一化到[0, 1]
            if gaze_map.max() > 0:
                gaze_map = gaze_map / gaze_map.max()
        
        return gaze_map
    
    def load_all_transformations(self, 
                                 subset: Optional[List[str]] = None) -> Dict:
        """
        批量加载多个变换类型的数据
        
        Args:
            subset: 要加载的变换类型列表 (None=全部)
            
        Returns:
            {transformation: {gaze_maps, n_images, ...}}
        """
        transformations = self.list_transformations()
        
        if subset is not None:
            transformations = [t for t in transformations if t in subset]
        
        results = {}
        
        for trans in transformations:
            try:
                logger.info(f"处理: {trans}")
                fixation_data = self.load_fixation(trans)
                gaze_maps = self.extract_gaze_maps(fixation_data, trans)
                
                if gaze_maps is not None and len(gaze_maps) > 0:
                    results[trans] = {
                        'gaze_maps': gaze_maps,
                        'n_images': len(gaze_maps),
                        'resolution': self.resolution,
                        'shape': gaze_maps.shape
                    }
                    logger.info(f"  ✓ {trans}: {len(gaze_maps)} 张显著性图, shape={gaze_maps.shape}")
                else:
                    logger.warning(f"  ✗ {trans}: 无法提取显著性图")
                    
            except Exception as e:
                logger.error(f"  ✗ {trans}: {e}")
                continue
        
        logger.info(f"成功加载 {len(results)}/{len(transformations)} 种变换")
        return results
    
    @staticmethod
    def analyze_fixation_statistics(fixation_points: np.ndarray) -> Dict:
        """
        计算注视点的统计信息
        
        Args:
            fixation_points: 注视点数组
            
        Returns:
            统计字典
        """
        if fixation_points is None or len(fixation_points) == 0:
            return {}
        
        return {
            'n_fixations': len(fixation_points),
            'x_mean': float(fixation_points[:, 0].mean()),
            'y_mean': float(fixation_points[:, 1].mean()),
            'x_std': float(fixation_points[:, 0].std()),
            'y_std': float(fixation_points[:, 1].std()),
            'x_min': float(fixation_points[:, 0].min()),
            'x_max': float(fixation_points[:, 0].max()),
            'y_min': float(fixation_points[:, 1].min()),
            'y_max': float(fixation_points[:, 1].max()),
        }


def test_jist01_loader():
    """测试JIST01加载器"""
    data_root = "/iridisfs/scratch/jc15u24/Code/JIST01/data"
    
    logging.basicConfig(level=logging.INFO)
    
    loader = JIST01Loader(data_root)
    
    # 列出变换
    transformations = loader.list_transformations()
    print(f"\n找到{len(transformations)}种变换:")
    for trans in transformations[:5]:
        print(f"  - {trans}")
    
    # 加载一个变换
    try:
        print(f"\n尝试加载 'Reference' 变换...")
        ref_data = loader.load_fixation('Reference')
        print(f"  字段: {list(ref_data.keys())}")
        
        # 显示数据形状
        for key, val in ref_data.items():
            if isinstance(val, np.ndarray):
                print(f"    {key}: shape={val.shape}, dtype={val.dtype}")
    except Exception as e:
        print(f"  错误: {e}")


if __name__ == '__main__':
    test_jist01_loader()
