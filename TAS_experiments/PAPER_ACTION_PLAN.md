# TAS论文投稿 - 具体行动计划

**当前状态**: 数据收集完毕，质量评估 ✅  
**目标**: SCI 4区论文发表  
**预计时间**: 2-3周 (取决于执行进度)  
**优先级**: 立即启动

---

## 🎯 第一阶段: 数据完善 (预计3-4天)

### Task 1.1: JIST01数据验证 [预计2小时]
**目标**: 验证TAS模型的泛化能力

**具体步骤**:
```bash
# 步骤1: 检查JIST01数据是否可用
ls -la /iridisfs/scratch/jc15u24/Code/JIST01/data/

# 步骤2: 加载JIST01数据
# 修改config.py中的数据路径
DATA_ROOT = "/iridisfs/scratch/jc15u24/Code/JIST01/data/"

# 步骤3: 运行improved_analysis_v4.py在JIST01上
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments/
python src/improved_analysis_v4.py --dataset JIST01 --output results/JIST01_validation/

# 步骤4: 生成交叉数据集对比表
# 预期输出: results/cross_dataset_summary.csv
```

**预期输出**:
- [ ] JIST01结果文件 (CSV格式)
- [ ] 跨数据集对比表
- [ ] generalization评估报告

**验收标准**:
- ✓ JIST01的NR-TAS CC > 0.15 (预期)
- ✓ 与TUD的趋势一致
- ✓ 统计显著性保持

---

### Task 1.2: 内容亚组分析 [预计1.5小时]

**目标**: 识别方法在不同场景的表现模式

**具体操作**:
```python
# 步骤1: 对40个内容进行分类
content_categories = {
    'Low_Complexity': ['dog', 'cycler_ice', ...],      # CC < 0.65
    'Medium_Complexity': ['walking_bear', ...],        # 0.65 < CC < 0.80
    'High_Complexity': ['kid_bucket', 'man_desert'],   # CC > 0.88
}

# 步骤2: 按类别计算汇总统计
for category, contents in content_categories.items():
    subset = results[results['content'].isin(contents)]
    print(f"{category}:")
    print(f"  CC: {subset['cc'].mean():.4f} ± {subset['cc'].std():.4f}")
    print(f"  Count: {len(subset)}")

# 步骤3: 执行Kruskal-Wallis H检验
from scipy.stats import kruskal
groups = [results[results['content'].isin(cat)]['cc'].values 
          for cat in content_categories.values()]
stat, p_value = kruskal(*groups)
print(f"H-stat: {stat:.4f}, p-value: {p_value:.4f}")
```

**预期输出表格**:
```
╔══════════════════╦════════════╦═══════╦═══════╦═══════╗
║ Complexity Level ║ CC Mean    ║ ±SD   ║ Count ║ Note  ║
╠══════════════════╬════════════╬═══════╬═══════╬═══════╣
║ Low (CC<0.65)    ║ 0.542      ║ 0.083 ║ 4     ║ 弱    ║
║ Medium (0.65-80) ║ 0.720      ║ 0.070 ║ 20    ║ 中等  ║
║ High (CC>0.88)   ║ 0.906      ║ 0.040 ║ 20    ║ 强    ║
╚══════════════════╩════════════╩═══════╩═══════╩═══════╝
```

**验收标准**:
- ✓ Kruskal-Wallis检验 p < 0.05
- ✓ 至少3个不同复杂度类别
- ✓ 每类至少4个样本

---

### Task 1.3: 参数敏感性分析 [预计1小时]

**目标**: 验证算法对超参数的鲁棒性

**关键超参数**:
```python
# 需要测试的参数
params_to_test = {
    'window_size': [3, 5, 7, 9, 11],           # 平滑窗口
    'threshold': [0.5, 0.6, 0.7, 0.8],         # 伪迹阈值
    'learning_rate': [0.001, 0.005, 0.01],     # 学习率
}

# 对每个参数执行网格搜索
# 预期: 生成sensitivity_analysis.csv
```

**预期输出**:
- [ ] 参数影响曲线 (3-4张)
- [ ] 最优参数组合推荐
- [ ] 鲁棒性评估报告

---

## 📊 第二阶段: 可视化与分析 (预计3-4天)

