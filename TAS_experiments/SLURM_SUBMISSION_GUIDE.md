# TAS实验改进工作 - SLURM提交指南

**文件**: `TAS_Improvement_v1.slurm`  
**时间**: 2026-01-25  
**预计耗时**: 2-4小时  
**目标**: 生成论文所需的统计表格和跨数据集验证

---

## 🚀 快速开始

### 1️⃣ 提交任务

```bash
# 进入项目目录
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments

# 提交SLURM任务
sbatch TAS_Improvement_v1.slurm

# 输出示例:
# Submitted batch job 548796
```

### 2️⃣ 监控进度

```bash
# 查看任务状态
squeue -u jc15u24 -l

# 实时查看输出 (替换548796为实际ID)
tail -f TAS_Improvement_v1-548796.out

# 监控资源使用
sstat -j 548796 --format=AveVMSize,MaxVMSize,AveRSS,MaxRSS
```

### 3️⃣ 查看结果

```bash
# 任务完成后，查看生成的表格
ls -lh results/table_*.csv results/*summary*.json

# 查看详细日志
tail -100 TAS_Improvement_v1-548796.out
```

---

## 📋 SLURM脚本说明

### 资源配置

```bash
分区:      swarm_a100
节点数:    1
CPU核心:   4 (多核并行处理)
GPU:       0 (纯数据分析，不需要GPU)
内存:      64GB (充足)
时间限制:  12小时
```

**为什么这个配置**:
- 4核CPU: 快速加载和处理数据
- 无GPU: 统计分析不需要GPU加速
- 64GB内存: 足以加载所有数据
- 12小时: 预留足够时间完成所有阶段

### 工作流程 (5个阶段)

#### PHASE 1: 环境验证 (< 1分钟)
```
✓ 检查Conda环境
✓ 验证TUD数据集 (/iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking)
✓ 验证JIST01数据集 (/iridisfs/scratch/jc15u24/Code/JIST01/data)
✓ 检查Python依赖 (numpy, pandas, scipy等)
✓ 验证代码文件 (jist01_loader.py, statistical_analyzer.py等)
```

#### PHASE 2: JIST01多数据集加载 (5-10分钟)
```
✓ 初始化JIST01数据加载器
✓ 发现19种变换类型
✓ 加载11种关键变换 (Reference + Motion Blur + Noise等)
✓ 验证1900+图像数据完整性
```

#### PHASE 3: 完整统计测试 (10-15分钟)
```
✓ 加载TUD基础实验结果 (160个数据点)
✓ 执行配对t检验 (TAS-NR vs FreeLook)
✓ 计算95%置信区间
✓ 计算Cohen's d效应量 (预期6.61)
✓ 应用Bonferroni多重比较校正
✓ 生成统计表格 (CSV格式)
```

#### PHASE 4: 跨数据集对比 (10-15分钟)
```
✓ 对比JIST01中19种变换的影响
✓ 分析变换对显著性的影响
✓ 计算跨数据集汇总统计
✓ 生成JSON格式的对比报告
```

#### PHASE 5: 生成最终报告 (< 5分钟)
```
✓ 列出所有生成的文件
✓ 验证数据完整性
✓ 输出投稿就绪度评估
✓ 显示完成消息
```

**总耗时**: 2-4小时 (取决于集群负载)
  - 输出位置
  - 后续步骤
  - 文档参考
```

#### 4. **内置的数据质量检查**
```python
检查项目:
  ✓ RQ1 样本统计
  ✓ CC 基线 vs TAS 对比
  ✓ JSD 改进计算
  ✓ 统计显著性检验
  ✓ 伪影检测质量
  ✓ 不稳定性分析
```

#### 5. **增强的错误处理**
```bash
- 设置 set -e（任何错误立即停止）
- 数据验证失败时明确报错
- 异常情况下记录详细信息
- 邮件通知 (ALL,FAIL)
```

---

## 🚀 如何提交

### 方式 1: 直接提交（推荐）

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
sbatch TUD.slurm
```

### 方式 2: 检查后提交

```bash
# 先验证脚本
bash -n TUD.slurm

# 查看实际内容
cat TUD.slurm | head -50

# 提交
sbatch TUD.slurm
```

