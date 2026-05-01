# CGI 2026 / TVC Journal-Track：关键硬伤修复 + 跨数据集泛化实验设计（可执行版）

> 目标：把当前论文从“单一数据集 + 启发式融合”提升到 **期刊通道可接受** 的证据强度：  
> 1) **强基线**、2) **严格无泄露的调参**、3) **跨数据集/跨失真类型泛化**、4) **机制验证（artifact map 真实性）**、5) **指标与统计规范化**、6) **图表与数值一致性可复核**。  
> 你目前可用数据集：  
> - **TUD Image Quality Database: Eye-Tracking Release 2**（简称 *R2*）  
> - **TUD Image Quality Database: Eye-Tracking Release 1**（简称 *R1*）  
> - **TUD Image Quality Database: Interactions**（简称 *INT*）

---

## 1. 需要修复的“硬伤清单”与对应实验模块

### W1. 核心方法“启发式融合”新颖性不足
**解决策略**：补齐“可学习映射”与“强非学习基线”，证明你的方法是 **在部署约束下的 Pareto 最优解**（或至少在稳定性约束下优于可学习基线/简单规则）。

**对应实验模块**：
- **B1：强基线对比（Learning / Non-learning / Oracle）**
- **B2：部署可行性设置（有/无 free-viewing prior）**

---

### W2. 基线不足且比较不公平
**解决策略**：构建 **统一输入信息量** 的基线族，并严格区分：
- **Setting-A（部署现实）**：仅图像可用（没有真实 free-viewing FDM）
- **Setting-B（半现实）**：可用预测的 free-viewing prior（由外部模型得到）
- **Setting-C（上界/Oracle）**：可用真实 free-viewing FDM（论文当前默认）

**对应实验模块**：
- **S1：三类设置对照（A/B/C）+ 一致协议**
- **B1：每个设置下至少 3–4 个强基线**

---

### W3. 参数选择缺乏依据；CC vs JSD 目标不一致
**解决策略**：明确主目标函数并做 **nested（内层）交叉验证** 选参，避免泄露；同时报告多目标权衡曲线（CC–JSD Pareto）。

**对应实验模块**：
- **H1：主目标定义与多目标报告**
- **P1：Nested LOCO 选参 + 稳健性评估**
- **F1：CC–JSD Pareto 曲线（每个数据集/失真类型）**

---

### W4. NR artifact map 可能“边缘/纹理响应”，机制存疑
**解决策略**：用 FR artifact proxy 做参照（当参考可用时），并用失真强度/类型做外部验证，证明你的 A 不是纯 edge-map。

**对应实验模块**：
- **M1：Artifact map 真实性验证（FR vs NR 一致性 + 与失真强度相关性）**
- **M2：Gaze shift 与 artifact map 的关系验证（解释性分析）**

---

### W5. 图表/数值不一致（如单个 case CC 与均值冲突）
**解决策略**：建立 **可复核的结果生成管线**：每个图对应可追溯的样本索引、指标计算脚本、导出日志；并在实验设计中要求“case 选择规则”固定且可重现。

**对应实验模块**：
- **R0：可复核结果生成协议（Logging + 固定 case 规则）**
- **R1：Case study 选择规则（best/median/worst 的明确定义）**

---

### W6. 指标不够标准化、统计报告不完整
**解决策略**：补充 saliency 社区常用指标并加入可靠性上界（inter-observer consistency/ceiling），提供显著性检验+效应量+多重比较校正。

**对应实验模块**：
- **E1：指标套件（CC/JSD + NSS/SIM/KL/AUC）**
- **E2：Ceiling/一致性上界（split-half / inter-subject）**
- **T1：统计检验（paired + effect size + Holm-Bonferroni）**

---

## 2. 数据集与统一预处理（保证跨数据集可比）

### 2.1 数据集角色分工（推荐）
- **R2（主训练/主分析）**：用于方法开发、选参、消融与主表结果
- **R1（跨数据集泛化-1）**：zero-shot 测试（不重新选参），验证对“不同采集/被试/流程”的稳健性
- **INT（跨数据集泛化-2 + 跨失真类型）**：重点验证 **跨失真类型**（如果 INT 包含多类型失真）与更复杂交互场景下的泛化