### Task 2.1: 生成关键对比图表 [预计2小时]

**必须生成的4张图**:

#### 图1: 方法对比柱状图 (带误差棒)
```python
import matplotlib.pyplot as plt
import numpy as np

methods = ['FreeLook', 'TAS', 'Mixture', 'Artifact']
cc_mean = [0.8487, 0.8103, 0.7822, 0.1139]
cc_std = [0.0647, 0.1067, 0.0870, 0.1469]

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(methods, cc_mean, yerr=cc_std, capsize=10, alpha=0.7)
ax.set_ylabel('Correlation Coefficient', fontsize=12)
ax.set_title('Artifact Suppression Methods Comparison', fontsize=14)
ax.set_ylim([0, 1])
ax.axhline(y=0.8103, color='r', linestyle='--', label='TAS performance')
plt.savefig('results/Fig1_method_comparison.png', dpi=300, bbox_inches='tight')
```

**输出**: `Fig1_method_comparison.png`

#### 图2: NR-TAS vs FR-TAS对比
```python
# 显示两种TAS变体的性能差异
# X轴: 内容 (40个)
# Y轴: CC值
# 两条线: NR-TAS, FR-TAS
```

**输出**: `Fig2_NR_vs_FR_comparison.png`

#### 图3: 内容相关性热力图
```python
# 热力图: 40个内容 × 多个指标 (CC, JSD, Stability)
# 色度编码表现好坏
```

**输出**: `Fig3_content_heatmap.png`

#### 图4: 压缩级别影响曲线
```python
# 线图: 压缩级别 (x轴) vs CC值 (y轴)
# 显示最优范围
```

**输出**: `Fig4_compression_level_curve.png`

**验收标准**:
- ✓ 分辨率 ≥ 300 dpi
- ✓ 包含统计信息 (误差棒、显著性标记)
- ✓ 清晰的图例和标签
- ✓ 科学出版规范格式

---

### Task 2.2: 示例眼动序列可视化 [预计1.5小时]

**目标**: 展示TAS的实际效果

**需要的可视化**:
```
行1: 原始眼动数据 (FreeLook)
行2: 检测的伪迹标记
行3: TAS去噪后的眼动
行4: Mixture方法对比

列: 3个代表性内容
  - 最佳场景 (kid_bucket)
  - 中等场景 (bird_bushes)
  - 最差场景 (dog)
```

**预期输出**: `Fig5_qualitative_examples.png` (3×4网格)

---

### Task 2.3: 统计检验结果表格 [预计30分钟]

**表格内容**:
```
方法对比              | 差异  | Cohen's d | t值   | p值 | 显著性
Artifact vs FL       | -0.735| -6.49     | -60.8 | *** | ✓
Mixture vs FL        | -0.067| -0.87     | -20.1 | *** | ✓
TAS vs FL            | -0.038| -0.44     | -6.08 | *** | ✓
NR-TAS vs FR-TAS     | +0.268| 高        | 高    | *** | ✓
```

**输出格式**: 高质量PNG表格图片 + CSV原始数据

---

## ✍️ 第三阶段: 论文框架搭建 (预计4-5天)

### Task 3.1: Methods部分 [预计2.5小时]

**需要描述**:
1. 数据集说明 (TUD + JIST01)
2. TAS模型细节
   - 架构设计
   - NR-TAS和FR-TAS的区别
   - 损失函数
3. 实验设计
   - 40折LOCO交叉验证
   - 评估指标 (CC, JSD)
   - 统计方法
4. 基线方法
   - FreeLook
   - Artifact suppression
   - Mixture model

**检查清单**:
- [ ] 符合投稿期刊要求
- [ ] 数学符号统一规范
- [ ] 算法步骤清晰明确
- [ ] 引用完整 (≥15篇)

---

### Task 3.2: Results部分 [预计2小时]

**必须包含的内容**:

#### RQ1: 任务切换影响
```
显示压缩级别对CC的影响，包括：
- 最优级别和对应CC值
- 性能变异范围
- 任务切换造成的扰动分析
```

#### RQ2: 预测性能
```
表格显示：
- 各方法的CC、JSD、置信区间
- 统计检验结果
- NR-TAS vs FR-TAS对比
```

