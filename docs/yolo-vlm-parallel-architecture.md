# FabricEye YOLO + VLM 并行验布检测架构设计

> **版本**: v1.0  
> **日期**: 2026-03-07  
> **状态**: ✅ 已确认

---

## 1. 方案概述

将现有的纯 VLM 级联检测架构（Flash → Plus）升级为 **YOLO + VLM 并行检测** 架构。核心理念：

- **YOLO 本地模型（YOLOv11s）**：逐帧实时检测（ms 级），处理已学会的缺陷类型
- **VLM Flash**：采样检测（每 N 帧抽 1 帧），发现 YOLO 未学过的新缺陷
- **事后交叉核对**：一卷布走完后，批量比对 YOLO 和 VLM 的结果
- **VLM Plus 复检**：仅对 YOLO 漏检项进行精准复核
- **人工复核 → YOLO 训练闭环**：人工确认的新缺陷样本用于增量训练 YOLO

---

## 2. 系统架构

### 2.1 整体流程图

```
布料开始行进 ─────────────────────────── 布料走完
│                                        │
│  [并行运行]                             │
│  ├─ YOLO: 逐帧检测 ─→ 结果缓存        │
│  └─ VLM Flash: 采样检测 ─→ 结果缓存   │
│                                        │
                                         ▼
                                 交叉核对 (~秒级)
                                         │
                                 ┌───────┴───────┐
                                 │               │
                           一致 & YOLO    VLM 独有发现
                           独有 → 入库    → Plus 复检
                                                 │
                                          人工复核 → 训练
                                                 │
                                           生成最终报告
```

### 2.2 详细流程说明

#### 检测阶段（布料行进中）
1. 视频帧流同时分发给 YOLO Worker 和 VLM Sampler
2. YOLO Worker 逐帧实时推理（~5-10ms/帧），结果写入 YOLO 结果缓存
3. VLM Sampler 每 N 帧采样 1 帧，调用 VLM Flash API（~1-3s/帧），结果写入 VLM 结果缓存
4. 检测过程中 YOLO 结果可实时显示给用户

#### 核对阶段（布料走完后，秒级完成）
1. 交叉核对引擎将 YOLO 和 VLM 结果按 **时间窗口 + IOU** 匹配
2. **双方一致** → 确认缺陷，直接入库
3. **仅 YOLO 发现** → 信任 YOLO 结果，直接入库
4. **仅 VLM 发现（YOLO 漏检）** → 送 VLM Plus 复检

#### 复检阶段
1. VLM Plus 对 YOLO 漏检项进行精准分析
2. 确认为缺陷 → 送人工复核队列
3. 排除 → 标记为 VLM 误报

#### 训练闭环
1. **仅人工确认的缺陷** 才能进入训练数据集
2. 训练数据推送到独立训练主机/云端
3. 增量训练完成后，新模型回传部署到检测主机

---

## 3. YOLO 模型选型

### 3.1 选定版本：YOLOv11s (Ultralytics)

| 属性 | 值 |
|---|---|
| 版本 | YOLOv11s (small) |
| 参数量 | ~9.4M |
| 推理速度 | ~5ms/帧 (640px, GPU) |
| 选型理由 | 小目标检测优于 YOLOv8，社区成熟，增量训练支持完善 |

### 3.2 缺陷类别映射（与 VLM 分类对齐）

```python
DEFECT_CLASSES = {
    0: "hole",           # 破洞
    1: "stain",          # 污渍
    2: "color_variance", # 色差
    3: "warp_break",     # 断经
    4: "weft_break",     # 断纬
    5: "foreign_matter", # 异物
    6: "crease",         # 折痕
    7: "snag",           # 抽丝
}
```

### 3.3 冷启动

项目初期使用公开面料缺陷数据集 + 小批量自标注数据进行预训练，后续通过人工复核闭环持续积累训练样本。

---

## 4. 模块设计

### 4.1 新增模块

```
backend/app/services/
├── cascade/                    # 保留，纯 VLM 模式后备
├── parallel/                   # 🆕 并行检测引擎
│   ├── __init__.py
│   ├── engine.py               # ParallelEngine 主控制器
│   ├── yolo_worker.py          # YOLO 检测线程
│   ├── vlm_sampler.py          # VLM 采样检测线程
│   ├── reconciler.py           # 交叉核对引擎
│   ├── plus_reviewer.py        # Plus 复检器
│   ├── result_store.py         # 检测结果缓存
│   └── types.py                # 数据类型定义
├── yolo/                       # 🆕 YOLO 模型管理
│   ├── detector.py             # YOLO 推理封装
│   ├── model_manager.py        # 模型版本管理
│   └── models/                 # 模型权重目录
├── training/                   # 🆕 训练数据管理
│   ├── sample_collector.py     # 样本收集器
│   ├── dataset_manager.py      # 数据集管理
│   └── training_api.py         # 训练任务 API
└── ai_analyzer.py              # 保留复用
```