> 注：若 INT/R1 的任务标签与 R2 不完全一致（例如没有 quality-scoring gaze），则按 “可用任务”进行子实验：  
> - 有 Q/F 双任务：做完整 TAS 迁移  
> - 仅有 F：用于 Setting-B 的 prior 评估、或用于稳定性上界/一致性分析

### 2.2 统一预处理（必须在三数据集保持一致）
- **空间对齐**：统一到同一分辨率（建议保留原比例，短边缩放到固定值，如 512 或 768；记录缩放因子）
- **FDM 生成**：固定高斯核参数 `sigma`（以视觉角为依据优先；若无法统一视觉角，至少统一像素 sigma 并报告敏感性）
- **归一化**：FDM 做 `sum-to-1`（概率分布），并保留未归一化版本用于 NSS
- **mask**：如有无效区域/边界，统一处理（裁剪或 mask）
- **JPEG/失真强度索引**：必须统一定义（连续 or 离散），并在所有图表保持一致

---

## 3. 实验设置总览（你最终要交付的实验矩阵）

### 3.1 三类部署设置（所有数据集统一）
- **Setting-A（Image-only）**：输入仅图像 `I`（最现实）
- **Setting-B（Predicted prior）**：输入 `I` + 预测 free-viewing prior `\tilde P^F`（现实可行）
- **Setting-C（Oracle prior）**：输入 `I` + 真实 free-viewing `P^F`（你当前方法的默认假设；作为上界/剖析）

> 论文主张可以是：  
> - **主结果**用 Setting-B（更像部署）  
> - Setting-C 作为“机制分析与上界”  
> - Setting-A 作为“若无 prior 时的退化表现”与对审稿质疑的回应

### 3.2 任务定义（目标输出）
- 目标：预测 `P^Q`（quality-scoring gaze distribution）  
- 额外：可预测 `P^F`（若 Setting-A 需要）

---

## 4. Baselines 设计（必须强，且输入信息量公平）

### 4.1 Non-learning baselines（必须有）
在 Setting-C（Oracle）下：
1. **Prior-only**：`\hat P = P^F`
2. **Artifact-only**：`\hat P = norm(A)`
3. **Fixed-mixture**：`\hat P = norm(0.5 P^F + 0.5 A)`
4. **Your SC-TAS**：带稳定性约束的融合（主方法）

在 Setting-B（Predicted prior）下：
- 将 `P^F` 替换为 `\tilde P^F`，重复上述 4 个

在 Setting-A（Image-only）下：
- 使用 `A`、以及任意 image-based saliency baseline（见 4.2）

### 4.2 Learning baselines（至少 2 个，且“轻量可复现”）
> 目的：回应“启发式融合不足以支撑期刊贡献”的质疑。  
> 推荐两级复杂度：一个极简（可解释），一个轻量网络（强基线）。

**LB1：Ridge / ElasticNet 回归（可解释强基线）**  
- 输入特征：`[P^F, A]`（Setting-C）或 `[\tilde P^F, A]`（Setting-B）  
- 输出：`P^Q`（逐像素回归或在低维 basis 上回归，例如 DCT/低频基）  
- 正则：L2 / ElasticNet  
- 优点：公平、快速、强且可解释

**LB2：小型 CNN / U-Net-lite（轻量强基线）**  
- 输入通道：`I` + prior（若 Setting-B/C）+ `A`  
- 输出：`P^Q`（概率图）  
- 损失：`KL(P^Q || \hat P)` + `λ * (1-CC)`（可选）  
- 控制规模：参数量 < 5M，训练策略与超参公开

**LB3（可选加分）：Conditional diffusion / transformer 不建议**  
- 期刊审稿会问训练成本与公平性，除非你能非常清楚地定位贡献

### 4.3 Oracle upper-bound（可选但建议）
**UB：Cross-subject ceiling**  
- 训练/预测不重要，用于“这个任务的可达到上界是多少”  
- 计算：将被试分两半生成 FDM，计算 CC/NSS/SIM 的一致性 → 作为 ceiling  
- 你的方法如果接近 ceiling，才有说服力；如果远低于 ceiling，就要讨论原因

---

## 5. 关键：无泄露的选参与评估协议（Nested LOCO）

