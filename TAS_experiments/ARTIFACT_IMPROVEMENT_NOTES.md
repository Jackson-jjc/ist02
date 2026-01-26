# 伪影检测改进说明

## 改进内容（已完成）

### 1. 核心算法升级
- **原始**：简单 8×8 blockiness 边界检测
- **改进**：多尺度 SSIM + DCT 系数分析 + CSF 加权

### 2. FR-Artifact 改进（全参考）
```python
# 新增组件：
- 多尺度 SSIM (权重 0.6)
  * 5 个尺度，权重 [0.0448, 0.2856, 0.3001, 0.2363, 0.0333]
  * 直接测量感知质量差异
  * SSIM = -1 时表示完全不同，1 表示相同
  
- DCT 系数分析 (权重 0.4)
  * 8×8 JPEG 块的高频分量检测
  * 直接对应 JPEG 压缩机制
  * 高频能量 ∝ 压缩伪影
```

**预期改进**：artifact_cc 从 0.074 → 0.35-0.50 (5-7 倍)

### 3. NR-Artifact 改进（无参考）
```python
# 新增多组件融合 (权重组合)：
- 改进 blockiness 检测 (0.4) - 使用 DCT 信息
- DCT 高频分析 (0.4) - 直接压缩伪影检测  
- Ringing 检测 (0.2) - 边缘环形伪影

# 与原始的区别：
原始：只有简单的 blockiness
改进：多维度综合评估 (DCT + blockiness + ringing)
```

### 4. 代码改进
- 新增 `_compute_ssim_multiscale()` - 多尺度 SSIM 计算
- 新增 `_compute_dct_artifact()` - DCT 系数伪影检测
- 新增 `_compute_improved_blockiness()` - 改进 blockiness
- 新增日志和调试信息

## 文件变更
```
src/artifact_maps.py
├─ 增加了 scipy.fftpack 导入
├─ 新增 3 个核心方法
├─ 升级 compute_fr_artifact() 
├─ 升级 compute_nr_artifact()
└─ 添加详细日志
```

## 预期效果

### 关键指标改进
| 指标 | 原始 | 预期 | 改进倍数 |
|------|------|------|---------|
| artifact_cc | 0.074 | >0.30 | 4-5倍 |
| FR-TAS CC | 0.8421 | ≥0.8487 | +0.66% |
| NR-TAS CC | 0.7910 | ≥0.8300 | +5% |
| NR-TAS 稳定性 | CV+116% | CV<10% | 显著改善 |

### 运行时间
- 伪影检测：额外 30-50% 时间（仍可接受）
- 总运行时间：3-4 小时 → 4-5 小时

## 实验提交信息
```
Job ID: 533387
提交时间: 2026-01-20
脚本: TUD.slurm (改进版，含新伪影检测)
资源: 4 CPU, 128GB RAM, 48h
队列: swarm_a100
```

## 监控命令

### 查看任务状态
```bash
squeue -u jc15u24
squeue -j 533387
```

### 实时查看日志
```bash
# 主日志
tail -f logs/tas_main_*.log

# 查看 Phase 3 的伪影检测结果
grep -A 20 "PHASE 3" logs/tas_main_*.log | grep "Artifact"
```

### 关键验证点
```bash
# 运行完后，检查伪影检测改进是否有效
python3 << 'EOF'
import pandas as pd
import numpy as np

# 加载结果
fr_results = pd.read_csv('results/rq2_prediction_fr_results.csv')
nr_results = pd.read_csv('results/rq2_prediction_nr_results.csv')

# 检查 artifact_cc 改进
print(f"artifact_cc 平均: {nr_results['artifact_cc'].mean():.4f}")
print(f"artifact_cc 标准差: {nr_results['artifact_cc'].std():.4f}")

# 如果 > 0.30，说明伪影检测改进成功
if nr_results['artifact_cc'].mean() > 0.30:
    print("✅ 伪影检测成功改进！")
else:
    print("⚠️  伪影检测改进有限，可能需要进一步调整")

# 检查 CC 指标
print(f"\nFR-TAS CC: {fr_results['cc'].mean():.4f}")
print(f"NR-TAS CC: {nr_results['cc'].mean():.4f}")
EOF
```

## 下一步计划

### 如果伪影检测改进成功 (artifact_cc > 0.30)
1. ✅ 验证 CC 下降问题是否缓解
2. 如果 NR-TAS CC 还有下降，进入 Phase 2：融合参数优化
3. 准备投稿

### 如果伪影检测改进有限 (artifact_cc ≤ 0.30)
1. 需要进一步调试 DCT 参数
2. 考虑使用预训练的 CNN 特征提取
3. 扩展到其他伪影类型检测

## 技术细节

### SSIM 计算
- 窗口大小: 11×11
- 高斯σ: 1.5
- k1, k2: 0.01, 0.03
- 5 个尺度的权重: [0.0448, 0.2856, 0.3001, 0.2363, 0.0333]

### DCT 分析
- 块大小: 8×8 (标准 JPEG)
- 低频阈值: 3×3 区域（移除 DC 和低频）
- 高频能量累积: 所有高频系数平方和
- 归一化: 95 百分位数

### Blockiness 检测
- 沿 8×8 块边界计算差异
- 水平和垂直边界分别处理
- 高斯平滑: σ=1.0, 5×5 kernel

## 预期发布时间
- 任务预计 4-5 小时完成
- 预计完成时间: 2026-01-20 下午 3-5 点

---
**更新时间**: 2026-01-20
**改进版本**: v2.1 (Improved Artifact Detection)
**状态**: 运行中 (Job 533387)
