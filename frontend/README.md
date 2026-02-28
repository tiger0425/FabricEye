# FabricEye AI验布系统 - 前端

> FabricEye AI验布系统的前端项目，基于 Vue 3 + Vite + Element Plus 构建。

## 技术栈

- **框架**: Vue 3 (Composition API + `<script setup>`)
- **构建工具**: Vite 5
- **UI组件库**: Element Plus
- **路由**: Vue Router 4
- **状态管理**: Pinia
- **HTTP客户端**: Axios

## 项目结构

```
frontend/
├── public/                 # 静态资源目录
├── src/
│   ├── api/               # API接口封装
│   │   ├── index.js      # API统一导出
│   │   ├── rolls.js      # 布卷管理API
│   │   ├── defects.js    # 缺陷检测API
│   │   └── videos.js     # 视频流API
│   ├── assets/           # 静态资源（图片、样式等）
│   ├── components/       # 组件目录
│   │   ├── common/       # 公共组件
│   │   │   ├── Layout.vue
│   │   │   ├── Header.vue
│   │   │   └── Sidebar.vue
│   │   ├── rolls/        # 布卷相关组件
│   │   │   ├── RollForm.vue
│   │   │   └── RollList.vue
│   │   ├── monitor/      # 监控相关组件
│   │   │   ├── VideoPlayer.vue
│   │   │   ├── DefectList.vue
│   │   │   └── StatusPanel.vue
│   │   └── reports/      # 报告相关组件
│   │       └── ReportViewer.vue
│   ├── views/            # 页面视图
│   │   ├── Home.vue       # 首页
│   │   ├── Rolls.vue     # 布卷管理
│   │   ├── Monitor.vue   # 实时监控
│   │   ├── Reports.vue   # 报告查看
│   │   └── Settings.vue  # 系统设置
│   ├── router/           # 路由配置
│   │   └── index.js
│   ├── stores/           # Pinia状态管理
│   │   ├── index.js      # Store统一导出
│   │   ├── rolls.js     # 布卷Store
│   │   └── monitor.js   # 监控Store
│   ├── utils/           # 工具函数
│   │   └── request.js   # Axios封装
│   ├── App.vue          # 根组件
│   └── main.js          # 应用入口
├── index.html           # HTML入口
├── package.json         # 项目依赖
├── vite.config.js       # Vite配置
└── README.md           # 项目说明
```

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

启动后访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

构建产物输出到 `dist` 目录

### 预览生产版本

```bash
npm run preview
```

## 功能模块

### 1. 首页 (Home)
- 系统概览统计
- 快捷操作入口
- 最近布卷列表

### 2. 布卷管理 (Rolls)
- 布卷列表展示
- 新建/编辑/删除布卷
- 开始/停止验布
- 搜索筛选

### 3. 实时监控 (Monitor)
- 视频流播放
- 实时缺陷检测
- AI分析状态
- 系统资源监控

### 4. 报告查看 (Reports)
- 报告列表展示
- 报告详情查看
- 报告下载/导出

### 5. 系统设置 (Settings)
- 基础设置
- AI模型配置

## 环境变量

可在 `vite.config.js` 中配置：

- `VITE_API_BASE_URL`: 后端API地址（默认: http://localhost:8000）
- `VITE_APP_TITLE`: 应用标题

## 开发规范

### 组件规范
- 使用 Composition API + `<script setup>` 语法
- 组件文件使用 PascalCase 命名
- 组件内部使用中文注释

### API接口
- 使用Axios封装请求
- 统一错误处理
- 请求/响应拦截器

### 状态管理
- 使用Pinia进行状态管理
- 按模块划分Store
- 命名使用 `useXxxStore` 格式

## 后续开发

- [ ] 添加用户认证模块
- [ ] 实现WebSocket实时通信
- [ ] 添加单元测试
- [ ] 优化性能
- [ ] 移动端适配

## License

MIT License