### 5.1 R2 内：主实验（Nested LOCO）
对每个 held-out content `c`：
- **Outer loop**：留出 `c` 的所有失真等级作为测试
- **Inner loop**：在剩余 `C-1` 个 content 上做选参  
  - 选参目标必须明确：  
    - 方案 1（推荐）：最小化 `JSD(P^Q, \hat P)`，并以 `CC(\hat P, P^F) ≥ τ` 为硬约束  
    - 方案 2：多目标：最小化 `JSD` 同时最大化 `CC`，输出 Pareto 并选 knee-point  
- 记录：每个 `c` 的最优 `(α, β, τ)`（或共享参数），并报告分布（均值±std）

> 必须保证：测试 content `c` 从未参与参数选择与阈值搜索。

### 5.2 Cross-dataset：零样本泛化（最重要）
- **Train/Select on R2**：在 R2 做完 nested LOCO 得到最终固定超参（或全局超参）
- **Test on R1（zero-shot）**：不改任何超参、不再调 `τ/β`  
- **Test on INT（zero-shot）**：同上  
- 报告：与 R2 相同的指标表 + 统计显著性 + 失败案例分析

> 这是最能打动 CGI/TVC 审稿人的部分：证明你的方法不是“对 R2 的调参产物”。

### 5.3 Limited-shot adaptation（可选加分）
如果 zero-shot 掉得太多，可增加：
- 在目标数据集（R1 或 INT）仅用 **K 个 content** 做轻量校准（例如只校准 `β` 或 `τ`）
- 报告性能随 K 增长的曲线（K=0, 5, 10, 20）
- 强调“极少量校准即可恢复”，这会增强部署可行性叙事

---

## 6. 泛化实验设计：你要做的“对照组”与“结论输出”

### 6.1 跨数据集泛化（R2 → R1 / INT）
**核心问题**：你的 stability constraint 是否真正带来可迁移性？

实验对照：
- Prior-only vs Fixed-mixture vs SC-TAS vs LB1 vs LB2  
- 在 Setting-B 与 Setting-C 均做（Setting-B 更关键）

输出：
- **Table-G1**：R2/R1/INT 三数据集上的主指标（均值±CI）
- **Fig-G1**：跨数据集性能降幅条形图（ΔJSD, ΔCC）
- **Case-G1**：每个数据集 3 个固定规则 case（best/median/worst），可复现

### 6.2 跨失真类型泛化（若 INT 含多失真）
**核心问题**：SC-TAS 是否只是 JPEG 特例？

做两种训练/选参：
- **JPEG-only 选参**（在 R2 上只用 JPEG 条件）
- **Multi-distortion 选参**（在 INT 或 R2+INT 上混合）

测试：
- 在 INT 的非 JPEG 类型（blur/noise 等）上测试  
- 输出：
  - **Table-G2**：按失真类型分组的结果  
  - **Fig-G2**：每类失真下 CC–JSD Pareto 曲线对比  
  - 讨论：哪些失真更容易“artifact-driven drift”，stability constraint 是否仍有效

---

## 7. 机制验证：artifact map A 的“伪影性”与可解释性（必须补）

### 7.1 FR vs NR 一致性（当参考可用时）
在有 reference 的样本上：
- 计算 `A_FR`（基于 reference residual / ringing/blocking proxy）
- 计算 `A_NR`（你当前 NR：block boundary + HF residual）
- **验证 1：相关性**  
  - `corr( A_NR, A_FR )`（像素级 Spearman 或 patch-level）  
- **验证 2：与失真强度相关**  
  - `mean(A_NR)` vs compression level / quality index（单调性检验）
- 输出：
  - **Fig-M1**：A_NR 与 A_FR 的可视化 + scatter  
  - **Table-M1**：相关性统计（均值±CI）

> 目的：证明 A_NR 不是纯 edge-map，而是随失真增强而增强，并与 FR proxy 一致。

### 7.2 Gaze shift 与 A 的关系（解释你的“任务漂移”叙事）
- 定义 gaze shift：`Δ = P^Q - P^F`（或其 magnitude / KL contribution map）
- 验证：
  - `corr(Δ+, A)`：正向漂移是否集中在伪影区域
  - 对比不同失真强度下的相关性变化
