# FabricEye - AI 智能验布系统 V2.0

> **面向小微面料商的零门槛、高性能 AI 实时验布解决方案**

FabricEye 是一款集成了边缘计算与大模型分析能力的智能验布系统。它通过普通摄像头采集视频流或上传历史视频，利用自研的 **CascadeEngine (级联检测引擎)** 进行实时缺陷分析，并通过 WebSocket 实时推送检测结果，帮助面料商降低人工成本，提升质检效率。

---

## ✨ 核心特性

- 🚀 **CascadeEngine 级联检测 V2.0**：采用 "Flash (快速初筛) + Plus (精准确认)" 双阶段 AI 检测流水线，平衡检测速度与精度。
- 📹 **视频文件检测**：支持上传历史视频进行离线检测，补检以往未检测的布卷。
- 🎬 **视频回放与标记**：检测完成后可回放视频，在画面上动态叠加缺陷标记和说明。
- 📥 **标记视频导出**：支持将带缺陷标记的视频导出为MP4文件，方便分享给客户。
- 📸 **全场景设备兼容**：支持工业相机及普通 OpenCV 摄像头，适配多种生产环境。
- ⚡ **实时推送与展示**：基于 WebSocket 的缺陷秒级推送，支持实时截图预览与历史缺陷回溯。
- 📊 **双 ID 图像策略**：首创实时临时 ID (`cid_`) 与数据库持久化 ID 并行策略，确保监控过程图片加载无延迟。
- 🛠️ **国产大模型深度集成**：适配通义千问 (Qwen3.5) 等主流多模态大模型，支持色差、破洞、污渍等多种缺陷识别。

---

## 🏗️ 技术架构

### 后端 (Backend)
- **框架**: FastAPI (高性能异步 Python 框架)
- **引擎**: CascadeEngine V2.0 (多线程流式分析引擎，支持实时/离线双模式)
- **数据库**: SQLite + SQLAlchemy 2.0 (异步驱动 aiosqlite)
- **图像处理**: OpenCV
- **AI 接口**: DashScope (Qwen3.5 Flash/Plus)
- **视频导出**: FFmpeg + OpenCV VideoWriter

### 前端 (Frontend)
- **框架**: Vue 3 (Composition API)
- **构建**: Vite 5
- **UI 组件**: Element Plus
- **状态管理**: Pinia
- **通信**: WebSocket + Axios
- **视频播放**: HTML5 Video + SVG 叠加层

---

## 📁 项目结构

```text
FabricEye/
├── backend/                # 后端服务目录
│   ├── app/
│   │   ├── core/           # 配置文件与数据库初始化
│   │   ├── models/         # 数据库模型 (Roll, Defect, Video)
│   │   ├── routers/        # API 接口
│   │   │   ├── rolls.py           # 布卷管理
│   │   │   ├── defects.py         # 缺陷管理
│   │   │   ├── videos.py          # 视频管理与回放
│   │   │   ├── video_upload.py    # 视频上传与离线检测
│   │   │   └── websocket.py       # WebSocket 实时推送
│   │   ├── services/       # 核心服务
│   │   │   ├── cascade_engine.py  # 级联检测引擎 V2.0
│   │   │   ├── video_capture.py   # 视频采集（Camera/File双模式）
│   │   │   ├── ai_analyzer.py     # AI分析服务
│   │   │   └── video_exporter.py  # 视频导出服务
│   │   └── main.py         # 应用入口 (Port: 8000)
│   ├── storage/            # 存储空间
│   │   ├── videos/         # 录制的视频文件
│   │   ├── snapshots/      # 缺陷截图
│   │   ├── marked_videos/  # 导出的标记视频
│   │   └── uploaded/       # 上传的待检测视频
│   └── .env                # 环境变量配置
├── frontend/               # 前端项目目录
│   ├── src/
│   │   ├── views/          # 核心页面
│   │   │   ├── Home.vue           # 首页
│   │   │   ├── Rolls.vue          # 布卷管理
│   │   │   ├── Monitor.vue        # 实时监控
│   │   │   ├── VideoPlayback.vue  # 视频回放（新增）
│   │   │   ├── VideoUpload.vue    # 视频上传（新增）
│   │   │   └── Reports.vue        # 报告查看
│   │   ├── components/     # 业务组件
│   │   │   ├── monitor/
│   │   │   │   ├── CascadePanel.vue   # 级联检测状态面板
│   │   │   │   ├── VideoPlayer.vue    # 视频播放器
│   │   │   │   └── DefectList.vue     # 缺陷列表
│   │   │   └── rolls/
│   │   └── stores/         # 状态管理
│   └── vite.config.js      # 前端构建配置 (Port: 5173)
├── docs/                   # 开发文档
│   ├── modular-cascade-design.md      # 级联检测架构设计
│   ├── streaming-architecture.md      # 流式处理架构
│   ├── api-design.md                  # API设计文档
│   ├── video-playback-development-guide.md      # 视频回放功能
│   └── offline-video-detection-guide.md         # 离线检测功能
└── data/                   # 数据库文件存放处
```

---

## 🚀 快速开始

### 1. 环境准备
- **Python**: 3.10+
- **Node.js**: 18+
- **硬件**: USB 摄像头或内置摄像头（可选，支持纯文件模式）

