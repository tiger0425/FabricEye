# FabricEye API 设计文档 V2.0

> **版本**: 2.0  
> **最后更新**: 2026-03-03  
> **状态**: 与代码同步

## 1. 概述

本文档定义了 FabricEye AI 验布系统的 RESTful API 规范。API 采用 JSON 格式进行数据交换，支持布卷管理、视频录制控制、缺陷查询、视频回放与导出等功能。

**Base URL**: `http://localhost:8000/api`

**通用响应格式**:
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

**错误响应格式**:
```json
{
  "code": 400,
  "message": "错误描述",
  "data": null
}
```

## 2. 布卷管理 API

### 2.1 创建布卷

**Endpoint**: `POST /rolls`

**请求体**:
```json
{
  "roll_number": "R001",
  "fabric_type": "涤纶",
  "batch_number": "B20240101",
  "length_meters": 100.5,
  "metadata": {
    "width": 1.5,
    "color": "白色"
  }
}
```

**响应 (201 Created)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "roll_number": "R001",
    "fabric_type": "涤纶",
    "batch_number": "B20240101",
    "length_meters": 100.5,
    "status": "pending",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "metadata": {
      "width": 1.5,
      "color": "白色"
    }
  }
}
```

### 2.2 获取布卷列表

**Endpoint**: `GET /rolls`

**查询参数**:
| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| page | int | 页码 | 1 |
| page_size | int | 每页数量 | 20 |
| status | string | 按状态筛选 | - |

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "roll_number": "R001",
        "fabric_type": "涤纶",
        "status": "completed",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### 2.3 获取布卷详情

**Endpoint**: `GET /rolls/{roll_id}`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "roll_number": "R001",
    "fabric_type": "涤纶",
    "batch_number": "B20240101",
    "length_meters": 100.5,
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T12:00:00Z",
    "metadata": {
      "width": 1.5,
      "color": "白色"
    },
    "videos": [...],
    "defects": [...]
  }
}
```

### 2.4 更新布卷

**Endpoint**: `PUT /rolls/{roll_id}`

**请求体**:
```json
{
  "fabric_type": "棉布",
  "status": "completed"
}
```

### 2.5 删除布卷

**Endpoint**: `DELETE /rolls/{roll_id}`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "删除成功"
}
```

### 2.6 开始验布

**Endpoint**: `POST /rolls/{roll_id}/start`

**说明**: 启动级联检测引擎，开始实时验布

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "已开始验布"
}
```

### 2.7 停止验布

**Endpoint**: `POST /rolls/{roll_id}/stop`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "已停止验布"
}
```

### 2.8 获取级联状态

**Endpoint**: `GET /rolls/{roll_id}/cascade-status`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "is_running": true,
    "roll_id": 1,
    "buffer_size": 5,
    "buffer_capacity": 120,
    "verification_queue_size": 0,
    "pending_count": 0,
    "confirmed_count": 12,
    "rejected_count": 3,
    "expired_count": 1,
    "total_frames_captured": 1523
  }
}
```

### 2.9 获取布卷报告

**Endpoint**: `GET /rolls/{roll_id}/report`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "roll": {
      "id": 1,
      "roll_number": "R001",
      "fabric_type": "涤纶",
      "status": "completed"
    },
    "summary": {
      "total_defects": 15,
      "by_severity": {
        "severe": 3,
        "moderate": 7,
        "minor": 5
      },
      "by_type": [
        {
          "type": "hole",
          "type_cn": "破洞",
          "count": 3,
          "percentage": 20.0
        }
      ],
      "quality_score": 85
    },
    "defects": [],
    "generated_at": "2024-01-15T12:00:00Z"
  }
}
```



## 3. 视频管理 API

### 3.1 开始录制

**Endpoint**: `POST /videos/start`

**请求体**:
```json
{
  "roll_id": 1,
  "fps": 30,
  "resolution": "1920x1080"
}
```

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "video_id": 1,
    "roll_id": 1,
    "status": "recording",
    "started_at": "2024-01-15T10:30:00Z",
    "file_path": "/storage/videos/roll_1_20240115_103000.mp4"
  }
}
```

### 3.2 停止录制