- 输出：
  - **Fig-M2**：Δ map 与 A map 的对照
  - **Table-M2**：相关性随强度变化的统计

---

## 8. 指标、统计检验与报告规范（按期刊口径写）

### 8.1 指标套件（建议最终保留 4–6 个）
- **分布一致性**：JSD（主）、KL（可选）
- **相关性**：CC（主）
- **saliency 常用**：NSS、SIM  
- **可选**：AUC-Judd（若 fixation points 可用）

> 注意：  
> - 对概率图用 JSD/KL/SIM  
> - 对 fixation-based 评价用 NSS/AUC  
> - 所有指标的实现必须固定并公开（至少在补充材料）

### 8.2 置信区间与显著性
- 对每个指标报告：`mean ± 95% CI`（bootstrap over contents）
- 方法间比较：paired test over contents  
  - 正态：paired t-test；非正态：Wilcoxon signed-rank  
- 多重比较：Holm-Bonferroni
- 效应量：Cohen’s d 或 Cliff’s delta

### 8.3 Ceiling（强烈建议）
- split-half inter-observer consistency（每 dataset、每 task、每 distortion）  
- 报告：你的方法与 ceiling 的差距（gap）

---

## 9. 消融实验（证明每个设计都“必要”）

### 9.1 SC-TAS 组件消融
- 去掉 stability constraint（仅融合）
- 去掉 A（仅 prior）
- 去掉 prior（仅 A）
- τ 扫描（0.70–0.95）
- β 扫描（0–1）

输出：
- **Fig-A1**：CC–JSD Pareto 面（或曲线）
- **Table-A1**：关键消融表（至少在 R2 与 INT 各一份）

### 9.2 Prior 来源消融（回应部署质疑）
在 Setting-B：
- 使用不同的 prior 生成方式（例如不同 free-viewing saliency predictor 或不同训练集得到的 prior）
- 输出：SC-TAS 对 prior 误差的鲁棒性曲线（prior-accuracy vs TAS performance）

---

## 10. Case Study：固定、可复现的选例规则（修复图表不一致）

### 10.1 固定规则（必须写进论文/补充材料）
对每个数据集分别选 3 个 content：
- **best**：在主指标（JSD）上提升最大（ΔJSD 最大）
- **median**：ΔJSD 中位数
- **worst**：ΔJSD 最小（或为负）

并固定失真等级：
- 选最高失真等级 + 中等失真等级各一组（避免只挑最极端）

输出：
- 每个 case 同时展示：`I`, `P^F`, `P^Q`, `A`, `\hat P`（方法与基线）
- 旁边标注同一套指标数值（JSD/CC/NSS/SIM）

### 10.2 结果生成与一致性检查（建议）
- 每张图导出时保存：
  - dataset、content id、distortion level、随机种子、指标 JSON
- 自动脚本检查：
  - Fig 中显示的数值是否与表格一致（unit test）

---

## 11. 你最终论文需要呈现的“最小完整证据包”（建议目录）

1. **Main Table（R2）**：Setting-B 为主，附 Setting-C  
2. **Cross-dataset Table（R1 / INT）**：zero-shot +（可选）limited-shot  
3. **Cross-distortion（若 INT 多失真）**：按失真类型分组  
4. **Learning baselines**：LB1 + LB2（必须出现在主表或附录主图）  
5. **Mechanism validation（A 的真实性）**：FR vs NR + 与失真强度单调性  
6. **Ceiling + 统计显著性**：CI、p-value、effect size、校正  
7. **Ablation**：stability constraint 必要性 + 参数敏感性（Pareto）  
8. **Reproducible case studies**：固定规则 + 全链路一致性

---

## 12. 实施顺序（最省时间的执行路线）

**Step 1（必做）**：R2 上补齐强基线（LB1/LB2）+ Nested LOCO 选参  
**Step 2（必做）**：R2 → R1 / INT 的 zero-shot cross-dataset（Setting-B/C）  
**Step 3（必做）**：机制验证（A_NR vs A_FR + 与失真强度相关）  
**Step 4（加分）**：跨失真类型（INT）+ limited-shot adaptation  
**Step 5（加分）**：ceiling + prior 鲁棒性消融

---
