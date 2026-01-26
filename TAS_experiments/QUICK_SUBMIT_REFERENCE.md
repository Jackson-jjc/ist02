# TAS改进工作 - SLURM快速提交参考

## ⚡ 30秒快速提交

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
sbatch TAS_Improvement_v1.slurm
```

**输出示例**: 
```
Submitted batch job 548796
```

## 📊 新SLURM脚本说明

| 配置项 | 设置 | 说明 |
|--------|------|------|
| **脚本名** | TAS_Improvement_v1.slurm | 新改进工作专用 |
| **CPU核心** | 4 | 多核并行处理 |
| **内存** | 64GB | 足以加载所有数据 |
| **GPU** | 0 | 不需要GPU(纯数据分析) |
| **时间** | 12小时 | 足以完成所有阶段 |
| **分区** | swarm_a100 | 标准计算分区 |

## 🎯 5个工作阶段

```
PHASE 1 (< 1 min)   环境验证
  └─ 检查TUD/JIST01数据, Python依赖, 代码文件
    ↓
PHASE 2 (5-10 min)  JIST01多数据集加载
  └─ 加载19种变换, 1900+图像数据
    ↓
PHASE 3 (10-15 min) 完整统计测试
  └─ t检验, 置信区间, 效应量, Bonferroni校正
    ↓
PHASE 4 (10-15 min) 跨数据集对比
  └─ 分析变换影响, 生成汇总统计
    ↓
PHASE 5 (< 5 min)   生成最终报告
  └─ 输出所有文件, 验证完整性

⏱️ 总耗时: 约 2-4 小时
```

## 📁 生成的输出文件

```
results/
├── table_method_comparison.csv          ← 论文Table 1 (方法对比)
├── table_statistical_tests.csv          ← 论文Table 2 (统计检验)
├── content_complexity_analysis.json     ← 论文Table 3 (复杂度)
├── cross_dataset_summary.json           ← 跨数据集汇总
└── jist01_transformation_comparison.csv ← JIST01变换对比

logs/
├── jist01_analysis_YYYYMMDD_HHMMSS.log
├── statistical_tests_YYYYMMDD_HHMMSS.log
├── cross_dataset_YYYYMMDD_HHMMSS.log
└── TAS_Improvement_v1-548796.out (主日志)
    ├─ RQ2-NR: 无参考 TAS
    └─ RQ3: 实际价值 + 可视化
    ↓
PHASE 3 (10 min)    → 数据质量检查
    ├─ CC/JSD 统计
    ├─ 配对 t 检验
    └─ 伪影检测质量
    ↓
PHASE 4 (输出)      → 结果总结
```

## 📁 输出位置

```
results/
  ├── rq1_task_shift_results.csv
  ├── rq2_prediction_fr_results.csv      ← FR-TAS 结果
  ├── rq2_prediction_nr_results.csv      ← NR-TAS 结果
  ├── rq3_consistency_results.csv
  └── rq3_distraction_results.csv

logs/
  ├── tas_main_YYYYMMDD_HHMMSS.log     ← 主实验日志
  ├── tas_v2_JOBID.log                 ← 调试日志
  └── validation_JOBID.log             ← 验证日志
```

## ✅ 监控命令

```bash
# 查看任务状态
squeue -u jc15u24

# 实时日志 (替换 JOBID)
tail -f logs/tas_main_*.log

# 快速结果查看
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('results/rq2_prediction_fr_results.csv')
print(f"FR-TAS CC improvement: {df['tas_cc'].mean() - df['freelook_cc'].mean():+.4f}")
print(f"FR-TAS JSD improvement: {df['freelook_jsd'].mean() - df['tas_jsd'].mean():+.4f}")
EOF
```

## 🔍 关键指标检查

```bash
# RQ2-FR 的 CC 改进（应该不再恶化）
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('results/rq2_prediction_fr_results.csv')
cc_change = df['tas_cc'].mean() - df['freelook_cc'].mean()
print(f"CC Change: {cc_change:+.6f}")
print(f"Status: {'✓ 改进' if cc_change > -0.005 else '✗ 仍在恶化'}")
EOF

# Artifact CC 质量（应该 > 0.30）
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('results/rq2_prediction_nr_results.csv')
artifact_cc = df['artifact_cc'].mean()
print(f"Artifact CC: {artifact_cc:.6f}")
print(f"Status: {'✓ 足够好' if artifact_cc > 0.30 else '✗ 仍需改进'}")
EOF
```

## 🎓 改进指标快查

| 指标 | 旧结果 | 新结果 | 目标 |
|------|--------|--------|------|
| **FR-TAS CC** | 0.8421 (↓0.66%) | ? | ≥ 0.8487 |
| **Artifact CC** | 0.074 | ? | > 0.30 |
| **NR-TAS Stability** | ↑116% | ? | 接近基线 |

## 🆘 快速故障排除

```bash
# 问题 1: 找不到 conda 环境
source activate /iridisfs/home/jc15u24/.conda/envs/easygen-clean

# 问题 2: 找不到 TUD 数据集
ls -ld /iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/

# 问题 3: Python 导入错误
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
python3 -c "from src.config import config; print('✓ OK')"

# 问题 4: 查看任务失败原因
cat TAS_v2-JOBID.err | grep -i error
```

## 📞 相关文档

- **完整指南**: [SLURM_SUBMISSION_GUIDE.md](./SLURM_SUBMISSION_GUIDE.md)
- **评估摘要**: [../TAS_EXECUTIVE_SUMMARY.md](../TAS_EXECUTIVE_SUMMARY.md)
- **详细分析**: [../TAS_EXPERIMENT_REVIEW.md](../TAS_EXPERIMENT_REVIEW.md)

## 💡 Tips

1. **提交前检查**
   ```bash
   bash -n TUD.slurm  # 验证语法
   ```

2. **交互式测试**（运行前先试小规模）
   ```bash
   cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
   python3 -c "from src.exp_rq1_task_shift import ExperimentRQ1; print('✓ Modules OK')"
   ```

3. **监控内存使用**
   ```bash
   watch -n 5 'free -h | grep -E "^Mem"'
   ```

4. **保存结果备份**
   ```bash
   cp -r results results_backup_$(date +%Y%m%d_%H%M%S)
   ```

## 🎉 预期结果

运行完成后 (3-4 小时)：
- ✓ 6 个 CSV 结果文件
- ✓ 可视化图表 (如果支持)
- ✓ 详细日志
- ✓ 统计验证报告
- ✓ 邮件通知

**成功标志**: 所有结果文件都存在，日志中没有 ERROR

