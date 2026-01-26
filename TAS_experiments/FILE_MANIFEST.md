# TAS 实验框架 - 文件清单

## 项目目录结构

```
/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments/
│
├── 📄 README.md                          ← 项目说明文档（中文）
├── 📄 DEPENDENCIES.md                    ← 完整的依赖清单（中文）
├── 📄 FILE_MANIFEST.md                   ← 本文件
│
├── 📋 requirements.txt                   ← pip依赖列表（用于pip install）
├── 🔧 validate_setup.py                  ← 验证脚本（检查环境和数据）
├── 🚀 run_all_experiments.py             ← 主脚本（一键运行所有实验）
│
├── 📜 submit_experiments.slurm           ← SLURM提交脚本
│
├── src/                                  ← Python源代码目录
│   ├── __init__.py                       ← （可选）包初始化
│   ├── 🔧 config.py                      ← 配置文件（路径、参数、常量）
│   ├── 📚 data_loader.py                 ← 数据加载模块（加载图像和显著性图）
│   ├── 🎨 artifact_maps.py               ← 伪影图计算（FR-Artifact, NR-Artifact）
│   ├── 🧠 tas_model.py                   ← TAS模型实现（对数线性和混合）
│   ├── 📊 metrics.py                     ← 评估指标（CC, JSD, 信息熵等）
│   ├── 📈 exp_rq1_task_shift.py          ← 实验1：任务偏移分析
│   ├── 📈 exp_rq2_prediction.py          ← 实验2：显著性预测（LOCO交叉验证）
│   ├── 📈 exp_rq3_practical.py           ← 实验3：实用价值分析
│   └── 🎬 visualizer.py                  ← 可视化和报告生成
│
├── results/                              ← 输出结果目录（运行后生成）
│   ├── rq1_task_shift_results.csv        ← RQ1详细结果
│   ├── rq2_prediction_fr_results.csv     ← RQ2 FR-TAS结果
│   ├── rq2_prediction_nr_results.csv     ← RQ2 NR-TAS结果
│   ├── rq3_consistency_results.csv       ← RQ3一致性分析
│   ├── rq3_distraction_results.csv       ← RQ3背景分散分析
│   ├── fig_rq1_task_shift.png            ← RQ1可视化图表
│   ├── fig_rq2_prediction.png            ← RQ2可视化图表
│   ├── fig_rq3_distraction.png           ← RQ3可视化图表
│   └── RESULTS_SUMMARY.txt               ← 最终文本总结报告
│
└── logs/                                 ← 日志目录（运行后生成）
    └── tas_<JOBID>.log                   ← 实验运行日志
```

---

## 数据集路径

```
/iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/
├── OriginalContent/                      ← 40张参考图像
├── TestImages/                           ← 160张JPEG压缩图像
├── SaliencyFreeLook/                     ← 160张自由浏览显著性图
├── SaliencyScoring/                      ← 160张评分任务显著性图
└── read_me.txt                           ← 数据集说明
```

---

## 核心模块说明

### 1️⃣ **config.py** - 配置文件
   - **作用**：定义所有路径、常数、参数
   - **关键变量**：
     - `DATA_ROOT` - 数据集根目录
     - `RESULTS_DIR` - 结果输出目录
     - `NUM_CONTENTS` - 内容数量（40）
     - `NUM_LEVELS` - 压缩级别数（4）
     - `EPSILON` - 数值稳定性参数（1e-12）

### 2️⃣ **data_loader.py** - 数据加载
   - **主要类**：`DataLoader`
   - **关键方法**：
     - `get_unique_contents()` - 获取所有40个内容名称
     - `load_image()` - 加载图像（支持YCrCb色彩空间）
     - `load_saliency_map()` - 加载显著性图（支持自由浏览/评分）
     - `normalize_saliency()` - 归一化为概率分布
     - `get_data_for_content()` - 一次加载某内容的所有数据

### 3️⃣ **artifact_maps.py** - 伪影计算
   - **主要类**：`ArtifactMapGenerator`
   - **关键方法**：
     - `compute_fr_artifact()` - 全参考伪影（多尺度带通错误）
     - `compute_nr_artifact()` - 无参考伪影（块性+环晕）
     - `compute_blockiness_map()` - 块性检测（8×8 JPEG块）
     - `compute_ringing_map()` - 环晕检测（边界振荡）

### 4️⃣ **tas_model.py** - TAS模型
   - **主要类**：`TASModel`
   - **关键方法**：
     - `loglinear_tas()` - 对数线性融合（主方法）
     - `mixture_tas()` - 混合融合（基线）
     - `predict_tas()` - 预测显著性
     - `fit_to_target()` - 优化参数以匹配目标显著性

### 5️⃣ **metrics.py** - 评估指标
   - **主要类**：`SaliencyMetrics`
   - **关键指标**：
     - `pearson_correlation()` - CC相关系数
     - `jensen_shannon_divergence()` - JSD散度
     - `entropy()` - 信息熵
     - `saliency_centroid()` - 显著性质心
     - `centroid_shift()` - 质心偏移距离