### 方式 3: 指定输出目录

```bash
sbatch --output="/path/to/logs/TAS_v2-%j.out" TUD.slurm
```

---

## 📊 运行预期

### 时间预估

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| Phase 1 | 验证和设置 | 5 分钟 |
| Phase 2a | RQ1 实验 | 30-45 分钟 |
| Phase 2b | RQ2-FR 实验 | 45-60 分钟 |
| Phase 2c | RQ2-NR 实验 | 45-60 分钟 |
| Phase 2d | RQ3 实验 | 20-30 分钟 |
| Phase 2e | 可视化生成 | 15-20 分钟 |
| Phase 3 | 数据验证 | 5-10 分钟 |
| **总计** | | **3-4 小时** |

### 资源使用

```
CPU: 4 cores (并行处理)
GPU: 1 A100
内存: 120-128GB (实际使用: 30-50GB)
存储: 200-500MB (结果文件)
```

---

## 📁 输出文件结构

```
TAS_experiments/
├── results/
│   ├── rq1_task_shift_results.csv
│   ├── rq2_prediction_fr_results.csv
│   ├── rq2_prediction_nr_results.csv
│   ├── rq3_consistency_results.csv
│   ├── rq3_distraction_results.csv
│   └── [plots and reports if generated]
├── logs/
│   ├── tas_main_YYYYMMDD_HHMMSS.log
│   ├── tas_v2_JOBID.log
│   └── validation_JOBID.log
└── TAS_v2-JOBID.out
    TAS_v2-JOBID.err
```

---

## ✅ 成功标志

运行完成后，检查以下标志：

```bash
# 1. 所有结果文件都存在
ls -l results/rq*.csv

# 2. 日志文件无严重错误
grep -i "error\|exception" logs/tas_v2_*.log

# 3. 最终摘要信息
tail -50 TAS_v2-JOBID.out | grep -A 30 "FINAL SUMMARY"

# 4. 检查数据质量
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('results/rq2_prediction_fr_results.csv')
print(f"RQ2-FR samples: {len(df)}")
print(f"CC columns exist: {'tas_cc' in df.columns}")
print(f"JSD columns exist: {'tas_jsd' in df.columns}")
EOF
```

---

## 🔧 故障排除

### 问题 1: "Conda environment not found"

**解决方案**:
```bash
# 检查实际路径
conda env list | grep easygen

# 或手动激活
source /iridisfs/home/jc15u24/.conda/envs/easygen-clean/etc/profile.d/conda.sh
conda activate easygen-clean
```

### 问题 2: "TUD dataset not found"

**解决方案**:
```bash
# 检查数据集位置
ls -ld /iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/

# 确保数据完整
ls /iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/*/
```

### 问题 3: "Python module not found"

**解决方案**:
```bash
# 检查依赖
pip list | grep numpy pandas scipy opencv

# 重新安装
pip install -r /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments/requirements.txt
```

### 问题 4: "GPU memory exceeded"

**解决方案**:
```bash
# 增加内存
sbatch --mem=256G TUD.slurm

# 或减少并行任务
# 编辑 TUD.slurm, 改 cpus-per-task=2
```

---

## 📊 监控运行进度

### 实时查看日志

```bash
# 查看任务状态
squeue -u jc15u24

# 实时跟踪日志
tail -f TAS_v2-JOBID.out

# 查看详细日志
tail -f logs/tas_main_*.log

# 统计进度
grep "✓" TAS_v2-JOBID.out | wc -l
```

### 检查资源使用

```bash
# 查看 GPU 使用
nvidia-smi

# 查看内存使用
free -h

# 查看 CPU 使用
top -b -n 1 | head -20
```

---

## 📈 结果分析

### 快速结果查看

```bash
# RQ1 任务偏移
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('results/rq1_task_shift_results.csv')
print(f"Mean CC: {df['cc'].mean():.4f}")
print(f"Mean JSD: {df['jsd'].mean():.4f}")
EOF

# RQ2 方法对比
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('results/rq2_prediction_fr_results.csv')
print("FR-TAS CC improvement:")
print(f"  Baseline: {df['freelook_cc'].mean():.4f}")
print(f"  TAS:      {df['tas_cc'].mean():.4f}")
print(f"  Change:   {(df['tas_cc'].mean()-df['freelook_cc'].mean()):+.4f}")
EOF
```

