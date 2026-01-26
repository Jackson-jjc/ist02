# TAS 实验框架 - 完整模块依赖清单

## 1. 核心库（必需）

### 标准库（已内置，无需安装）
- `os` - 操作系统接口
- `sys` - 系统参数和函数
- `re` - 正则表达式
- `pathlib.Path` - 路径处理
- `typing` - 类型注解
- `logging` - 日志记录
- `datetime` - 日期和时间

### 第三方库（需要安装）

#### 1. **numpy** >= 1.21.0
   - 数值计算和数组操作
   - 用途：矩阵运算、图像处理
   - 在模块中：data_loader, artifact_maps, tas_model, metrics, 所有实验模块

#### 2. **scipy** >= 1.7.0
   - 科学计算库
   - 具体子模块：
     - `scipy.optimize.differential_evolution` - 参数优化
     - `scipy.optimize.minimize` - 优化算法
     - `scipy.spatial.distance.jensenshannon` - Jensen-Shannon散度计算
     - `scipy.stats.pearsonr` - Pearson相关系数
     - `scipy.stats.spearmanr` - Spearman相关系数
     - `scipy.stats.sem` - 标准误差
     - `scipy.stats.wilcoxon` - Wilcoxon配对检验
   - 用途：统计分析、参数优化

#### 3. **pandas** >= 1.3.0
   - 数据处理和分析
   - 用途：结果统计、CSV读写、数据聚合
   - 在模块中：exp_rq1, exp_rq2, exp_rq3, visualizer

#### 4. **opencv-python** >= 4.5.0
   - 计算机视觉库
   - 用途：
     - 颜色空间转换（RGB ↔ YCrCb ↔ Gray）
     - 图像滤波和平滑（Gaussian blur）
     - 图像金字塔（pyrDown, pyrUp）
     - 边缘检测（Canny）
     - 形态操作（dilate）
   - 在模块中：data_loader, artifact_maps

#### 5. **Pillow (PIL)** >= 8.3.0
   - 图像处理库
   - 用途：加载和保存图像文件
   - 在模块中：data_loader

#### 6. **matplotlib** >= 3.4.0
   - 数据可视化库
   - 用途：生成图表和数据可视化
   - 在模块中：exp_rq1, visualizer

---

## 2. 最小依赖集（仅处理数据、无可视化）

如果只需运行实验逻辑而不生成图表：

```
numpy>=1.21.0
scipy>=1.7.0
pandas>=1.3.0
opencv-python>=4.5.0
Pillow>=8.3.0
```

（可以不安装 matplotlib）

---

## 3. 完整依赖集（含可视化）

```
numpy>=1.21.0
scipy>=1.7.0
pandas>=1.3.0
opencv-python>=4.5.0
Pillow>=8.3.0
matplotlib>=3.4.0
```

---

## 4. 安装命令

### 方式1：使用 pip（推荐）

```bash
# 一次性安装所有依赖
pip install -r requirements.txt

# 或单独安装
pip install numpy scipy pandas opencv-python Pillow matplotlib
```

### 方式2：使用 conda（如果已安装Anaconda/Miniconda）

```bash
# 创建新环境
conda create -n tas-env python=3.8

# 激活环境
conda activate tas-env

# 安装依赖
conda install numpy scipy pandas opencv pillow matplotlib

# 或从requirements.txt
pip install -r requirements.txt
```

### 方式3：在SLURM中自动安装

修改 `submit_experiments.slurm`：
```bash
pip install --user -r requirements.txt
```

---

## 5. 模块依赖关系图

```
run_all_experiments.py (主脚本)
├── config.py [需要: Path]
├── data_loader.py [需要: numpy, cv2, PIL, re, Path]
├── artifact_maps.py [需要: numpy, cv2]
├── tas_model.py [需要: numpy, scipy.optimize]
├── metrics.py [需要: numpy, scipy.stats, scipy.spatial]
├── exp_rq1_task_shift.py [需要: numpy, pandas, scipy.stats, matplotlib]
│   └── 依赖: data_loader, artifact_maps, metrics
├── exp_rq2_prediction.py [需要: numpy, pandas, scipy.stats]
│   └── 依赖: data_loader, artifact_maps, tas_model, metrics
├── exp_rq3_practical.py [需要: numpy, pandas, scipy.stats]
│   └── 依赖: data_loader, artifact_maps, tas_model, metrics
└── visualizer.py [需要: numpy, pandas, matplotlib]
```

---

## 6. Python 版本要求

- **推荐**: Python 3.7+
- **最低**: Python 3.6（某些scipy版本可能不支持3.5）
- **最佳**: Python 3.8 或 3.9

检查 Python 版本：
```bash
python --version
python3 --version
```

---

## 7. 验证安装

运行验证脚本检查依赖：

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
python validate_setup.py
```

如果所有检查通过，输出：
```
✓ ALL CHECKS PASSED - Ready to run experiments
```

---

## 8. 常见安装问题

### 问题1: opencv-python 与系统OpenCV冲突
**解决方案**：使用 `opencv-python-headless`（无GUI）
```bash
pip install opencv-python-headless
```

### 问题2: Pillow 版本不兼容
**解决方案**：升级到最新
```bash
pip install --upgrade Pillow
```

### 问题3: scipy 版本过旧
**解决方案**：
```bash
pip install --upgrade scipy
```

### 问题4: 权限不足
**解决方案**：使用 `--user` 标志
```bash
pip install --user -r requirements.txt
```

---

## 9. 模块详细用途表

| 模块 | 版本 | 主要用途 | 关键函数/类 |
|------|------|---------|-----------|
| numpy | 1.21+ | 数值计算 | np.array, np.sum, np.mean, np.std |
| scipy | 1.7+ | 优化、统计 | differential_evolution, pearsonr, jensenshannon |
| pandas | 1.3+ | 数据处理 | DataFrame, pd.read_csv, to_csv |
| opencv | 4.5+ | 图像处理 | cv2.cvtColor, cv2.GaussianBlur, cv2.resize |
| Pillow | 8.3+ | 图像I/O | Image.open() |
| matplotlib | 3.4+ | 可视化 | plt.plot, plt.scatter, plt.savefig |

---

## 10. 环境变量设置（可选）

若需加快导入速度，可设置：
```bash
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

---

## 总结

**最小配置**（仅处理数据）：
```bash
pip install numpy scipy pandas opencv-python Pillow
```

**完整配置**（含可视化）：
```bash
pip install numpy scipy pandas opencv-python Pillow matplotlib
```

**建议的安装方式**：
```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
pip install -r requirements.txt
python validate_setup.py
```
