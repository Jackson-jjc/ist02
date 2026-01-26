# TUD 实验修复 - 快速开始指南

## 📋 修复内容概览

已修复 TUD 实验的**原始图像加载问题**：

| 问题 | 症状 | 修复 |
|-----|------|------|
| 原始图像加载失败 | "找不到原始图像" | 新增 `load_original_image()` 方法 |
| 文件格式问题 | 只支持 .jpg 格式 | 现在支持 .bmp、.jpg、.png |
| 错误处理不当 | 使用压缩图像作参考 | 明确的错误日志和降级处理 |

## 🚀 快速运行

### 方法 1：提交修复版本的 SLURM 任务

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
sbatch TUD_fixed_v4.slurm
```

**预期输出：**
```
Submitted batch job 12345678
```

查看任务状态：
```bash
squeue -lu jc15u24
```

### 方法 2：本地验证（无 GPU）

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
python3 test_fixes.py
```

**预期输出：**
```
✓ Found 40 unique contents
✓ Content 'arab_mountain' has 4 compression levels
✓ Loaded image successfully
✓ Loaded original image successfully
✓ Loaded saliency maps

ALL TESTS PASSED ✓
```

## 📂 修改的文件

### 1. src/data_loader.py
- **新增方法：** `load_original_image(content_name, color_space='ycrcb')`
- **功能：** 从 OriginalContent 文件夹加载原始参考图像
- **特性：** 支持多种格式（.bmp、.jpg、.png）、缓存机制、优雅的错误处理

### 2. improved_analysis_v4.py
- **修改位置：** `run_main_experiments_tud()` 方法中的原始图像加载部分
- **改进：** 使用新的 `load_original_image()` 方法，更清晰的逻辑流

### 3. test_fixes.py (新建)
- **用途：** 验证数据加载修复
- **测试内容：** 唯一内容、压缩级别、图像加载、原始图像加载、saliency maps

### 4. TUD_fixed_v4.slurm (新建)
- **用途：** 修复版本的 SLURM 提交脚本
- **包含内容：** 环境检查、数据验证、改进的实验运行

## 🔍 关键改进点

### 原来的问题代码
```python
try:
    original_files = list(config.ORIGINAL_CONTENT_DIR.glob(f"{test_content.rsplit('_', 1)[0]}*"))
    if original_files:
        img_original = self.data_loader.load_image(original_files[0].name)
    else:
        img_original = self.data_loader.load_image(test_filename)  # ❌ 用压缩图作参考！
except:
    img_original = self.data_loader.load_image(test_filename)  # ❌ 用压缩图作参考！
```

### 修复后的代码
```python
img_original = self.data_loader.load_original_image(test_content)  # ✓ 直接调用
if img_original is None:
    logger.warning(f"Could not load original image for {test_content}")
    img_original = self.data_loader.load_image(test_filename)  # 只在无法加载时退化
```

## 📊 验证结果

```
================================================================================
TESTING TUD DATA LOADER FIXES
================================================================================

[Test 1] Getting unique contents...
✓ Found 40 unique contents
  First 5: ['arab_mountain', 'bear_fish', 'bird_bushes', 'cat_fence', 'climber_mountains']

[Test 2] Getting compression levels for first content...
✓ Content 'arab_mountain' has 4 compression levels: [18, 38, 47, 64]

[Test 3] Loading test image...
✓ Loaded image 'arab_mountain_jpgq_(18).jpg': shape=(600, 600, 3), dtype=float32

[Test 4] Loading original image (NEW FIX)...
✓ Loaded original image for 'arab_mountain': shape=(600, 600, 3), dtype=float32

[Test 5] Loading saliency maps...
✓ Loaded saliency maps:
  - FreeLook: shape=(600, 600)
  - Scoring: shape=(600, 600)

================================================================================
ALL TESTS PASSED ✓
================================================================================
```

## ⚠️ 需要注意

1. **conda 环境：** 修复已在 `easygen-clean` 环境中测试通过
2. **数据完整性：** 所有 40 个内容的原始图像都应该在 OriginalContent 文件夹中
3. **磁盘空间：** 确保结果文件夹有足够空间存储实验结果

## 📝 后续步骤

修复后，TUD 实验应该能够：
- ✓ 正确加载所有 40 个内容的原始参考图像
- ✓ 为 Full-Reference (FR) 方法提供有效基线
- ✓ 提高 TAS 模型可靠性
- ✓ 减少因数据加载失败导致的跳过样本

## 💡 故障排除

如果实验仍然失败：

1. **检查数据完整性：**
   ```bash
   ls /iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/OriginalContent | wc -l
   # 应该显示 40
   ```

2. **检查文件格式：**
   ```bash
   file /iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/OriginalContent/arab_mountain.bmp
   # 应该显示 BMP image
   ```

3. **查看详细日志：**
   ```bash
   tail -f logs/tud_fixed_v4_*.log
   ```

## 📞 联系

如有问题，请检查：
- TUD_FIX_SUMMARY.md - 详细修复说明
- logs/ 文件夹 - 实验日志
- 结果文件 - results/ 文件夹
