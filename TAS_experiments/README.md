# Task-Adaptive Saliency (TAS) Experiments

这是基于TUD眼动追踪数据集的任务自适应显著性实验框架。

## 项目结构

```
TAS_experiments/
├── src/                              # Python源代码
│   ├── config.py                     # 配置文件
│   ├── data_loader.py                # 数据加载模块
│   ├── artifact_maps.py              # 伪影图计算
│   ├── tas_model.py                  # TAS模型实现
│   ├── metrics.py                    # 评估指标
│   ├── exp_rq1_task_shift.py         # 实验1：任务偏移分析
│   ├── exp_rq2_prediction.py         # 实验2：显著性预测
│   ├── exp_rq3_practical.py          # 实验3：实用价值
│   └── visualizer.py                 # 可视化和报告
├── run_all_experiments.py            # 主脚本（一键运行所有实验）
├── validate_setup.py                 # 验证脚本
├── submit_experiments.slurm          # SLURM提交脚本
├── results/                          # 结果输出目录
└── logs/                             # 日志文件
```

## 数据集要求

该实验框架使用TUD Image Quality Database: Eye-Tracking Release 2数据集，包含：

- **OriginalContent/** (40张参考图像)
- **TestImages/** (160张JPEG压缩图像 = 40内容 × 4压缩级别)
- **SaliencyFreeLook/** (160张自由浏览显著性图)
- **SaliencyScoring/** (160张评分任务显著性图)

数据集位置：`/iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/`

## 快速开始

### 1. 验证环境和数据

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
python validate_setup.py
```

如果所有检查通过，您会看到 `✓ ALL CHECKS PASSED`。

### 2. 本地运行（小规模测试）

```bash
# 创建并激活虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或在Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行所有实验
python run_all_experiments.py
```

### 3. 提交到SLURM（推荐用于完整运行）

```bash
sbatch submit_experiments.slurm
```

查看任务状态：
```bash
squeue -lu jc15u24
```

查看输出：
```bash
tail -f logs/tas_<JOBID>.out
```

## 实验说明

### 实验1: RQ1 - 任务偏移分析 (Task Shift Analysis)

**研究问题**: 自由浏览和评分任务的显著性分布如何随JPEG压缩而改变？

**关键指标**:
- **CC (Pearson相关系数)**: 显著性相似度 (↑越好)
- **JSD (Jensen-Shannon散度)**: 分布差异 (↓越好)
- **信息熵**: 注意力集中度
- **质心偏移**: 空间稳定性

**输出**:
- `rq1_task_shift_results.csv` - 详细结果
- `fig_rq1_task_shift.png` - 趋势曲线

### 实验2: RQ2 - 显著性预测 (Saliency Prediction)

**研究问题**: 能否使用自由浏览显著性 + 伪影证据预测评分显著性？

**方法对比**:
1. **FreeLook** - 基线（仅自由浏览）
2. **Artifact-only** - 仅伪影
3. **Mixture** - 加权混合
4. **TAS (Log-linear)** - 本文方法（对数线性）
5. **Oracle** - 上界（评分显著性本身）

**两个变体**:
- **FR-TAS** - 全参考伪影图（更强但需参考图）
- **NR-TAS** - 无参考伪影图（可部署）

**交叉验证**: Leave-One-Content-Out (LOCO)

**输出**:
- `rq2_prediction_fr_results.csv` - FR-TAS结果
- `rq2_prediction_nr_results.csv` - NR-TAS结果
- `fig_rq2_prediction.png` - 方法对比

### 实验3: RQ3 - 实用价值分析 (Practical Value)

**轨迹B** (无MOS可用): 一致性和ROI-背景风险指标

**关键指标**:
- **SW-PSNR** (显著性加权PSNR): 衡量感知质量
- **单调性违反率**: 压缩级别增加时PSNR应单调递减
- **背景分散指标** ($D_{bg}$): 背景注意力泄漏

**输出**:
- `rq3_consistency_results.csv` - 一致性分析
- `rq3_distraction_results.csv` - 背景分散分析
- `fig_rq3_distraction.png` - 趋势比较

## 核心算法

### 伪影图计算

#### FR-Artifact (全参考)
多尺度带通加权误差：
$$A_{FR}(x) = \sum_{k=1}^{K} w_k \cdot |B_k(Y_d)(x) - B_k(Y_r)(x)|$$

#### NR-Artifact (无参考)
基于8×8 JPEG块界的块性指标加可选的环晕检测。

### TAS模型

#### 对数线性模型 (推荐)
$$\tilde{P}_{tas}(x) \propto (P_f(x)+\delta)^{\alpha} \cdot (A(x)+\delta)^{\beta} \cdot (P_C(x)+\delta)^{\gamma}$$

其中：
- $P_f$ = 自由浏览显著性
- $A$ = 伪影概率图
- $\delta = 1/(H \times W)$ = 底层概率（防止零值困境）
- 参数 $\{\alpha, \beta, \gamma\}$ 按压缩级别学习

#### 混合模型 (基线)
$$P_{mix} = \text{norm}(w_1 P_f + w_2 P_A + w_3 P_C)$$

## 参数配置

在 `src/config.py` 中修改：

```python
# 数据集
NUM_CONTENTS = 40
NUM_LEVELS = 4

# TAS模型默认参数
ALPHA_DEFAULT = 1.0      # 自由浏览权重
BETA_DEFAULT = 1.0       # 伪影权重
GAMMA_DEFAULT = 0.1      # 中心先验权重

# 预处理
EPSILON = 1e-12
SALIENCY_DENOISE_SIGMA = 1.0
```

## 输出文件

### 结果文件 (results/)
- `rq1_task_shift_results.csv` - RQ1详细结果
- `rq2_prediction_fr_results.csv` - RQ2 FR-TAS结果
- `rq2_prediction_nr_results.csv` - RQ2 NR-TAS结果
- `rq3_consistency_results.csv` - RQ3一致性结果
- `rq3_distraction_results.csv` - RQ3分散指标
- `RESULTS_SUMMARY.txt` - 文本总结报告

### 图表 (results/)
- `fig_rq1_task_shift.png` - 任务偏移曲线
- `fig_rq2_prediction.png` - 预测性能对比
- `fig_rq3_distraction.png` - 背景分散趋势

### 日志文件 (logs/)
- `tas_<JOBID>.log` - 详细运行日志（本地）
- `tas_<JOBID>.out` - SLURM标准输出
- `tas_<JOBID>.err` - SLURM错误输出

## 关键设计原则

1. **内容分组交叉验证** - 防止同一场景在训练/测试中泄漏
2. **亮度通道** - 使用YCrCb色彩空间的Y通道（JPEG伪影主要在亮度）
3. **概率归一化** - 所有显著性图均归一化为概率分布
4. **参数学习** - 在训练集上选择所有参数，然后应用到测试集
5. **统计推断** - 以内容为单位（n=40）避免伪重复

## 依赖项

- numpy >= 1.21.0
- scipy >= 1.7.0
- pandas >= 1.3.0
- opencv-python >= 4.5.0
- Pillow >= 8.3.0
- matplotlib >= 3.4.0

## 故障排除

### 数据找不到
```bash
# 检查数据路径
python -c "from src.config import DATA_ROOT; print(DATA_ROOT)"
```

### 内存不足
修改 `src/config.py` 中的 `VERBOSE = False` 以减少日志输出。

### 显著性图加载失败
确保 SaliencyFreeLook/ 和 SaliencyScoring/ 文件夹中的文件命名格式正确（`_COMBINED.jpg` 后缀）。

## 参考文献

数据集论文：
- H. Alers, H. Liu, J. Redi and I. Heynderickx, "TUD Image Quality Database: Eye-Tracking Release 2", 2010
- H. Alers et al., "Studying the risks of optimizing the image quality in saliency regions at the expense of background content", IS&T/SPIE Electronic Imaging 2010

## 许可证

本实验框架遵循与数据集相同的许可证。使用该数据集的研究请引用上述论文。

## 联系信息

如有问题，请查看日志文件或提交 issue。
