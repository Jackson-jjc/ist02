"""
JIST01 数据结构探索脚本
"""
import scipy.io as sio
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载Reference数据
ref_file = "/iridisfs/scratch/jc15u24/Code/JIST01/data/fixation/fixation/Reference.mat"

try:
    data = sio.loadmat(ref_file, squeeze_me=True)
    
    print("=" * 70)
    print("JIST01 数据结构分析")
    print("=" * 70)
    
    print("\n顶层字段:")
    for key, val in data.items():
        if not key.startswith('__'):
            if isinstance(val, np.ndarray):
                print(f"  {key}: shape={val.shape}, dtype={val.dtype}")
            else:
                print(f"  {key}: type={type(val).__name__}")
    
    # 深入检查fixation_vec
    print("\n\n深入检查 'fixation_vec' (样本):")
    fixation_vec = data['fixation_vec']
    print(f"  长度: {len(fixation_vec)}")
    print(f"  第一个元素的类型: {type(fixation_vec[0])}")
    
    if isinstance(fixation_vec[0], np.ndarray):
        print(f"  第一个元素的shape: {fixation_vec[0].shape}")
        print(f"  第一个元素的前5行:\n{fixation_vec[0][:5]}")
    elif isinstance(fixation_vec[0], dict):
        print(f"  第一个元素的key: {fixation_vec[0].keys()}")
    
    # 查看更多元素
    print(f"\n  前3个元素的形状/类型:")
    for i in range(min(3, len(fixation_vec))):
        elem = fixation_vec[i]
        if isinstance(elem, np.ndarray):
            print(f"    [{i}]: shape={elem.shape}, dtype={elem.dtype}")
        else:
            print(f"    [{i}]: type={type(elem).__name__}")
    
    # 尝试找出数据的含义
    print("\n\n数据分析:")
    first_elem = fixation_vec[0]
    if isinstance(first_elem, np.ndarray):
        print(f"  假设: 每个元素是一个(n_samples, n_features)的数组")
        print(f"  shape示例: {first_elem.shape}")
        if first_elem.ndim == 2:
            print(f"  可能是: ({first_elem.shape[0]} 个图像, {first_elem.shape[1]} 个特征)")
            if first_elem.shape[1] >= 2:
                print(f"  前2个特征的统计:")
                print(f"    Feature 0: min={first_elem[:, 0].min():.1f}, max={first_elem[:, 0].max():.1f}, mean={first_elem[:, 0].mean():.1f}")
                print(f"    Feature 1: min={first_elem[:, 1].min():.1f}, max={first_elem[:, 1].max():.1f}, mean={first_elem[:, 1].mean():.1f}")
    
except Exception as e:
    logger.error(f"加载失败: {e}")
    import traceback
    traceback.print_exc()
