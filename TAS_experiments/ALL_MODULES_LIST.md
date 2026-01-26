# 🎯 TAS 实验项目 - 所有模块清单（用户查询版）

---

## ✅ 需要安装的第三方模块

### 📦 pip 安装命令（推荐）

#### **一次性全部安装**
```bash
pip install -r requirements.txt
```

#### **或手动逐个安装**
```bash
pip install numpy>=1.21.0
pip install scipy>=1.7.0
pip install pandas>=1.3.0
pip install opencv-python>=4.5.0
pip install Pillow>=8.3.0
pip install matplotlib>=3.4.0
```

---

## 📋 所有模块详细清单

### 🔴 必需模块（6个）

| # | 模块名 | 最低版本 | 用途 | 备注 |
|---|--------|---------|------|------|
| 1️⃣ | **numpy** | 1.21.0 | 数值计算、数组操作 | 每个文件都用到 |
| 2️⃣ | **scipy** | 1.7.0 | 优化算法、统计检验 | 参数学习、假设检验 |
| 3️⃣ | **pandas** | 1.3.0 | 数据处理、表格操作 | 结果统计聚合 |
| 4️⃣ | **opencv-python** | 4.5.0 | 图像处理 | 颜色转换、滤波、金字塔 |
| 5️⃣ | **Pillow** | 8.3.0 | 图像加载 | 读写JPG文件 |
| 6️⃣ | **matplotlib** | 3.4.0 | 可视化绘图 | 生成图表 |

### 🟢 标准库（已内置，无需安装）

```
os              # 文件系统操作
sys             # 系统参数
re              # 正则表达式
pathlib.Path    # 路径处理
typing          # 类型注解
logging         # 日志记录
datetime        # 日期时间
```

---

## 📊 安装验证

### 验证是否安装成功
```bash
python -c "import numpy, scipy, pandas, cv2, PIL, matplotlib; print('✅ All modules OK')"
```

### 检查版本
```bash
python -c "import numpy; print(f'numpy: {numpy.__version__}')"
python -c "import scipy; print(f'scipy: {scipy.__version__}')"
python -c "import pandas; print(f'pandas: {pandas.__version__}')"
python -c "import cv2; print(f'opencv: {cv2.__version__}')"
python -c "from PIL import Image; print('PIL: OK')"
python -c "import matplotlib; print(f'matplotlib: {matplotlib.__version__}')"
```

---

## 🎯 各模块在项目中的使用

### 1. **numpy** 核心使用位置
```
✓ data_loader.py        - 图像数组操作
✓ artifact_maps.py      - 伪影计算矩阵运算
✓ tas_model.py          - 参数计算、概率计算
✓ metrics.py            - 指标计算（CC、JSD等）
✓ exp_rq*.py            - 数据聚合
✓ visualizer.py         - 数据整形
```

### 2. **scipy** 核心使用位置
```
✓ tas_model.py
  └─ scipy.optimize.differential_evolution  # 参数优化
  └─ scipy.optimize.minimize                # 损失函数最小化

✓ metrics.py
  └─ scipy.spatial.distance.jensenshannon   # JS散度
  └─ scipy.stats.pearsonr                   # Pearson相关
  └─ scipy.stats.spearmanr                  # Spearman相关
  └─ scipy.stats.sem                        # 标准误差
  └─ scipy.stats.wilcoxon                   # 配对检验
```

### 3. **pandas** 核心使用位置
```
✓ exp_rq1_task_shift.py - 结果DataFrame、CSV保存
✓ exp_rq2_prediction.py - 交叉验证结果聚合
✓ exp_rq3_practical.py  - 指标聚合
✓ visualizer.py         - 结果表生成、统计汇总
```

### 4. **opencv-python (cv2)** 核心使用位置
```
✓ data_loader.py
  └─ cv2.cvtColor()          # 颜色空间转换 (RGB ↔ YCrCb ↔ Gray)
  └─ cv2.resize()            # 图像大小调整
  └─ cv2.GaussianBlur()      # 高斯滤波

✓ artifact_maps.py
  └─ cv2.pyrDown()           # 高斯金字塔下采样
  └─ cv2.pyrUp()             # 高斯金字塔上采样
  └─ cv2.GaussianBlur()      # 图像平滑
  └─ cv2.Canny()             # 边缘检测
  └─ cv2.Laplacian()         # 拉普拉斯滤波
  └─ cv2.dilate()            # 形态膨胀
  └─ cv2.getStructuringElement()  # 结构元素
```

### 5. **Pillow (PIL)** 核心使用位置
```
✓ data_loader.py
  └─ Image.open()            # 加载JPG文件
```

### 6. **matplotlib** 核心使用位置
```
✓ visualizer.py
  └─ plt.errorbar()          # 带误差棒的曲线
  └─ plt.scatter()           # 散点图
  └─ plt.savefig()           # 保存图表
  └─ plt.plot()              # 折线图
```

---

## 🔧 安装故障排除

### 问题1: opencv-python 导入失败
**解决方案1**：使用 headless 版本
```bash
pip uninstall opencv-python
pip install opencv-python-headless
```

**解决方案2**：检查依赖
```bash
pip install --upgrade opencv-python
```

### 问题2: scipy 版本太旧
**解决**：升级
```bash
pip install --upgrade scipy
```

### 问题3: Pillow 兼容性问题
**解决**：
```bash
pip install --upgrade Pillow
```

### 问题4: 权限错误
**解决**：
```bash
pip install --user -r requirements.txt
```

