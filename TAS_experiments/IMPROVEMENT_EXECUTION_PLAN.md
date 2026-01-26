# TAS 实验改进执行计划 - 完整版

**生成时间**: 2026-01-25  
**状态**: 🚀 立即执行  
**目标**: SCI 4区论文完整数据包  

---

## 📋 整体改进方案

### 现状分析
- ✅ TUD数据完整（160个数据点）
- ✅ 统计显著性强（p < 0.001）
- ⚠️ 单数据集验证（需补充JIST01）
- ⚠️ 效应量中等（Cohen's d = 0.44）
- ⚠️ 内容异质性高（需要亚组分析）
- ⚠️ 缺少可视化示例和对比

### JIST01数据集评估
- **兼容性**: ✅ 完全兼容
  - 格式: .mat (Tobii X120记录)
  - 分辨率: 1080×1920 (与TUD基本一致)
  - 样本量: 1900图像
  - 眼动数据: 10个被试/图像，4秒/图像，60Hz采样
  
- **与TUD的区别**:
  - TUD: 40个视频内容，自然视频序列
  - JIST01: 1900个静态图像，各种变换
  - **优势**: 提供跨数据集验证和变换鲁棒性评估

- **建议使用模式**:
  1. 选择Reference + 关键变换类型 (Motion Blur, Noise, Compression)
  2. 与TUD结果对比，验证泛化性
  3. 评估TAS对图像变换的鲁棒性

---

## 🛠️ 五大改进模块

### 模块1: JIST01数据集集成 (优先级: ⭐⭐⭐⭐⭐)
**时间**: 2-3小时  
**负责**: 数据加载和格式转换

**Action Items**:
1. [ ] 创建 `jist01_loader.py` - 加载JIST01 .mat格式数据
2. [ ] 修改 `config.py` - 添加JIST01相关配置
3. [ ] 运行验证 - 在JIST01上执行TAS模型
4. [ ] 生成对比表 - Cross-dataset summary

**预期输出**:
- `results/JIST01_validation_nr_v4.csv`
- `results/JIST01_validation_fr_v4.csv`
- `results/cross_dataset_summary.json`

**关键指标**:
```
TUD:     CC_mean = 0.2049 ± 0.1221 (NR-TAS)
JIST01:  CC_mean = ??? (预期 0.18-0.22)  ← 验证一致性
效应量差异应 < 10%
```

---

### 模块2: 可视化轨迹示例 (优先级: ⭐⭐⭐⭐)
**时间**: 2-3小时  
**负责**: 图形化展示和对比

**Action Items**:
1. [ ] 选择代表性样本
   - 最佳表现: kid_bucket (CC=0.928)
   - 中等表现: walking_bear (CC=0.720)
   - 最差表现: dog (CC=0.542)

2. [ ] 生成对比图表 (每个样本)
   - 行1: 原始视频帧截图
   - 行2: 自由浏览显著性热力图
   - 行3: NR-TAS预测显著性
   - 行4: 差异可视化 (误差图)

3. [ ] 创建眼动轨迹覆盖图
   - 显示前100个扫视序列
   - 标注扫视方向和持续时间

4. [ ] 生成统计对比条形图
   - CC分布 (按方法和变换)
   - JSD分布 (按方法)

**预期输出**:
- `results/figures/fig_best_case_example.pdf`
- `results/figures/fig_worst_case_example.pdf`
- `results/figures/fig_gaze_trajectory_overlay.pdf`
- `results/figures/fig_method_comparison_bars.pdf`

---

### 模块3: 内容亚组分析 (优先级: ⭐⭐⭐⭐)
**时间**: 1-2小时  
**负责**: 场景复杂度分类和子组比较

**Action Items**:
1. [ ] 按显著性预测性能分类40个内容
   ```
   Low Complexity     (CC < 0.65): dog, cycler_ice, walking_bear, climber_sunglasses
   Medium Complexity  (0.65-0.80): [20个]
   High Complexity    (CC > 0.88): kid_bucket, man_desert, bird_bushes, [20个]
   ```

2. [ ] 计算每类的汇总统计
   ```
   按类别输出:
   - 样本数, 均值, SD, Min, Max
   - 95% 置信区间
   ```

3. [ ] 执行Kruskal-Wallis H检验
   - H统计量, p值, 效应量(eta-squared)

4. [ ] 生成分层对比表
   - 方法×复杂度×数据集 的3维表

**预期输出**:
- `results/content_complexity_analysis.csv`
- `results/subgroup_statistics.json`
- `results/kruskal_wallis_results.txt`

---

### 模块4: 统计测试补充 (优先级: ⭐⭐⭐)
**时间**: 1.5小时  
**负责**: 详细的统计检验和置信区间