### 生成对比表

```bash
python3 << 'EOF'
import pandas as pd
import numpy as np

# 加载数据
rq2_fr = pd.read_csv('results/rq2_prediction_fr_results.csv')
rq2_nr = pd.read_csv('results/rq2_prediction_nr_results.csv')

# 创建对比表
comparison = pd.DataFrame({
    'Method': ['FreeLook', 'FR-TAS', 'NR-TAS'],
    'CC_mean': [
        rq2_fr['freelook_cc'].mean(),
        rq2_fr['tas_cc'].mean(),
        rq2_nr['tas_cc'].mean()
    ],
    'JSD_mean': [
        rq2_fr['freelook_jsd'].mean(),
        rq2_fr['tas_jsd'].mean(),
        rq2_nr['tas_jsd'].mean()
    ]
})

print(comparison.to_string(index=False))
EOF
```

---

## 🎯 下一步行动

### 如果结果良好 ✓

1. **验证改进**
   - [ ] CC 是否不再恶化
   - [ ] artifact_cc 是否 > 0.35
   - [ ] JSD 是否持续改进

2. **论文更新**
   - [ ] 更新 RQ2 结果部分
   - [ ] 添加改进方法说明
   - [ ] 准备投稿

3. **多数据集验证** (可选)
   - [ ] 下载 MIT/COCO 数据集
   - [ ] 进行交叉验证

### 如果结果有问题 ✗

1. **检查问题**
   - [ ] 查看详细日志 `logs/`
   - [ ] 检查数据文件是否完整
   - [ ] 验证依赖版本

2. **调试步骤**
   - [ ] 在本地运行小规模测试
   - [ ] 逐个运行 RQ1/RQ2/RQ3
   - [ ] 查看 Phase 3 的数据质量报告

3. **获取帮助**
   - [ ] 查看 `TAS_EXPERIMENT_REVIEW.md` 的常见问题
   - [ ] 检查 `TAS_REPAIR_FEASIBILITY.md` 的调试指南

---

## 📚 相关文档

- **评估报告**: `../TAS_EXECUTIVE_SUMMARY.md`
- **详细分析**: `../TAS_EXPERIMENT_REVIEW.md`
- **修复指南**: `../TAS_REPAIR_FEASIBILITY.md`
- **建议清单**: `../TAS_QUICK_RECOMMENDATIONS.md`
- **导航索引**: `../README_TAS_EVALUATION.md`

---

## 💡 脚本特点

### ✨ 主要优势

1. **完整的验证流程** - 确保数据和环境正确
2. **详细的进度日志** - 实时跟踪运行状态
3. **内置的数据验证** - 自动检查结果质量
4. **清晰的错误处理** - 任何问题都能快速定位
5. **组织良好的输出** - 便于后续分析
6. **邮件通知** - 完成或失败都会通知

### 🎯 工作流设计

```
验证环境 → 运行实验 → 生成可视化 → 数据验证 → 结果总结
   |         |            |          |          |
  5 min   3-4 hours      15 min     10 min     输出
```

---

## 📋 检查清单 (提交前)

- [ ] TUD.slurm 文件已更新
- [ ] 具有可执行权限: `chmod +x TUD.slurm`
- [ ] 项目路径正确: `/iridisfs/scratch/jc15u24/Code/IST02`
- [ ] 数据集存在: `TUD_Task_EyeTracking/`
- [ ] Conda 环境已创建: `easygen-clean`
- [ ] Python 依赖已安装: `pip install -r requirements.txt`
- [ ] 日志目录存在或可创建: `logs/`
- [ ] 结果目录存在或可创建: `results/`
- [ ] 邮箱地址正确: `jc15u24@soton.ac.uk`

---

## 🎉 祝好运！

改进的脚本已准备好提交。这个版本包含了完整的验证、详细的日志记录和自动的数据质量检查。

**预期结果**: 3-4 小时后获得完整的改进实验结果。

有任何问题，请参考本指南或详细的评估文档。