**Endpoint**: `POST /videos/{video_id}/stop`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "video_id": 1,
    "status": "completed",
    "completed_at": "2024-01-15T10:35:00Z",
    "duration_seconds": 300.5,
    "file_size": 524288000
  }
}
```

### 3.3 获取视频详情

**Endpoint**: `GET /videos/{video_id}`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "roll_id": 1,
    "file_path": "/storage/videos/roll_1_20240115_103000.mp4",
    "file_size": 524288000,
    "duration_seconds": 300.5,
    "resolution": "1920x1080",
    "fps": 30.0,
    "status": "completed",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:35:00Z"
  }
}
```

### 3.4 获取布卷的视频列表

**Endpoint**: `GET /rolls/{roll_id}/videos`

### 3.5 获取视频信息

**Endpoint**: `GET /videos/{video_id}/info`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "roll_id": 1,
    "file_path": "/storage/videos/roll_1_20240115_103000.mp4",
    "file_size": 524288000,
    "file_size_mb": 500.0,
    "duration_seconds": 300.5,
    "resolution": "1920x1080",
    "fps": 30.0,
    "status": "completed",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:35:00Z"
  }
}
```

### 3.6 视频流播放

**Endpoint**: `GET /videos/stream/{video_id}`

**说明**: 返回视频文件流，支持范围请求（Range Requests）

### 3.7 获取视频缺陷时间轴

**Endpoint**: `GET /videos/{video_id}/defects/timeline`

**说明**: 用于视频回放时叠加缺陷标记

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "video_id": 1,
    "total_defects": 15,
    "defects": [
      {
        "id": 1,
        "timestamp": 125.5,
        "duration": 2.0,
        "bbox": [100, 200, 300, 400],
        "type": "hole",
        "type_cn": "破洞",
        "confidence": 0.95,
        "severity": "severe",
        "snapshot_path": "/storage/snapshots/defect_1.jpg"
      }
    ]
  }
}
```

### 3.8 导出标记视频

**Endpoint**: `POST /videos/{video_id}/export-marked`

**说明**: 后台生成带缺陷标记的视频文件

**请求体**:
```json
{
  "format": "mp4",
  "quality": "high"
}
```

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "导出任务已创建",
  "data": {
    "task_id": "uuid-string",
    "status": "processing"
  }
}
```

### 3.9 查询导出状态

**Endpoint**: `GET /videos/export-status/{task_id}`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "processing",
    "progress": 65.5,
    "output_path": "/storage/marked_videos/marked_1_20240303_143000.mp4"
  }
}
```

### 3.10 下载标记视频

**Endpoint**: `GET /videos/download-marked/{task_id}`

**说明**: 下载已完成的标记视频文件

**响应**: 文件流（Content-Type: video/mp4）


## 4. 缺陷查询 API

### 4.1 获取缺陷列表

**Endpoint**: `GET /defects`

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| roll_id | int | 按布卷筛选 |
| video_id | int | 按视频筛选 |
| defect_type | string | 按类型筛选 |
| severity | string | 按严重程度筛选 |
| min_confidence | float | 最低置信度 |
| reviewed | bool | 是否已复核 |
| page | int | 页码 |
| page_size | int | 每页数量 |

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "roll_id": 1,
        "video_id": 1,
        "defect_type": "hole",
        "defect_type_cn": "破洞",
        "confidence": 0.95,
        "severity": "severe",
        "position_meter": 50.5,
        "timestamp": 125.5,
        "bbox_x1": 100.0,
        "bbox_y1": 200.0,
        "bbox_x2": 150.0,
        "bbox_y2": 250.0,
        "snapshot_path": "/storage/snapshots/defect_1.jpg",
        "detected_at": "2024-01-15T10:30:05Z",
        "reviewed": false,
        "reviewed_result": null
      }
    ],
    "total": 15,
    "page": 1,
    "page_size": 20
  }
}
```

### 4.2 获取缺陷详情

**Endpoint**: `GET /defects/{defect_id}`

### 4.3 更新复核结果

**Endpoint**: `PUT /defects/{defect_id}/review`

**请求体**:
```json
{
  "reviewed_result": "confirmed"
}
```

**可选值**: `confirmed`, `false_positive`, `uncertain`

### 4.4 获取缺陷统计

**Endpoint**: `GET /rolls/{roll_id}/defects/statistics`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_defects": 15,
    "by_type": {
      "hole": 3,
      "stain": 5,
      "color_variance": 2,
      "warp_break": 3,
      "weft_break": 2
    },
    "by_severity": {
      "minor": 5,
      "moderate": 7,
      "severe": 3
    },
    "defect_rate": 0.15,  # 缺陷率 = 缺陷数 / 布卷长度
    "reviewed_count": 10,
    "confirmed_count": 8
  }
}
```