### 4.2 核心类设计

#### ParallelEngine（主控制器）
- `start()` — 启动 YOLO Worker + VLM Sampler 并行运行
- `stop_and_reconcile()` — 布料走完 → 停止 → 核对 → Plus 复检 → 生成报告

#### YoloWorker（YOLO 检测线程）
- 从帧缓冲区逐帧取出，调用 YOLOv11s 推理
- 结果写入 `ResultStore`（帧号、时间戳、bbox、类别、置信度）

#### VlmSampler（VLM 采样线程）
- 每 N 帧抽取 1 帧，调用 VLM Flash API
- 结果写入 `ResultStore`

#### Reconciler（交叉核对引擎）
- 按时间窗口分组 YOLO 和 VLM 结果
- 用 IOU 阈值匹配同一缺陷
- 输出：matched（双方一致）、yolo_only、vlm_only

#### PlusReviewer（Plus 复检器）
- 对 vlm_only 项调用 VLM Plus API 精准分析
- 确认 → 人工复核队列，否认 → 排除

### 4.3 交叉核对算法

匹配维度：
1. **时间窗口**：YOLO 帧时间戳与 VLM 采样帧时间戳差值 ≤ `RECONCILE_TIME_WINDOW`（默认 2 秒）
2. **空间匹配**：同一时间窗口内，bbox 的 IOU ≥ `RECONCILE_IOU_THRESHOLD`（默认 0.3）

### 4.4 VLM 采样策略

| 布料行进速度 | 推荐采样间隔 | VLM 调用频率 |
|---|---|---|
| 慢速 (≤10m/min) | 每 60 帧（2秒） | ~0.5 次/秒 |
| 中速 (10-30m/min) | 每 30 帧（1秒） | ~1 次/秒 |
| 快速 (>30m/min) | 每 15 帧（0.5秒） | ~2 次/秒 |

---

## 5. 配置参数

| 变量名 | 默认值 | 说明 |
|---|---|---|
| `AI_PROVIDER` | `parallel` | 设为 `parallel` 启用并行检测 |
| `YOLO_MODEL_PATH` | `models/yolov11s_fabric.pt` | YOLO 模型路径 |
| `YOLO_CONFIDENCE` | `0.5` | YOLO 检测置信度阈值 |
| `VLM_SAMPLE_INTERVAL` | `30` | VLM 采样间隔（帧数） |
| `RECONCILE_IOU_THRESHOLD` | `0.3` | 核对匹配 IOU 阈值 |
| `RECONCILE_TIME_WINDOW` | `2.0` | 核对时间窗口（秒） |
| `TRAINING_API_URL` | — | 训练服务器地址 |
| `TRAINING_MIN_SAMPLES` | `50` | 触发训练最少样本数 |

---

## 6. 与现有架构的关系

- `cascade/` 保留，通过 `AI_PROVIDER=cascade` 可切回纯 VLM 模式
- `ai_analyzer.py` 完全复用，VLM 调用接口不变
- `video_capture.py` 完全复用，帧采集不变
- 前端 Monitor.vue 需扩展支持 YOLO + VLM 双路状态显示

---

## 7. 前端需求

### 需要新增/修改的页面

1. **人工复核功能** — 展示待复核缺陷列表，支持确认/否决/修改分类
2. **交叉核对报告** — 展示一致/YOLO独有/VLM独有/Plus复检结果
3. **模型管理**（设置页扩展） — YOLO 模型版本、训练数据统计、更新历史

---

## 8. 开发阶段规划

| 阶段 | 内容 | 依赖 |
|---|---|---|
| **一** | YOLO 集成 + 并行检测框架 (`ParallelEngine`, `YoloWorker`, `VlmSampler`) | YOLOv11s 环境 |
| **二** | 交叉核对 + Plus 复检 (`Reconciler`, `PlusReviewer`) | 阶段一完成 |
| **三** | 人工复核 + 训练数据闭环 (前端 UI + `training/` 模块) | 阶段二完成 |
| **四** | 前端整合 + 优化 (Monitor 适配、报告页、模型管理) | 阶段三完成 |

---

*文档版本：v1.0*  
*确认日期：2026-03-07*
