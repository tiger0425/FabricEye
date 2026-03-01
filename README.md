# FabricEye - AI 智能验布系统

> **面向小微面料商的零门槛、高性能 AI 实时验布解决方案**

FabricEye 是一款集成了边缘计算与大模型分析能力的智能验布系统。它通过普通摄像头采集视频流，利用自研的 **CascadeEngine (级联检测引擎)** 进行实时缺陷分析，并通过 WebSocket 实时推送检测结果，帮助面料商降低人工成本，提升质检效率。

---

## ✨ 核心特性

- 🚀 **CascadeEngine 级联检测**：采用 "Flash (快速初筛) + Plus (精准确认)" 双阶段 AI 检测流水线，平衡检测速度与精度。
- 📸 **全场景设备兼容**：支持工业相机及普通 OpenCV 摄像头，适配多种生产环境。
- ⚡ **实时推送与展示**：基于 WebSocket 的缺陷秒级推送，支持实时截图预览与历史缺陷回溯。
- 📊 **双 ID 图像策略**：首创实时临时 ID (`cid_`) 与数据库持久化 ID 并行策略，确保监控过程图片加载无延迟。
- 🛠️ **国产大模型深度集成**：适配通义千问 (Qwen-VL) 等主流多模态大模型，支持色差、破洞、污渍等多种缺陷识别。

---

## 🏗️ 技术架构

### 后端 (Backend)
- **框架**: FastAPI (高性能异步 Python 框架)
- **引擎**: CascadeEngine (多线程流式分析引擎)
- **数据库**: SQLite + SQLAlchemy 2.0 (异步驱动 aiosqlite)
- **图像处理**: OpenCV
- **AI 接口**: DashScope (Qwen-VL)

### 前端 (Frontend)
- **框架**: Vue 3 (Composition API)
- **构建**: Vite 5
- **UI 组件**: Element Plus
- **状态管理**: Pinia
- **通信**: WebSocket + Axios

---

## 📁 项目结构

```text
FabricEye/
├── backend/                # 后端服务目录
│   ├── app/
│   │   ├── core/           # 配置文件与数据库初始化
│   │   ├── models/         # 数据库模型 (Roll, Defect, Video)
│   │   ├── routers/        # API 接口 (验布控制、缺陷管理、WS 推送)
│   │   ├── services/       # 核心服务 (CascadeEngine, VideoCapture)
│   │   └── main.py         # 应用入口 (Port: 8001)
│   ├── storage/            # 视频与截图存储空间
│   └── .env                # 环境变量配置
├── frontend/               # 前端项目目录
│   ├── src/
│   │   ├── views/          # 核心页面 (Monitor.vue, Rolls.vue)
│   │   ├── components/     # 业务组件 (CascadePanel, DefectList)
│   │   └── stores/         # 状态管理
│   └── vite.config.js      # 前端构建配置 (Port: 5175)
└── data/                   # 数据库文件存放处
```

---

## 🚀 快速开始

### 1. 环境准备
- **Python**: 3.10+
- **Node.js**: 18+
- **硬件**: 建议具备 USB 摄像头或内置摄像头

### 2. 后端部署
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
# 配置 .env 文件 (参考 .env.example)
uvicorn app.main:app --reload --port 8001
```

### 3. 前端部署
```bash
cd frontend
npm install
npm run dev
```
访问：[http://localhost:5175](http://localhost:5175)

---

## ⚙️ 关键配置 (.env)

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `cascade` | 设置为 `cascade` 启用级联检测引擎 |
| `CAMERA_TYPE` | `opencv` | 摄像头类型 (opencv/mock) |
| `CAMERA_ID` | `0` | 默认摄像头 ID |
| `QWEN_API_KEY` | `sk-xxx` | 阿里云 DashScope API Key |

---

## 📊 项目当前状态

- [x] **后端核心**: 完成异步数据库架构与级联检测引擎逻辑。
- [x] **前端监控**: 实现实时视频轮询、WebSocket 缺陷推送及自动同步状态。
- [x] **缺陷展示**: 修复实时截图显示问题，支持 `cid_` 协议访问临时截图。
- [x] **数据闭环**: 完成验布启动 -> AI 检测 -> 缺陷推送 -> 数据库存储 -> 历史查看的全流程。
- [ ] **待办**: 长时间运行稳定性压力测试、工业相机驱动 (GenICam) 深度集成。

---

## 🤝 贡献与反馈
欢迎提交 Issue 或 Pull Request 来完善 FabricEye。

**让每一卷布都有 AI 守护** 🤖✨