### 问题5: 在SLURM中安装失败
**解决**：在SLURM脚本中添加
```bash
module load python  # 如果需要
pip install --user -r requirements.txt
```

---

## 🚀 快速安装脚本

### 完整自动化安装（保存为 install.sh）
```bash
#!/bin/bash

echo "🔧 安装TAS实验项目依赖..."

# 检查Python版本
python --version

# 升级pip
pip install --upgrade pip

# 安装依赖
echo "📦 安装依赖包..."
pip install -r requirements.txt

# 验证安装
echo "✅ 验证安装..."
python validate_setup.py

echo "✨ 安装完成！"
```

**使用方法**：
```bash
bash install.sh
```

---

## 📦 requirements.txt 内容

```
numpy>=1.21.0
scipy>=1.7.0
pandas>=1.3.0
opencv-python>=4.5.0
Pillow>=8.3.0
matplotlib>=3.4.0
```

---

## ✨ 最小依赖配置

### 如果只要运行实验（不需要可视化）
```bash
pip install numpy scipy pandas opencv-python Pillow
# 不安装 matplotlib
```

### 如果在资源受限的环境
```bash
pip install numpy scipy pandas opencv-python-headless Pillow
# 使用 headless opencv，不需要 GUI
```

---

## 🔍 模块依赖图

```
numpy
  ↑
  ├─ scipy (依赖numpy)
  ├─ pandas (依赖numpy)
  └─ opencv (独立)
     
matplotlib
  └─ numpy (依赖)
  └─ pandas (依赖)

Pillow (独立)

项目模块依赖树：
config.py
  ├─ numpy, pathlib
data_loader.py
  ├─ numpy, cv2, PIL, pathlib, re, typing
artifact_maps.py
  ├─ numpy, cv2, typing, logging
tas_model.py
  ├─ numpy, scipy, typing, logging
metrics.py
  ├─ numpy, scipy, typing, logging
exp_rq*.py
  ├─ numpy, pandas, scipy, typing, logging, matplotlib
visualizer.py
  ├─ numpy, pandas, matplotlib, pathlib, typing, logging
run_all_experiments.py
  ├─ 所有上述模块
```

---

## 📊 依赖安装大小估计

| 模块 | 大小 | 安装时间 |
|------|------|--------|
| numpy | ~25 MB | 1-2 分钟 |
| scipy | ~30 MB | 2-3 分钟 |
| pandas | ~20 MB | 1-2 分钟 |
| opencv-python | ~80 MB | 3-5 分钟 |
| Pillow | ~5 MB | <1 分钟 |
| matplotlib | ~40 MB | 2-3 分钟 |
| **总计** | **~200 MB** | **10-15 分钟** |

---

## ⚡ 快速检查清单

```bash
# 1. 检查Python版本
python --version          # 应该是 3.7+

# 2. 验证pip
pip --version

# 3. 安装依赖
pip install -r requirements.txt

# 4. 快速验证
python -c "import numpy, scipy, pandas, cv2, PIL; print('✅ OK')"

# 5. 运行验证脚本
python validate_setup.py

# 6. 查看结果
# 应该看到：✓ ALL CHECKS PASSED
```

---

## 🎓 详细依赖列表

### numpy >= 1.21.0
- **功能**：数值计算核心
- **使用**：数组运算、数学函数、矩阵操作
- **关键方法**：np.array, np.sum, np.mean, np.std, np.log, np.power

### scipy >= 1.7.0
- **子模块 1**：scipy.optimize
  - `differential_evolution` - 全局优化算法
  - `minimize` - 局部优化
- **子模块 2**：scipy.stats
  - `pearsonr`, `spearmanr` - 相关系数
  - `sem` - 标准误差
  - `wilcoxon` - 配对检验
- **子模块 3**：scipy.spatial.distance
  - `jensenshannon` - JS散度计算

### pandas >= 1.3.0
- **功能**：表格数据处理
- **关键类**：DataFrame, Series
- **关键方法**：to_csv, read_csv, groupby, agg, describe

### opencv-python >= 4.5.0
- **模块别名**：cv2
- **功能**：图像处理
- **关键功能**：
  - 颜色转换：cvtColor
  - 图像滤波：GaussianBlur, Laplacian
  - 图像金字塔：pyrDown, pyrUp
  - 边缘检测：Canny
  - 形态操作：dilate, erode
  - 图像调整：resize

### Pillow >= 8.3.0
- **导入**：from PIL import Image
- **功能**：图像I/O
- **关键方法**：Image.open(), save()

### matplotlib >= 3.4.0
- **导入**：import matplotlib.pyplot as plt
- **功能**：绘图和可视化
- **关键方法**：plot, scatter, errorbar, savefig, subplot

---

## 📞 验证步骤

```bash
# 第1步：进入项目目录
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments

# 第2步：安装依赖
pip install -r requirements.txt

# 第3步：运行验证脚本
python validate_setup.py

# 如果输出 ✅ ALL CHECKS PASSED，说明安装成功！
```

---

**📌 重要提示**：
- 所有模块版本号是最低版本，更新的版本也可以使用
- 如果遇到版本冲突，可以尝试升级所有模块：`pip install --upgrade numpy scipy pandas opencv-python Pillow matplotlib`
- 对于SLURM环境，建议使用 `--user` 标志：`pip install --user -r requirements.txt`

**✅ 完成后，请运行 `python validate_setup.py` 进行最终验证！**
