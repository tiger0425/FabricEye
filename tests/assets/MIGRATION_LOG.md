# 测试截图整理记录

## 整理时间
2026年3月3日

## 整理内容
将散落在项目根目录的55个测试截图文件按规范整理到 tests/assets/ 目录下

## 文件统计

### 原位置
- 路径: `/e/myProject/FabricEye/*.png`
- 数量: 55 个文件

### 新位置分布

| 目录 | 文件数 | 说明 |
|------|--------|------|
| `tests/assets/screenshots/defects/` | 3 | 缺陷检测示例图 |
| `tests/assets/screenshots/ui/v2.0/monitor/` | 16 | 监控页面截图 |
| `tests/assets/screenshots/ui/v2.0/playback/` | 3 | 回放页面截图 |
| `tests/assets/screenshots/ui/v2.0/rolls/` | 4 | 布卷管理页面截图 |
| `tests/assets/screenshots/ui/v2.0/settings/` | 2 | 设置页面截图 |
| `tests/assets/screenshots/ui/v2.0/stream/` | 5 | 视频流相关截图 |
| `tests/assets/screenshots/ui/v2.0/test/` | 12 | 测试用例截图 |
| `tests/assets/screenshots/ui/v2.0/misc/` | 9 | 其他杂项截图 |
| `tests/assets/debug/` | 1 | 调试截图 |
| **总计** | **55** | |

## 移动的文件清单

### defects/ (3个)
- defect-appeared.png
- defect-markers-fixed.png
- defect_display_fixed.png

### ui/v2.0/monitor/ (16个)
- monitor-page-error-state.png
- monitor-page-initial.png
- monitor-page.png
- monitor-snapshot.png
- monitor-status.png
- monitor-stream.png
- monitor-working.png
- monitor_cascade_status.png
- monitor_current.png
- monitor_full_v2.png
- monitor_page.png
- monitor_page_verification.png
- monitor_status.png
- monitor_v2_working.png
- monitor_video_test.png
- monitor_view.png

### ui/v2.0/playback/ (3个)
- playback-page.png
- playback_error.png
- playback_page.png

### ui/v2.0/rolls/ (4个)
- rolls-list-error.png
- rolls-list-final.png
- rolls-list-no-playback.png
- rolls_page.png

### ui/v2.0/settings/ (2个)
- settings_v2_full.png
- settings_v2_working.png

### ui/v2.0/stream/ (5个)
- stream_test_1.png
- stream_test_2.png
- video-playing-test.png
- video_frame_1.png
- video_frame_2.png

### ui/v2.0/test/ (12个)
- test-after-restart-fixed.png
- test-before-restart.png
- test-defect-list-final.png
- test-defect-list-fixed.png
- test-defect-list-with-timestamps.png
- test-defect-list.png
- test-defects-table.png
- test-home-page.png
- test-monitor-page-full.png
- test-monitor-page.png
- test-rolls-page.png
- test-timestamp-fixed-success.png

### ui/v2.0/misc/ (9个)
- cascade-panel-status.png
- detection_status.png
- detection_working.png
- final_fix.png
- final_monitor_view.png
- final_result.png
- final_status.png
- frontend_status.png
- now_you_see.png

### debug/ (1个)
- debug-screenshot.png

## 后续建议

1. **命名规范化**: 当前文件名还未完全按 `[日期]_[模块]_[功能]_[状态].png` 规范命名，建议后续逐步规范
2. **定期清理**: 建议每月清理 `tests/assets/debug/` 目录下的临时文件
3. **归档策略**: 重要版本的截图可以复制到 `tests/assets/screenshots/archive/vX.X/` 永久保存

## 规范参考

详细规范请参阅: [测试资产管理规范](../../docs/testing-assets-guideline.md)