### 6️⃣ **exp_rq1_task_shift.py** - 实验1
   - **主要类**：`ExperimentRQ1`
   - **目标**：分析自由浏览 vs 评分任务的显著性差异
   - **输出**：CC, JSD, 信息熵, 质心偏移

### 7️⃣ **exp_rq2_prediction.py** - 实验2
   - **主要类**：`ExperimentRQ2`
   - **目标**：验证TAS预测评分显著性的能力
   - **方法**：LOCO交叉验证，对比多种融合方法
   - **输出**：FR-TAS和NR-TAS的性能对比

### 8️⃣ **exp_rq3_practical.py** - 实验3
   - **主要类**：`ExperimentRQ3`
   - **目标**：分析实用价值（一致性和ROI-背景风险）
   - **指标**：SW-PSNR单调性、背景分散指标
   - **输出**：实用性分析结果

### 9️⃣ **visualizer.py** - 可视化
   - **主要类**：`ResultsVisualizer`
   - **功能**：
     - 绘制RQ1任务偏移曲线
     - 绘制RQ2预测性能对比
     - 绘制RQ3背景分散趋势
     - 生成最终总结报告

---

## 执行流程

### 完整流程
```
1. validate_setup.py
   └─> 检查数据、路径、依赖

2. run_all_experiments.py (主脚本)
   ├─> ExperimentRQ1.run()
   │   └─> rq1_task_shift_results.csv
   │
   ├─> ExperimentRQ2.run() [FR-TAS]
   │   └─> rq2_prediction_fr_results.csv
   │
   ├─> ExperimentRQ2.run() [NR-TAS]
   │   └─> rq2_prediction_nr_results.csv
   │
   ├─> ExperimentRQ3.run()
   │   ├─> rq3_consistency_results.csv
   │   └─> rq3_distraction_results.csv
   │
   └─> ResultsVisualizer.run()
       ├─> fig_rq1_task_shift.png
       ├─> fig_rq2_prediction.png
       ├─> fig_rq3_distraction.png
       └─> RESULTS_SUMMARY.txt
```

---

## 关键数据流

```
原始数据
├── TestImages/{content}_jpgq_({level}).jpg
├── SaliencyFreeLook/{content}_jpgq_({level})_COMBINED.jpg
└── SaliencyScoring/{content}_jpgq_({level})_COMBINED.jpg
           ↓
       DataLoader
           ↓
   ┌─────────┴──────────────────────────┐
   ↓                                    ↓
图像 (YCrCb)                    显著性图 (归一化概率)
   │                                    │
   ├──> ArtifactMapGenerator           │
   │    ├── FR-Artifact (多尺度)       │
   │    └── NR-Artifact (块性)          │
   │         ↓ 归一化为概率             │
   │         P_A                        │
   │                                    │
   └────────┬────────────────┬──────────┘
            ↓                ↓
        TASModel
        ├── loglinear_tas(P_f, P_A) → P_tas
        └── mixture_tas(P_f, P_A) → P_mix
            ↓
        SaliencyMetrics
        ├── CC(P_tas, P_score)
        ├── JSD(P_tas, P_score)
        └── ...
            ↓
        DataFrame → CSV
            ↓
        ResultsVisualizer → PNG/TXT
```

---

## 快速参考

### 运行实验

```bash
# 1. 验证环境
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
python validate_setup.py

# 2. 本地运行（全部实验，可能需要几小时）
python run_all_experiments.py

# 3. 提交到SLURM
sbatch submit_experiments.slurm
```

### 查看结果

```bash
# 查看最终报告
cat results/RESULTS_SUMMARY.txt

# 查看RQ1结果（CSV）
head results/rq1_task_shift_results.csv

# 查看生成的图表
ls -lh results/fig_*.png

# 查看日志
tail -f logs/tas_*.log
```

### 修改配置

编辑 `src/config.py`，调整：
- `VERBOSE` - 详细输出（True/False）
- `SEED` - 随机数种子
- `ALPHA_DEFAULT`, `BETA_DEFAULT`, `GAMMA_DEFAULT` - TAS模型参数

---

## 文件大小估计

| 文件 | 大小 | 说明 |
|------|------|------|
| 源代码 | ~80 KB | 8个.py文件 |
| requirements.txt | ~200 B | 依赖声明 |
| 结果（CSV） | ~10 MB | 3个结果文件 |
| 图表（PNG） | ~3 MB | 3个高分辨率图 |
| 日志 | ~5 MB | 完整运行日志 |
| **总计** | **~18 MB** | 单次完整运行 |

---

## 重要提醒

⚠️ **首次运行前检查清单**：
- [ ] 数据集完整（40 contents，160 images，160 saliency maps）
- [ ] Python版本 ≥ 3.7
- [ ] 已安装 requirements.txt 中的所有包
- [ ] 有充足的磁盘空间（至少50 MB）
- [ ] 已运行 `validate_setup.py` 并通过验证

✅ **运行成功的标志**：
- [ ] 生成 `results/RESULTS_SUMMARY.txt`
- [ ] 生成 3 个 `.png` 图表
- [ ] 生成 5 个 `.csv` 结果文件
- [ ] 日志中无 `ERROR` 信息

---

最后更新：2026年1月16日
