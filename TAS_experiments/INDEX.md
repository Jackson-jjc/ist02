# 📑 TAS 实验框架 - 完整目录索引

**项目位置**：`/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments/`

---

## 🎯 快速导航

### 👤 我是新用户，应该看什么？
→ **第一步**：[QUICK_START.md](QUICK_START.md) - 5分钟快速上手  
→ **第二步**：[ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) - 了解所有依赖模块

### 🔧 我想安装和配置
→ [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) - 完整的模块清单和安装方法  
→ [DEPENDENCIES.md](DEPENDENCIES.md) - 依赖详解和故障排除

### 📚 我想了解项目结构
→ [FILE_MANIFEST.md](FILE_MANIFEST.md) - 文件结构和模块说明  
→ [MODULES_SUMMARY.md](MODULES_SUMMARY.md) - 模块功能一览表

### 🚀 我想运行实验
→ [QUICK_START.md](QUICK_START.md) - 运行步骤  
→ [README.md](README.md) - 完整的项目说明

### ✅ 我想检查项目完成度
→ [PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md) - 完成清单

---

## 📋 所有文档列表

### 📘 核心文档（必读）

| 文件 | 大小 | 用途 | 适合人群 |
|------|------|------|---------|
| [QUICK_START.md](QUICK_START.md) | 9.0 KB | 快速启动指南 | **首次使用** |
| [README.md](README.md) | 7.0 KB | 完整项目说明 | 需要详细信息 |
| [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) | 9.1 KB | **所有模块清单** | **想装依赖** |

### 📗 参考文档（进阶）

| 文件 | 大小 | 用途 | 适合人群 |
|------|------|------|---------|
| [DEPENDENCIES.md](DEPENDENCIES.md) | 5.7 KB | 依赖详解 | 有安装问题 |
| [FILE_MANIFEST.md](FILE_MANIFEST.md) | 9.5 KB | 文件结构说明 | 想了解架构 |
| [MODULES_SUMMARY.md](MODULES_SUMMARY.md) | 8.0 KB | 模块功能表 | 想快速查询 |
| [PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md) | 12 KB | 项目完成清单 | 想验证完成度 |

### 📄 配置文件

| 文件 | 用途 |
|------|------|
| [requirements.txt](requirements.txt) | pip依赖列表 |

### 🚀 可执行脚本

| 文件 | 用途 | 执行时间 |
|------|------|--------|
| [validate_setup.py](validate_setup.py) | 验证环境和数据 | 2 分钟 |
| [run_all_experiments.py](run_all_experiments.py) | 运行所有实验 | 3-5 小时 |
| [submit_experiments.slurm](submit_experiments.slurm) | SLURM提交脚本 | 后台运行 |

---

## 🎯 快速命令参考

### 安装依赖
```bash
cd /iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments
pip install -r requirements.txt
```

### 验证环境
```bash
python validate_setup.py
```

### 运行实验（本地）
```bash
python run_all_experiments.py
```

### 提交到SLURM
```bash
sbatch submit_experiments.slurm
```

### 查看结果
```bash
cat results/RESULTS_SUMMARY.txt
head results/rq2_prediction_fr_results.csv
ls results/fig_*.png
```

---

## 📊 项目统计

### 文件统计
- 📘 文档文件：7 个（共 50+ KB）
- 🐍 Python文件：10 个（共 100+ KB）
- ⚙️ 配置文件：1 个
- 📊 结果目录：会自动生成

### 代码统计
- 总代码行数：2260+ 行
- 文档行数：1170+ 行
- 注释行数：390+ 行
- 核心模块数：9 个

---

## 🎓 学习路径

### 第1天：快速上手（30分钟）
1. 阅读 [QUICK_START.md](QUICK_START.md)
2. 运行 `python validate_setup.py`
3. 理解项目结构

### 第2天：安装和验证（1小时）
1. 查看 [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md)
2. 安装所有依赖：`pip install -r requirements.txt`
3. 验证安装成功