### 2. 后端部署

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# 配置 .env 文件 (参考 .env.example，设置 QWEN_API_KEY)
uvicorn app.main:app --reload --port 8000
```

### 3. 前端部署

```bash
cd frontend
npm install
npm run dev
```

访问：[http://localhost:5173](http://localhost:5173)

---

## ⚙️ 关键配置 (.env)

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `cascade` | 设置为 `cascade` 启用级联检测引擎 |
| `CAMERA_TYPE` | `opencv` | 摄像头类型 (opencv/mock/file) |
| `CAMERA_ID` | `0` | 默认摄像头 ID |
| `QWEN_API_KEY` | `sk-xxx` | 阿里云 DashScope API Key |
| `PRIMARY_MODEL` | `qwen3.5-flash` | Flash 快速初筛模型 |
| `SECONDARY_MODEL` | `qwen3.5-plus` | Plus 精准确认模型 |
| `ENABLE_SECONDARY` | `True` | 是否启用二次验证 |
| `FLASH_THRESHOLD` | `0.4` | Flash 检测阈值 |
| `SKIP_VERIFY_THRESHOLD` | `0.8` | 跳过复核阈值 |

---

## 📖 使用指南

### 方式一：实时检测（摄像头）

1. 进入 **"实时监控"** 页面
2. 点击 **"新建布卷"** 创建检测任务
3. 填写布卷信息（编号、面料类型等）
4. 点击 **"开始验布"** 启动摄像头检测
5. 实时查看检测到的缺陷和统计信息
6. 点击 **"停止验布"** 结束检测

### 方式二：离线检测（视频文件）

1. 进入 **"上传视频检测"** 页面（如未显示，需先开发此功能）
2. 拖拽或选择视频文件上传（支持 MP4/AVI/MOV/MKV）
3. 填写布卷编号和面料类型
4. 系统自动后台处理，显示进度百分比
5. 处理完成后点击 **"查看结果"** 进入回放页面

### 方式三：视频回放与导出

1. 进入 **"布卷管理"** 页面
2. 找到已完成的布卷，点击 **"回放"** 按钮
3. 在回放页面：
   - 观看带缺陷标记的视频
   - 点击时间轴跳转到缺陷位置
   - 点击缺陷标记查看详情
4. 点击 **"导出标记视频"** 生成带标记的MP4文件

---

## 📊 项目当前状态

### 已完成 ✅

- [x] **后端核心**: 异步数据库架构与级联检测引擎 V2.0
- [x] **实时检测**: 摄像头视频采集 + AI 实时分析
- [x] **离线检测**: 视频文件上传 + 后台异步处理
- [x] **视频录制**: 检测过程自动保存为视频文件
- [x] **视频回放**: 支持缺陷标记动态叠加和时间轴导航
- [x] **视频导出**: 生成带标记的MP4视频文件
- [x] **前端监控**: 实时视频轮询、WebSocket 缺陷推送
- [x] **缺陷展示**: 实时截图显示，支持 `cid_` 协议
- [x] **数据闭环**: 验布启动 → AI 检测 → 缺陷推送 → 数据库存储 → 历史查看
- [x] **模块化架构**: CascadeEngine 支持 Flash/Plus 双阶段检测

### 进行中 🚧

- [ ] **长时间运行稳定性**: 压力测试与内存优化
- [ ] **工业相机驱动**: GenICam 深度集成

### 规划 📋

- [ ] **YOLO 本地模型**: 降低 API 成本，提升检测速度
- [ ] **批量上传优化**: 支持同时处理多个视频文件
- [ ] **移动端适配**: 响应式布局优化
- [ ] **多租户支持**: SaaS 平台化改造

---

## 🛠️ 开发文档

项目已生成详细的开发文档，位于 `docs/` 目录：

| 文档 | 内容 |
|------|------|
| `modular-cascade-design.md` | 级联检测引擎 V2.0 架构设计 |
| `streaming-architecture.md` | 流式处理架构说明 |
| `api-design.md` | RESTful API + WebSocket 接口规范 |
| `video-playback-development-guide.md` | 视频回放功能开发指南 |
| `offline-video-detection-guide.md` | 离线视频检测功能开发指南 |
| `testing-assets-guideline.md` | **测试资产管理规范** |

---

## 🐛 常见问题

### Q: 前端提示 "服务器内部错误"
A: 检查后端是否正常运行，以及 `vite.config.js` 中的代理端口是否与后端端口一致（默认 8000）。

### Q: 视频回放不显示缺陷标记
A: 确认该布卷已完成检测并生成了缺陷数据，检查浏览器控制台是否有 API 错误。

### Q: 上传视频后进度卡在 0%
A: 检查后端日志，确认离线处理任务是否正常启动，视频文件是否完整保存到 `storage/uploaded/`。

### Q: 导出标记视频失败
A: 确认系统已安装 FFmpeg，检查 `storage/marked_videos/` 目录权限。

---

## 📋 开发者规范

### 测试截图管理

**⚠️ 重要**: 所有测试截图、调试图片必须存放到指定目录，**禁止**存放在项目根目录！

#### 目录结构
```
tests/
├── assets/
│   ├── screenshots/ui/v2.0/     # UI 测试截图（按版本存放）
│   ├── screenshots/defects/      # 缺陷示例图
│   ├── debug/                    # 调试输出（不提交到Git）
│   └── recordings/              # 测试录屏（不提交到Git）
└── reports/html/                # 测试报告
```

#### 命名规范
- UI 截图: `[日期]_[模块]_[功能]_[状态].png`  
  示例: `20260303_monitor_start-inspection_success.png`
- 缺陷示例: `defect_[类型]_[严重程度]_[编号].png`  
  示例: `defect_hole_severe_001.png`

#### 详细规范
请参阅 [测试资产管理规范](./docs/testing-assets-guideline.md)

---

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request 来完善 FabricEye。

**让每一卷布都有 AI 守护** 🤖✨

---

## 📄 License

MIT License

Copyright (c) 2026 FabricEye Team