## 5. 实时状态 API (WebSocket)

### 5.1 WebSocket 连接

**Endpoint**: `WS /ws/rolls/{roll_id}/status`

**连接示例**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/rolls/1/status');

ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log(status);
};
```

### 5.2 消息格式

#### 5.2.1 检测状态更新

```json
{
  "type": "cascade_status",
  "data": {
    "is_running": true,
    "roll_id": 1,
    "buffer_size": 5,
    "buffer_capacity": 120,
    "verification_queue_size": 0,
    "pending_count": 0,
    "confirmed_count": 12,
    "rejected_count": 3,
    "expired_count": 1,
    "total_frames_captured": 1523
  }
}
```

#### 5.2.2 实时缺陷检测

```json
{
  "type": "defect_detected",
  "data": {
    "defect_id": 1,
    "defect_type": "hole",
    "defect_type_cn": "破洞",
    "confidence": 0.95,
    "severity": "severe",
    "position_meter": 50.5,
    "timestamp": 125.5,
    "bbox": [100, 200, 300, 400]
  }
}
```

#### 5.2.3 系统通知

```json
{
  "type": "notification",
  "data": {
    "level": "info",
    "message": "检测完成",
    "timestamp": "2024-01-15T10:35:00Z"
  }
}
```
```json
{
  "type": "recording_status",
  "data": {
    "video_id": 1,
    "status": "recording",
    "duration_seconds": 125.5,
    "file_size": 104857600
  }
}
```

**实时缺陷检测**:
```json
{
  "type": "defect_detected",
  "data": {
    "defect_id": 1,
    "defect_type": "hole",
    "confidence": 0.95,
    "severity": "severe",
    "position_meter": 50.5,
    "timestamp": 125.5
  }
}
```

**分析进度**:
```json
{
  "type": "analysis_progress",
  "data": {
    "video_id": 1,
    "progress": 0.45,
    "frames_processed": 1350,
    "total_frames": 3000,
    "defects_found": 8
  }
}
```

## 6. 健康检查与监控

### 6.1 系统健康状态

**Endpoint**: `GET /health`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "healthy",
    "database": "connected",
    "storage": {
      "total_gb": 1000,
      "used_gb": 250,
      "available_gb": 750
    },
    "active_rolls": 2,
    "active_videos": 1
  }
}
```

### 6.2 摄像头状态

**Endpoint**: `GET /cameras/status`

**响应 (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "cameras": [
      {
        "id": "cam_001",
        "status": "online",
        "resolution": "1920x1080",
        "fps": 30
      }
    ]
  }
}
```

## 7. 错误码定义

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如布卷编号重复） |
| 422 | 业务逻辑错误 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

## 8. 附录：数据模型映射

### 8.1 Roll (布卷)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| roll_number | string | 布卷编号（唯一） |
| fabric_type | string | 面料类型 |
| batch_number | string | 批次号 |
| length_meters | float | 布卷长度（米） |
| status | enum | 状态 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |
| metadata | json | 扩展字段 |

### 8.2 Video (视频)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| roll_id | int | 外键 |
| file_path | string | 文件路径 |
| file_size | bigint | 文件大小（字节） |
| duration_seconds | float | 视频时长 |
| resolution | string | 分辨率 |
| fps | float | 帧率 |
| status | enum | 状态 |
| started_at | datetime | 开始时间 |
| completed_at | datetime | 完成时间 |

### 8.3 Defect (缺陷)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| roll_id | int | 外键 |
| video_id | int | 外键（可空） |
| defect_type | enum | 缺陷类型 |
| defect_type_cn | string | 中文名称 |
| confidence | float | 置信度 |
| severity | enum | 严重程度 |
| position_meter | float | 位置（米） |
| timestamp | float | 视频时间戳 |
| bbox_x1 | float | 边界框坐标 |
| bbox_y1 | float | 边界框坐标 |
| bbox_x2 | float | 边界框坐标 |
| bbox_y2 | float | 边界框坐标 |
| snapshot_path | string | 快照路径 |
| detected_at | datetime | 检测时间 |
| reviewed | bool | 是否复核 |
| reviewed_result | enum | 复核结果 |

---

## 文档更新记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-03-03 | 2.0 | 更新为与代码同步，补充视频回放、导出相关 API，添加级联检测状态 API | AI助手 |
| 2024-01-15 | 1.0 | 初始版本 | - |

