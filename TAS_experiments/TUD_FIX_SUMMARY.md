# TUD 实验修复总结

## 问题识别

TUD 实验出错的主要原因是**原始图像加载逻辑不完善**：

### 1. 原始图像格式问题
- **OriginalContent** 文件夹中的文件是 `.bmp` 格式（如 `arab_mountain.bmp`）
- 代码试图用 `glob` 模糊匹配查找原始图像，导致经常找不到文件
- 当找不到原始图像时，代码会使用压缩图像作为参考，这对 FR 方法完全无效

### 2. 文件命名解析问题
- TestImages 中的文件格式为：`{content_name}_jpgq_({level}).jpg`
- 原有的 `extract_content_and_level` 方法已经正确，但原始图像加载没有利用这个信息

## 修复方案

### 修改 1：[data_loader.py](src/data_loader.py) - 添加 `load_original_image()` 方法

**新增方法的关键特性：**
```python
def load_original_image(self, content_name: str, color_space: str = 'ycrcb') -> Optional[np.ndarray]:
    """
    Load original reference image from OriginalContent folder.
    Supports both .bmp and .jpg formats.
    """
    # 尝试多种扩展名：.bmp, .jpg, .png
    for ext in ['.bmp', '.jpg', '.png']:
        filepath = self.config.ORIGINAL_CONTENT_DIR / (content_name + ext)
        if filepath.exists():
            # 加载并返回
```

**优点：**
- ✓ 支持多种文件格式（.bmp、.jpg、.png）
- ✓ 直接路径匹配，不依赖模糊的 glob 搜索
- ✓ 缓存机制避免重复加载
- ✓ 返回 Optional，优雅处理找不到的情况

### 修改 2：[improved_analysis_v4.py](improved_analysis_v4.py) - 更新原始图像加载逻辑

**原来的代码（有问题）：**
```python
try:
    original_files = list(config.ORIGINAL_CONTENT_DIR.glob(f"{test_content.rsplit('_', 1)[0]}*"))
    if original_files:
        img_original = self.data_loader.load_image(original_files[0].name)
    else:
        img_original = self.data_loader.load_image(test_filename)
except:
    img_original = self.data_loader.load_image(test_filename)
```

**修复后的代码：**
```python
img_original = self.data_loader.load_original_image(test_content)
if img_original is None:
    logger.warning(f"Could not load original image for {test_content}, using compressed as reference")
    img_original = self.data_loader.load_image(test_filename)
```

**改进点：**
- ✓ 使用新的专用方法加载原始图像
- ✓ 更清晰的错误处理和日志
- ✓ 直接传递 content_name，而不是试图解析文件名

## 验证结果

运行 `test_fixes.py` 验证所有功能：

```
✓ Found 40 unique contents
✓ Content 'arab_mountain' has 4 compression levels: [18, 38, 47, 64]
✓ Loaded image 'arab_mountain_jpgq_(18).jpg': shape=(600, 600, 3)
✓ Loaded original image for 'arab_mountain': shape=(600, 600, 3)
✓ Loaded saliency maps: FreeLook (600, 600), Scoring (600, 600)

ALL TESTS PASSED ✓
```

## 下一步：运行修复后的实验

使用以下命令提交修复后的 TUD 实验：

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
sbatch TAS_v4_improved.slurm  # 或创建新的 TUD_fixed.slurm
```

## 修改的文件

1. **src/data_loader.py** - 添加 `load_original_image()` 方法 (~40 行)
2. **improved_analysis_v4.py** - 简化原始图像加载逻辑 (~10 行)
3. **test_fixes.py** - 新建测试脚本，用于验证修复

## 预期改进

修复后，TUD 实验应该：
- ✓ 正确加载所有 40 个内容的原始参考图像
- ✓ 为 FR（Full-Reference）方法提供有效的基线
- ✓ 提高 TAS 模型的可靠性和准确性
- ✓ 减少因数据加载失败导致的跳过样本
