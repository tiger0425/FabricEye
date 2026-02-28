# FabricEye AI 验布系统 - 后端

FabricEye 是一个基于 AI 的实时布卷缺陷检测系统。后端采用 FastAPI 框架，结合 OpenCV 进行视频流处理，并使用 SQLAlchemy (异步) 管理 SQLite 数据库。

## 技术栈

- **框架**: FastAPI
- **服务器**: Uvicorn
- **数据库**: SQLite (异步驱动: aiosqlite)
- **ORM**: SQLAlchemy 2.0
- **图像处理**: OpenCV
- **配置管理**: Pydantic Settings

## 目录结构

```text
backend/
├── app/
│   ├── core/           # 核心配置与数据库连接
│   ├── models/         # SQLAlchemy ORM 模型
│   ├── routers/        # API 路由定义
│   ├── services/       # 业务逻辑与 AI 处理服务
│   ├── utils/          # 通用工具函数
│   └── main.py         # 应用入口
├── requirements.txt    # 依赖列表
└── README.md           # 项目说明
```

## 快速开始

### 1. 安装依赖

建议使用虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. 启动应用

```bash
cd backend
uvicorn app.main:app --reload
```

访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看 Swagger API 文档。

## 核心功能 (Phase 1)

- [x] 基础 FastAPI 框架搭建
- [x] 异步 SQLite 数据库集成
- [x] 路由与模型占位定义
- [x] 视频采集与 AI 分析服务框架
- [x] 健康检查端点
