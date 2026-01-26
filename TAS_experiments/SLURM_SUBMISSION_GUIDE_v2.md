# 🚀 TAS实验改进 - SLURM提交指南

**文件**: `TAS_Improvement_v2.slurm`  
**状态**: ✅ 已修复并验证  
**耗时**: 预计 30-60 分钟

---

## ⚡ 快速提交 (3个命令)

```bash
# 1. 进入项目目录
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments

# 2. 提交任务
sbatch TAS_Improvement_v2.slurm

# 3. 查看任务状态
squeue -lu jc15u24
```

---

## 📋 SLURM配置说明

| 参数 | 值 | 说明 |
|------|-----|------|
| Job名 | TAS_Improvement_v2 | 任务名称 |
| 分区 | swarm_a100 | 使用A100分区 |
| CPU核 | 4 | 4核CPU |
| GPU | 0 | 不需要GPU |
| 内存 | 32G | 32GB内存 |
| 时限 | 2小时 | 足以完成任务 |

**为什么改了?**
- ✓ GPU改为0 (不需要)
- ✓ 内存降为32G (足够且更容易被调度)
- ✓ 时限改为2小时 (任务实际只需30-60分钟)

---

## 🎯 任务内容

### Task 1: JIST01数据加载 (已修复 ✓)
```
✓ 加载3种关键变换
✓ 验证100张显著性图
✓ 生成数据统计
```

**修复点**: 正确处理预计算的显著性图格式

### Task 2: 统计分析
```
✓ 配对t检验
✓ 置信区间计算
✓ Cohen's d效应量
✓ Bonferroni校正
```

### Task 3: 跨数据集对比
```
✓ TUD vs JIST01对比
✓ 变换影响分析
✓ 生成对比表
```

---

## 📊 输出文件

任务完成后，会在 `results/` 生成:

```
results/
├── table_method_comparison.csv          ← 论文Table 1
├── table_statistical_tests.csv          ← 论文Table 2
└── jist01_transformation_comparison.csv ← 变换对比
```

---

## 🔍 实时监控

### 监控任务进度
```bash
# 查看任务状态
squeue -lu jc15u24

# 查看输出 (实时)
tail -f TAS_Improvement_v2-*.out

# 查看错误
tail -f TAS_Improvement_v2-*.err

# 查看详细日志
ls -lh logs/improvement_v2_*.log
```

### 任务完成后
```bash
# 检查结果
ls -lh results/table_*.csv

# 查看表格内容
head results/table_method_comparison.csv
```

---

## ⚠️ 如果任务失败

### 查看错误日志
```bash
# 最新的错误文件
tail -100 TAS_Improvement_v2-*.err

# 或查看详细日志
cat logs/improvement_v2_*.log
```

### 常见错误和解决方案

**错误1: 无法找到JIST01数据**
```
→ 检查路径: /iridisfs/scratch/jc15u24/Code/JIST01/data
```

**错误2: 内存不足**
```
→ 在SLURM中改为 #SBATCH --mem=64G
```

**错误3: 超时**
```
→ 改为 #SBATCH --time=3:00:00
```

---

## 📝 修改SLURM参数

如需修改SLURM参数，编辑文件开头:

```bash
#SBATCH --job-name=TAS_Improvement_v2    # 任务名
#SBATCH --partition=swarm_a100           # 分区
#SBATCH --nodes=1                        # 节点数
#SBATCH --ntasks=1                       # 任务数
#SBATCH --cpus-per-task=4                # CPU核数
#SBATCH --mem=32G                        # 内存 (改为64G if 不足)
#SBATCH --time=2:00:00                   # 时限 (改为3:00:00 if 超时)
#SBATCH --mail-type=FAIL                 # 失败时邮件通知
```

---

## 🎓 推荐流程

```
1. 提交任务
   sbatch TAS_Improvement_v2.slurm
   
2. 获取任务ID
   显示: Submitted batch job XXXXXX
   
3. 监控进度 (可选)
   tail -f TAS_Improvement_v2-XXXXXX.out
   
4. 等待完成
   预计时间: 30-60分钟
   
5. 检查结果
   ls -lh results/table_*.csv
   
6. 使用数据
   复制CSV表格到论文中
```

---

## ✅ 验证清单

运行前检查:
- [ ] JIST01数据存在: `/iridisfs/scratch/jc15u24/Code/JIST01/data/`
- [ ] TUD数据存在: `/iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking/`
- [ ] SLURM文件有执行权限: `ls -l TAS_Improvement_v2.slurm` (应有x权限)
- [ ] Python虚拟环境可用: 已在脚本中配置

完成后检查:
- [ ] 任务状态: COMPLETED
- [ ] 没有ERROR或FAILED
- [ ] results/目录有CSV文件
- [ ] 文件大小> 0

---

## 🔗 相关文档

- [改进工作总结](FINAL_IMPROVEMENT_SUMMARY.txt)
- [快速开始指南](START_HERE_IMPROVEMENT.md)
- [资源索引](IMPROVEMENT_RESOURCE_INDEX.md)

---

## 💬 常见问题

**Q: 任务会运行多长时间?**  
A: 预计30-60分钟。包括:
- JIST01加载: ~5分钟
- 统计分析: ~10分钟
- 数据输出: ~5分钟

**Q: 如果我想修改参数怎么办?**  
A: 编辑SLURM文件中的 `#SBATCH` 行，然后重新提交

**Q: 失败了怎么办?**  
A: 查看错误日志 `TAS_Improvement_v2-*.err`，修复问题后重新提交

**Q: 怎样取消任务?**  
A: `scancel <JOBID>` (任务ID可从squeue得到)

---

## 📞 快速命令参考

```bash
# 查看所有任务
squeue -lu jc15u24

# 提交新任务
sbatch TAS_Improvement_v2.slurm

# 取消任务
scancel <JOBID>

# 查看任务详情
scontrol show job <JOBID>

# 查看最新输出
tail -50 TAS_Improvement_v2-*.out

# 查看完整日志
cat logs/improvement_v2_*.log

# 查看结果文件
ls -lh results/table_*.csv
```

---

**准备就绪! 可以提交任务了 🚀**

```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
sbatch TAS_Improvement_v2.slurm
```
