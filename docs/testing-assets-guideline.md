# FabricEye 测试资产管理规范

> **版本**: v1.0  
> **生效日期**: 2026年3月3日  
> **适用范围**: 所有开发者、测试人员

---

## 一、背景与目的

### 问题
- 测试截图、调试图片散落在项目根目录，难以管理
- 文件命名混乱，无法快速定位历史版本
- 容易误提交到代码仓库，增加仓库体积

### 目标
- 统一测试资产（截图、录屏、日志）的存放位置
- 建立规范的命名和分类体系
- 便于团队协作和历史追溯

---

## 二、目录结构

```
FabricEye/
├── tests/                      # 测试相关目录（新增）
│   ├── assets/                 # 测试资产
│   │   ├── screenshots/        # 测试截图
│   │   │   ├── ui/             # UI 测试截图
│   │   │   │   ├── v2.0/       # 按版本分类
│   │   │   │   └── latest/     # 最新版本
│   │   │   ├── defects/        # 缺陷检测结果示例
│   │   │   └── archive/        # 归档的历史截图
│   │   ├── recordings/         # 测试录屏
│   │   │   ├── videos/         # 视频录制
│   │   │   └── streams/        # 流式数据录制
│   │   └── debug/              # 调试输出
│   │       ├── frames/         # 调试帧图片
│   │       └── logs/           # 调试日志
│   └── reports/                # 测试报告
│       └── html/               # HTML 测试报告
├── docs/images/                # 文档用图（README、PRD等）
│   ├── architecture/           # 架构图
│   ├── screenshots/            # 产品截图
│   └── badges/                 # 徽章图标
└── .gitignore                  # 已配置忽略 tests/assets/
```

---

## 三、命名规范

### 3.1 截图文件命名

**格式**: `[日期]_[模块]_[功能]_[状态].png`

| 字段 | 说明 | 示例 |
|------|------|------|
| 日期 | YYYYMMDD | 20260303 |
| 模块 | 页面或模块名 | monitor, rolls, playback |
| 功能 | 测试的功能点 | start-inspection, defect-list |
| 状态 | 结果状态 | success, error, initial |

**示例**:
- `20260303_monitor_start-inspection_success.png`
- `20260303_rolls_defect-list_error.png`
- `20260303_playback_video-export_success.png`

### 3.2 缺陷检测示例图命名

**格式**: `defect_[类型]_[严重程度]_[编号].png`

**示例**:
- `defect_hole_severe_001.png`
- `defect_stain_moderate_002.png`

### 3.3 调试帧命名

**格式**: `frame_[卷ID]_[帧号]_[时间戳].jpg`

**示例**:
- `frame_roll001_0150_20260303_143052.jpg`

---

## 四、使用规范

### 4.1 存放位置

| 文件类型 | 存放位置 | 说明 |
|----------|----------|------|
| 自动化测试截图 | `tests/assets/screenshots/ui/` | 按版本分子目录 |
| 缺陷检测示例 | `tests/assets/screenshots/defects/` | 用于文档和演示 |
| 调试输出 | `tests/assets/debug/` | 临时文件，定期清理 |
| 测试录屏 | `tests/assets/recordings/` | 功能验证视频 |
| README 配图 | `docs/images/screenshots/` | 产品展示图 |
| 架构图 | `docs/images/architecture/` | 系统设计图 |

### 4.2 版本管理

**每个大版本创建独立子目录**:
```
tests/assets/screenshots/ui/
├── v1.0/               # 1.0 版本测试截图
├── v2.0/               # 2.0 版本测试截图
└── latest/             # 当前开发版本（软链接或复制）
```

### 4.3 清理策略

| 目录 | 保留策略 | 清理频率 |
|------|----------|----------|
| `debug/` | 保留7天 | 每周自动清理 |
| `screenshots/ui/latest/` | 保留30天 | 每月手动清理 |
| `screenshots/ui/vX.X/` | 永久保留 | 不清理 |
| `recordings/` | 保留30天 | 每月手动清理 |

---

## 五、Git 管理

### 5.1 已配置的 .gitignore

```gitignore
# 测试资产（大文件，不提交）
tests/assets/screenshots/ui/latest/
tests/assets/debug/
tests/assets/recordings/
*.log

# 文档用图（小文件，可以提交）
!docs/images/
!tests/assets/screenshots/defects/
```

### 5.2 需要提交的文件

✅ **可以提交**:
- `docs/images/` - 文档用图（经过压缩）
- `tests/assets/screenshots/defects/` - 缺陷示例（用于演示）
- `tests/reports/` - 测试报告摘要

❌ **不要提交**:
- 临时调试截图
- 视频录屏文件
- 日志文件

---

## 六、开发工具配置

### 6.1 Playwright 配置

在 `playwright.config.js` 或测试代码中指定输出目录：

```javascript
// playwright.config.js
export default {
  outputDir: 'tests/assets/screenshots/ui/latest/',
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
};

// 测试代码中手动截图
await page.screenshot({
  path: `tests/assets/screenshots/ui/v2.0/${date}_monitor_success.png`
});
```

### 6.2 VS Code 快速上传

配置 VS Code 的 `settings.json`，快速保存截图：

```json
{
  "fabricEye.screenshotPath": "tests/assets/screenshots/ui/latest/",
  "fabricEye.autoNaming": true
}
```

---

## 七、示例工作流

### 场景：测试监控页面功能

1. **开始测试前**
   ```bash
   mkdir -p tests/assets/screenshots/ui/v2.0
   ```

2. **测试过程中截图**
   ```javascript
   await page.screenshot({
     path: 'tests/assets/screenshots/ui/v2.0/20260303_monitor_initial.png'
   });
   ```

3. **发现缺陷时**
   ```javascript
   await page.screenshot({
     path: 'tests/assets/screenshots/ui/v2.0/20260303_monitor_defect-error.png'
   });
   ```

4. **测试完成后**
   - 保留成功的截图到版本目录
   - 将关键截图复制到 `docs/images/screenshots/` 用于文档
   - 清理 `tests/assets/debug/` 下的临时文件

---

## 八、检查清单

提交代码前，确认：

- [ ] 没有大文件（>1MB）提交到仓库
- [ ] 临时截图放在 `tests/assets/debug/`
- [ ] 正式截图按命名规范存放
- [ ] 没有 `.log` 文件提交
- [ ] `tests/assets/screenshots/ui/latest/` 已清理旧文件

---

## 九、违规处理

如发现以下情况，需立即整改：

1. ❌ 在根目录放置测试截图
2. ❌ 提交视频文件到代码仓库
3. ❌ 命名不规范导致无法识别

整改步骤：
1. 移动文件到正确位置
2. 按规范重命名
3. 更新 `.gitignore`（如需要）
4. 提交整改说明

---

## 十、附录

### 快速命令

```bash
# 创建今日测试目录
mkdir -p tests/assets/screenshots/ui/v2.0/$(date +%Y%m%d)

# 清理7天前的调试文件
find tests/assets/debug/ -type f -mtime +7 -delete

# 查看截图目录大小
du -sh tests/assets/

# 复制到文档目录
cp tests/assets/screenshots/ui/v2.0/20260303_monitor_success.png docs/images/screenshots/
```

### 相关文档

- [UI测试指南](./ui-testing-guide.md)
- [截图命名速查表](./naming-cheatsheet.md)

---

**制定人**: AI助手  
**审核人**: （待项目技术负责人审核）  
**最后更新**: 2026年3月3日
