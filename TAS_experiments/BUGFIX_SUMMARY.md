# TUD实验 Bug修复总结

## 问题诊断

### 报错信息
```
FileNotFoundError: [Errno 2] No such file or directory: 
'/iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/TestImages/dog_jpgq_(22).jpg'
```

### 根本原因
在 `src/data_loader.py` 中的 `get_compression_levels()` 方法使用 `filename.startswith(content_name)` 进行内容匹配，导致前缀重叠问题：

- 当查找内容 `'dog'` 的压缩级别时
- 代码也会匹配 `'dog_walker'` 的文件（因为 `'dog_walker'.startswith('dog')` 为真）
- 导致将 `dog_walker` 的级别 (22, 27, 77, 87) 错误地归属于 `dog`
- 当代码尝试加载 `dog_jpgq_(22).jpg` 时失败（该文件不存在）

## 修复方案

### 修改位置
文件: `src/data_loader.py`，第44-51行

### 修改前（有bug）
```python
def get_compression_levels(self, content_name: str) -> List[int]:
    """Get all compression levels for a given content"""
    levels = []
    for filename in os.listdir(self.config.TEST_IMAGES_DIR):
        if filename.startswith(content_name) and filename.endswith('.jpg'):
            _, level = self.extract_content_and_level(filename)
            levels.append(level)
    return sorted(list(set(levels)))
```

### 修改后（修复）
```python
def get_compression_levels(self, content_name: str) -> List[int]:
    """Get all compression levels for a given content"""
    levels = []
    for filename in os.listdir(self.config.TEST_IMAGES_DIR):
        if filename.endswith('.jpg'):
            extracted_content, level = self.extract_content_and_level(filename)
            if extracted_content == content_name:
                levels.append(level)
    return sorted(list(set(levels)))
```

### 改动说明
- 改用精确的内容名称匹配 (`extracted_content == content_name`)，而不是前缀匹配
- 确保只有完全匹配的内容才会被包含

## 数据验证结果

✓ 所有40个内容都有对应的4个图像  
✓ 每个图像都有对应的SaliencyFreeLook热图  
✓ 每个图像都有对应的SaliencyScoring热图  
✓ 总计160个图像，160个FreeLook热图，160个Scoring热图  

## 内容级别验证

修复前后的对比：

| 内容 | 修复前 | 修复后 | 正确性 |
|------|-------|-------|------|
| dog | [22, 27, 29, 33, 67, 77, 87, 90] | [29, 33, 67, 90] | ✓ |
| dog_walker | [22, 27, 77, 87] | [22, 27, 77, 87] | ✓ |

## 方法合理性验证

### 实验设计评估
1. **RQ1 - 任务转移分析**：分析自由看和评分任务之间的视觉注意力转移
   - 方法：比较两个任务下的saliency分布差异（CC、JSD等指标）
   - 合理性：✓ 正确

2. **RQ2 - 注视点预测**：使用自由看的saliency预测评分任务的结果
   - 方法：使用log-linear和mixture模型进行预测
   - 合理性：✓ 正确

3. **RQ3 - 实用应用**：探索压缩对saliency预测的影响
   - 方法：在不同的压缩级别上验证模型性能
   - 合理性：✓ 正确

## 提交清单

- [x] Bug修复
- [x] 路径验证
- [x] 数据完整性验证
- [x] 代码逻辑验证
- [x] 重新提交任务