### 第3天：运行实验（5小时）
1. 运行主脚本：`python run_all_experiments.py`
2. 查看 [README.md](README.md) 了解算法
3. 等待结果完成

### 第4天及以后：深入理解（可选）
1. 查看 [FILE_MANIFEST.md](FILE_MANIFEST.md) 了解架构
2. 查看 [MODULES_SUMMARY.md](MODULES_SUMMARY.md) 了解模块
3. 阅读源代码注释
4. 修改配置进行高级使用

---

## 🔧 按用途快速查找

### 🟢 我想...

#### 快速开始
- [QUICK_START.md](QUICK_START.md) - ⭐ **从这里开始**

#### 安装依赖
- [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) - 完整模块清单
- [requirements.txt](requirements.txt) - pip配置

#### 解决问题
- [DEPENDENCIES.md](DEPENDENCIES.md) - 故障排除
- [validate_setup.py](validate_setup.py) - 自动诊断

#### 了解架构
- [FILE_MANIFEST.md](FILE_MANIFEST.md) - 文件和模块
- [MODULES_SUMMARY.md](MODULES_SUMMARY.md) - 功能一览

#### 验证完成度
- [PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md) - 项目清单

#### 获取详细信息
- [README.md](README.md) - 完整说明
- src/ 目录中的代码 - 源代码

---

## 📈 文档优先级

### 🔴 最优先（必读）
1. [QUICK_START.md](QUICK_START.md) - 快速启动
2. [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) - 模块清单

### 🟡 次优先（根据需要）
3. [DEPENDENCIES.md](DEPENDENCIES.md) - 安装问题
4. [validate_setup.py](validate_setup.py) - 环境验证

### 🟢 进阶（可选）
5. [README.md](README.md) - 详细说明
6. [FILE_MANIFEST.md](FILE_MANIFEST.md) - 架构说明
7. [MODULES_SUMMARY.md](MODULES_SUMMARY.md) - 功能查询
8. [PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md) - 完成清单

---

## 💡 常见问题快速查找

| 问题 | 查看文件 |
|------|---------|
| 如何安装依赖？ | [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) |
| 安装失败怎么办？ | [DEPENDENCIES.md](DEPENDENCIES.md) |
| 项目有哪些文件？ | [FILE_MANIFEST.md](FILE_MANIFEST.md) |
| 各模块是干什么的？ | [MODULES_SUMMARY.md](MODULES_SUMMARY.md) |
| 如何运行实验？ | [QUICK_START.md](QUICK_START.md) |
| 项目完成度如何？ | [PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md) |
| 需要哪些Python版本？ | [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) |
| 实验需要多久？ | [QUICK_START.md](QUICK_START.md) |

---

## 🎯 三步快速开始

### ✅ 第1步（5分钟）：阅读快速指南
```bash
cat QUICK_START.md
```

### ✅ 第2步（10分钟）：安装依赖
```bash
pip install -r requirements.txt
python validate_setup.py
```

### ✅ 第3步（3-5小时）：运行实验
```bash
python run_all_experiments.py
```

---

## 📞 获取帮助

### 1️⃣ 有一般问题
→ 查看 [QUICK_START.md](QUICK_START.md)

### 2️⃣ 有安装问题
→ 查看 [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) 或 [DEPENDENCIES.md](DEPENDENCIES.md)

### 3️⃣ 想了解项目结构
→ 查看 [FILE_MANIFEST.md](FILE_MANIFEST.md) 或 [MODULES_SUMMARY.md](MODULES_SUMMARY.md)

### 4️⃣ 想了解实验细节
→ 查看 [README.md](README.md)

### 5️⃣ 想验证安装
→ 运行 `python validate_setup.py`

### 6️⃣ 遇到错误
→ 查看 [DEPENDENCIES.md](DEPENDENCIES.md) 的"常见问题"部分

---

## 📚 文档内容速览