#### RQ3: 实用价值
```
展示TAS在评分任务中的应用，包括：
- 与背景的相似度
- 与评分的对应关系
- 实际应用场景演示
```

**结构建议**:
```
Results
├── 整体性能对比 (表1 + 图1)
├── TAS方法详细分析 (表2 + 图2-3)
├── 内容相关性分析 (表3 + 图3)
├── 亚组分析 (表4)
├── 参数敏感性 (表5)
└── 定性示例 (图5)
```

---

### Task 3.3: Discussion部分 [预计2小时]

**关键讨论点**:

1. **为什么NR-TAS优于FR-TAS?**
   ```
   - 频域滤波破坏任务相关信息 ✓
   - 直接学习更适合非平稳信号 ✓
   - 实证对比的深度分析 ✓
   ```

2. **性能trade-off的合理性**
   ```
   - CC降低4.5% (0.8487 → 0.8103)
   - 但伪迹有效抑制 (CC+0.70)
   - 值得的权衡 ✓
   ```

3. **内容异质性的原因分析**
   ```
   - 视觉复杂度差异
   - 运动速度影响
   - 光照条件依赖
   - 提出自适应方案
   ```

4. **与相关工作的对比**
   ```
   - 与其他伪迹检测方法对比
   - 创新点阐述
   - 限制条件说明
   ```

5. **局限性和未来工作**
   ```
   限制:
   - 目前仅用TUD/JIST01数据
   - 参数的内容依赖性
   - 实时性还需改进
   
   未来:
   - 跨数据集的元学习
   - 在线适应性参数调整
   - 与其他模态的融合
   ```

---

### Task 3.4: Introduction + Conclusion [预计1.5小时]

#### Introduction结构:
```
背景 (2段)
  ↓
眼动追踪的应用和挑战 (1段)
  ↓
伪迹检测的现有方法评述 (2段)
  ↓
研究差距和机会 (1段)
  ↓
本研究的贡献和创新点 (1段)
  ↓
论文组织结构 (1段)
```

#### Conclusion结构:
```
主要发现总结 (1段)
  ↓
研究贡献和启示 (1段)
  ↓
实际应用价值 (1段)
  ↓
局限性坦诚说明 (1段)
  ↓
未来研究方向 (1段)
```

---

## 🔍 第四阶段: 审稿前准备 (预计2-3天)

### Task 4.1: 参考文献检查 [预计1小时]

**需要补充的领域**:
- [ ] 眼动追踪基础 (3-5篇)
- [ ] 伪迹检测方法 (5-8篇)
- [ ] 任务相关性研究 (3-5篇)
- [ ] 机器学习方法 (5-10篇)
- [ ] 应用案例 (5-8篇)

**总计**: 至少30-40篇参考文献

**格式检查**:
- [ ] 引用格式一致 (APA/IEEE)
- [ ] 所有in-text citations都有对应bibliography
- [ ] 文献年份合理 (近5年占比>50%)

---

### Task 4.2: 表格和图表最终化 [预计1.5小时]

**检查清单**:
- [ ] 所有表格有清晰标题和脚注
- [ ] 所有图片有详细图注
- [ ] 图表中的统计标记清晰 (*, **, ***)
- [ ] 颜色盲友好 (避免仅用红绿)
- [ ] 分辨率符合要求 (≥300 dpi for 期刊)

---

### Task 4.3: 格式和语言检查 [预计1小时]

**格式规范**:
- [ ] 页面设置 (字体、行距、边距)
- [ ] 标题层级统一
- [ ] 公式编号和引用正确
- [ ] 目录和交叉引用完整

**语言检查**:
- [ ] 语法和拼写检查 (Grammarly/检查)
- [ ] 学术用语规范
- [ ] 中英文混用检查 (如果有)
- [ ] 专业术语一致性

**工具推荐**:
```bash
# 拼写和语法
grammarly-cli check paper.docx

# Latex编译检查
pdflatex paper.tex
bibtex paper
pdflatex paper.tex (×2)
```

---

### Task 4.4: 投稿前核查表 [预计30分钟]