**Action Items**:
1. [ ] 计算所有方法对的配对t检验
   ```
   TAS vs FreeLook, TAS vs Mixture, TAS vs Artifact
   输出: t统计量, p值, Cohen's d, 95% CI
   ```

2. [ ] 应用Bonferroni多重比较校正
   - 调整显著性水平: α/n
   - 标记显著对

3. [ ] 计算效应量和功效
   - Cohen's d (已有)
   - Hedges' g (无偏估计)
   - 后验功效分析

4. [ ] 生成95%置信区间
   - 每个方法的CC均值±95%CI
   - 方法差异的置信区间

**预期输出**:
- `results/statistical_tests_complete.csv`
- `results/confidence_intervals.json`
- `results/effect_sizes_summary.txt`

---

### 模块5: 参数敏感性分析 (优先级: ⭐⭐)
**时间**: 1-2小时  
**负责**: 验证模型参数的稳健性

**Action Items**:
1. [ ] 绘制参数曲线
   - α (频率权重): 0.8-1.6
   - β (伪影权重): 0.05-0.15
   - γ (内容权重): 1.4-2.2
   - 对CC的影响曲线

2. [ ] 执行局部敏感性分析
   - 固定其他参数，逐个变化
   - 记录CC变化

3. [ ] 验证参数最优性
   - 确认当前参数 (1.2, 0.1, 1.8) 接近最优

**预期输出**:
- `results/parameter_sensitivity_analysis.pdf`
- `results/parameter_optimization_results.json`

---

## 📊 改进前后对比表

```
┌─────────────────────────┬────────────┬───────────┬──────────┐
│ 指标                    │ 改进前     │ 改进后    │ 提升     │
├─────────────────────────┼────────────┼───────────┼──────────┤
│ 数据集覆盖              │ 1 (TUD)    │ 2 (TUD+J) │ +100%    │
│ 样本量                  │ 160        │ 160+1900  │ +1075%   │
│ 统计检验完整性          │ 30%        │ 95%       │ +65%     │
│ 可视化示例              │ 无         │ 4-5个     │ 新增     │
│ 参数验证                │ 部分       │ 完整      │ 完成     │
│ 论文就绪度              │ 70%        │ 95%       │ +25%     │
└─────────────────────────┴────────────┴───────────┴──────────┘
```

---

## 🚀 执行时间表

| 周 | 任务 | 时间 | 优先级 | 状态 |
|---|------|------|--------|------|
| 1-Day1 | 模块1: JIST01集成 | 2-3h | ⭐⭐⭐⭐⭐ | 待开始 |
| 1-Day2 | 模块4: 统计测试 | 1.5h | ⭐⭐⭐ | 待开始 |
| 1-Day3 | 模块2: 可视化轨迹 | 2-3h | ⭐⭐⭐⭐ | 待开始 |
| 2-Day1 | 模块3: 亚组分析 | 1-2h | ⭐⭐⭐⭐ | 待开始 |
| 2-Day2 | 模块5: 参数敏感 | 1-2h | ⭐⭐ | 待开始 |
| 2-Day3 | 汇总与校对 | 1h | ⭐⭐⭐ | 待开始 |

**总耗时**: 9-13小时 (约2天实时计算)

---

## 📋 投稿准备最终检查清单

### 必须完成 (Mandatory)
- [ ] JIST01数据验证完成
- [ ] 所有统计测试通过
- [ ] 至少3张对比图表
- [ ] Methods部分完整
- [ ] Tables: 3-4个

### 强烈建议 (Highly Recommended)
- [ ] 亚组分析结果
- [ ] 参数敏感性分析
- [ ] 失败案例分析
- [ ] 与相关工作详细对比表

### 可选增强 (Optional but beneficial)
- [ ] 计算复杂度分析
- [ ] 跨用户/跨摄像机鲁棒性
- [ ] 实时应用演示视频

---

## ⚠️ 风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| JIST01 .mat 格式不兼容 | 无法运行 | 提前测试加载器 |
| 计算时间过长 | 延期投稿 | 使用采样或并行 |
| JIST01结果与TUD偏差大 | 论文被拒 | 分析原因，调整假设 |
| 可视化质量差 | 减分 | 使用高质量渲染器 |

---

## 📞 技术支持检查表

- [ ] Python版本: >= 3.8
- [ ] 必需库: scipy, numpy, pandas, matplotlib, scikit-learn
- [ ] CUDA/GPU: 可选但推荐
- [ ] 磁盘空间: >= 10GB
- [ ] 内存: >= 16GB

---

**下一步**: 立即开始模块1 (JIST01集成)