### [QUICK_START.md](QUICK_START.md)
- 依赖清单
- 三步启动
- 实验内容
- 快速命令
- 常见问题
- 预期结果

### [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) ⭐ **完整模块清单**
- 6个必需模块详表
- 安装命令
- 故障排除
- 模块使用位置
- 依赖关系

### [README.md](README.md)
- 项目概述
- 数据集说明
- 快速开始
- 实验设计
- 算法说明
- 参数配置
- 参考文献

### [DEPENDENCIES.md](DEPENDENCIES.md)
- 所有模块版本
- 使用位置
- 安装方法
- 故障排除
- 环境设置

### [FILE_MANIFEST.md](FILE_MANIFEST.md)
- 项目文件树
- 模块功能说明
- 执行流程
- 数据流图
- 文件大小估计

### [MODULES_SUMMARY.md](MODULES_SUMMARY.md)
- 模块功能表
- 模块用途
- 核心算法
- 实验流程图

### [PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md)
- 完成度统计
- 功能列表
- 项目规模
- 创新特点
- 质量保证

---

## 🎯 按角色查找文档

### 👨‍💼 项目管理者
- [PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md) - 查看完成度
- [README.md](README.md) - 了解项目

### 👨‍💻 开发者
- [FILE_MANIFEST.md](FILE_MANIFEST.md) - 文件和架构
- [MODULES_SUMMARY.md](MODULES_SUMMARY.md) - 模块功能
- src/ 目录 - 源代码

### 👨‍🔬 研究人员
- [README.md](README.md) - 算法和方法
- [QUICK_START.md](QUICK_START.md) - 运行步骤

### 👨‍💼 运维人员
- [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) - 依赖安装
- [DEPENDENCIES.md](DEPENDENCIES.md) - 故障排除
- [submit_experiments.slurm](submit_experiments.slurm) - SLURM配置

---

## ✨ 推荐阅读顺序

```
第1次使用：
QUICK_START.md → ALL_MODULES_LIST.md → validate_setup.py

第2次使用：
QUICK_START.md → run_all_experiments.py → results/

深入学习：
README.md → FILE_MANIFEST.md → MODULES_SUMMARY.md → src/

问题排查：
DEPENDENCIES.md → validate_setup.py → logs/
```

---

## 📍 所有文件位置

```
/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments/
├── 📘 文档 (6 个)
│   ├── README.md
│   ├── QUICK_START.md ⭐
│   ├── ALL_MODULES_LIST.md ⭐
│   ├── DEPENDENCIES.md
│   ├── FILE_MANIFEST.md
│   ├── MODULES_SUMMARY.md
│   └── PROJECT_COMPLETION_CHECKLIST.md
│
├── 🔧 脚本 (3 个)
│   ├── validate_setup.py
│   ├── run_all_experiments.py
│   └── submit_experiments.slurm
│
├── ⚙️ 配置 (1 个)
│   └── requirements.txt
│
├── src/ 源代码
│   ├── config.py
│   ├── data_loader.py
│   ├── artifact_maps.py
│   ├── tas_model.py
│   ├── metrics.py
│   ├── exp_rq1_task_shift.py
│   ├── exp_rq2_prediction.py
│   ├── exp_rq3_practical.py
│   └── visualizer.py
│
├── results/ (运行后生成)
└── logs/ (运行后生成)
```

---

## 🎉 你已经找到了完整的文档！

**建议的下一步**：
1. 阅读 [QUICK_START.md](QUICK_START.md) (5分钟)
2. 查看 [ALL_MODULES_LIST.md](ALL_MODULES_LIST.md) (3分钟)
3. 运行 `pip install -r requirements.txt` (10分钟)
4. 运行 `python validate_setup.py` (2分钟)
5. 执行 `python run_all_experiments.py` (3-5小时)

---

**最后更新**：2026年1月16日  
**文档版本**：1.0  
**项目状态**：✅ 完全就绪