```
□ 论文长度控制在8-12页 (SCI 4区通常要求)
□ 摘要 (Abstract) ≤ 250 words
□ 包含 4-5 张主要图表
□ 包含 3-4 张统计表格
□ 所有数据有95% CI 或 error bars
□ p值都正确报告 (p<0.001 vs p=0.0001 vs p=0.013)
□ 样本量清晰说明 (N=160 或每个细胞的N值)
□ 没有重复的论述或数据
□ 致谢和利益冲突声明完整
□ 符合投稿期刊的投稿指南
□ 作者署名顺序确定
□ 对应作者信息清晰
□ 关键词 (5-8个) 精选
```

---

## 🎯 投稿期刊建议 (优先顺序)

### 第一选择: IEEE TNNLS (影响因子 3.8)
**适配度**: ⭐⭐⭐⭐⭐  
**优势**: 
- 接受眼动追踪研究
- 机器学习方法认可度高
- 审稿周期 4-6个月

**投稿要求**:
- 字数: 8,000-10,000
- 图表: 6-8张
- 参考文献: 35-50篇

### 第二选择: IEEE JBHI (影响因子 3.1)
**适配度**: ⭐⭐⭐⭐  
**优势**:
- 生物医学信息技术专业期刊
- 眼动应用研究偏好明显
- 审稿周期 3-4个月

### 第三选择: Pattern Recognition (影响因子 3.8)
**适配度**: ⭐⭐⭐  
**优势**:
- 模式识别顶级期刊
- 方法创新重视
- 但应用导向可能稍弱

---

## ⏰ 时间表总结

```
┌──────────────┬──────────────────────┬──────────────┐
│ 阶段         │ 主要任务             │ 预计工作量   │
├──────────────┼──────────────────────┼──────────────┤
│ 第一阶段     │ JIST01验证           │ 4-5小时      │
│ (3-4天)      │ 亚组分析             │              │
│              │ 参数敏感性           │              │
├──────────────┼──────────────────────┼──────────────┤
│ 第二阶段     │ 图表生成             │ 4-5小时      │
│ (3-4天)      │ 可视化优化           │              │
│              │ 统计表格             │              │
├──────────────┼──────────────────────┼──────────────┤
│ 第三阶段     │ Methods              │ 5-6小时      │
│ (4-5天)      │ Results              │              │
│              │ Discussion           │              │
│              │ Intro & Conclusion   │              │
├──────────────┼──────────────────────┼──────────────┤
│ 第四阶段     │ 文献检查             │ 3-4小时      │
│ (2-3天)      │ 格式检查             │              │
│              │ 语言润色             │              │
│              │ 投稿准备             │              │
├──────────────┼──────────────────────┼──────────────┤
│ 总计         │                      │ 16-20小时    │
│              │ 预计周期: 2-3周      │ (7-10天)     │
└──────────────┴──────────────────────┴──────────────┘
```

---

## 📅 建议执行日程

```
Week 1:
  Mon-Tue:  Task 1.1 & 1.2 (JIST01+亚组)     [4小时]
  Wed-Thu:  Task 1.3 (参数敏感性)             [1.5小时]
  Fri:      Task 2.1 & 2.2 (可视化生成)       [3.5小时]

Week 2:
  Mon-Tue:  Task 3.1 (Methods写作)            [2.5小时]
  Wed-Thu:  Task 3.2 (Results整理)            [2小时]
  Fri:      Task 3.3 & 3.4 (Discussion+Intro) [3.5小时]

Week 3:
  Mon-Tue:  Task 4.1 & 4.2 (文献+表格检查)    [2.5小时]
  Wed-Thu:  Task 4.3 & 4.4 (语言+核查)        [1.5小时]
  Fri:      最后准备和投稿                     [1小时]
```

---

## ✅ 就绪检查

启动前请确认:
- [ ] 所有数据文件完整无缺
- [ ] 代码环境可正常运行
- [ ] JIST01数据可访问
- [ ] 有充分的研究时间 (2-3周)
- [ ] 编写工具就绪 (Word/LaTeX)
- [ ] 文献管理工具配置好 (Zotero/Mendeley)

---

**准备就绪后，建议立即启动第一阶段！** 🚀

**联系方式**: jc15u24@soton.ac.uk  
**更新日期**: 2026-01-25
