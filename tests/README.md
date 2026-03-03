# FabricEye 测试目录

本目录用于存放测试相关文件，包括测试脚本、测试资产和测试报告。

## 目录结构

```
tests/
├── assets/                 # 测试资产（截图、录屏等）
│   ├── screenshots/        # 测试截图
│   │   ├── ui/v2.0/       # UI 测试截图（按版本分类）
│   │   └── defects/        # 缺陷检测示例图
│   ├── debug/              # 调试输出（临时文件）
│   └── recordings/         # 测试录屏
├── reports/                # 测试报告
│   └── html/              # HTML 格式报告
└── README.md              # 本文件
```

## 使用规范

### 1. 截图存放位置

- ✅ **正确**: `tests/assets/screenshots/ui/v2.0/20260303_monitor_success.png`
- ❌ **错误**: `monitor_test.png`（存放在项目根目录）

### 2. 命名规范

- UI 测试: `[日期]_[模块]_[功能]_[状态].png`
- 缺陷示例: `defect_[类型]_[严重程度]_[编号].png`

### 3. Git 提交

- ✅ 可以提交: `tests/assets/screenshots/defects/`, `docs/images/`
- ❌ 不要提交: `tests/assets/debug/`, `tests/assets/recordings/`

详细规范请参阅: [测试资产管理规范](../docs/testing-assets-guideline.md)

## 快速命令

```bash
# 创建今日测试目录
mkdir -p tests/assets/screenshots/ui/v2.0/$(date +%Y%m%d)

# 清理调试文件
find tests/assets/debug/ -type f -mtime +7 -delete

# 查看目录大小
du -sh tests/assets/
```
