# FabricEye Cascade Engine 重构计划

> **文档版本**: v1.0  
> **日期**: 2026-03-02  
> **目标文件**: `backend/app/services/cascade_engine.py` (405行)  
> **重构策略**: 拆分为 `services/cascade/` 包，保持向后兼容

---

## 1. 现状分析

### 1.1 源文件结构

| 组件 | 行号 | 类型 | 职责 |
|------|------|------|------|
| `PendingDefect` | 31-44 | dataclass | 待确认缺陷数据结构 |
| `DetectionDeduplicator` | 47-80 | class | 去重算法，IOU计算 |
| `get_vlm_roi` | 83-96 | function | 图像处理，ROI提取 |
| `AsyncVideoWriter` | 99-125 | class | 异步视频写入器 |
| `CascadeEngine` | 127-405 | class | 主引擎，3个检测循环 |

### 1.2 依赖关系图

```
CascadeEngine (主引擎)
├── VideoCaptureService (外部依赖)
├── AIAnalyzerService (外部依赖)
├── DetectionDeduplicator (内部组件)
├── AsyncVideoWriter (内部组件)
├── PendingDefect (内部数据类型)
├── get_vlm_roi (内部工具函数)
└── settings (配置)
```

### 1.3 外部依赖

| 导入模块 | 来源 |
|----------|------|
| `VideoCaptureService` | `app.services.video_capture` |
| `AIAnalyzerService` | `app.services.ai_analyzer` |
| `manager` | `app.routers.websocket` |
| `SessionLocal` | `app.core.database` |
| `Defect, DefectType, ...` | `app.models.defect` |
| `Video, VideoStatus` | `app.models.video` |
| `settings` | `app.core.config` |

### 1.4 消费者分析

| 文件 | 导入方式 | 用途 |
|------|----------|------|
| `app/routers/rolls.py` | `from app.services.cascade_engine import CascadeEngine` | 引擎生命周期管理 |

---

## 2. 目标架构

```
services/cascade/
├── __init__.py           # 向后兼容入口 (≈30行)
├── types.py              # PendingDefect 数据类型 (≈20行)
├── deduplicator.py       # DetectionDeduplicator (≈35行)
├── video_writer.py       # AsyncVideoWriter (≈30行)
├── image_processor.py    # get_vlm_roi + 图像工具 (≈20行)
└── engine.py             # CascadeEngine 主引擎 (≈180行)
```

### 2.1 模块职责

| 模块 | 预估行数 | 独立依赖 | 导出内容 |
|------|----------|----------|----------|
| `types.py` | ~20 | numpy | `PendingDefect` |
| `deduplicator.py` | ~35 | settings | `DetectionDeduplicator` |
| `video_writer.py` | ~30 | cv2, threading, queue | `AsyncVideoWriter` |
| `image_processor.py` | ~20 | cv2, numpy | `get_vlm_roi` |
| `engine.py` | ~180 | 所有子模块 + 外部服务 | `CascadeEngine` |
| `__init__.py` | ~30 | 所有子模块 | 向后兼容重导出 |

**总计**: ~315行 (比原405行减少90行，主要通过移除冗余和更紧凑的排列)

---

## 3. 详细实施计划 (10步流程)

### Step 1: 创建包目录结构

```bash
cd backend/app/services
mkdir -p cascade
touch cascade/__init__.py
touch cascade/types.py
touch cascade/deduplicator.py
touch cascade/video_writer.py
touch cascade/image_processor.py
touch cascade/engine.py
```

**验证**: 目录创建成功

---

### Step 2: 提取数据类型到 `types.py`

**内容**:
```python
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class PendingDefect:
    """Tracks a detection from Flash through Plus verification."""
    cascade_id: int
    frame_index: int
    flash_confidence: float
    roi_crop: np.ndarray
    timestamp: float
    bbox: tuple
    defect_type: str
    severity: str
    created_at: float
    status: str = "pending"
    plus_confidence: Optional[float] = None
```

**依赖**: numpy (已有), dataclasses (已有)

**验证**: `python -c "from app.services.cascade.types import PendingDefect; print(PendingDefect)"`

---

### Step 3: 提取去重器到 `deduplicator.py`

**内容**:
```python
from typing import List, Tuple

class DetectionDeduplicator:
    def __init__(self, iou_threshold: float, time_window: float):
        self.iou_threshold = iou_threshold
        self.time_window = time_window
        self._recent: List[Tuple[tuple, float]] = []

    def is_duplicate(self, bbox: tuple, timestamp: float) -> bool:
        self._prune(timestamp)
        for prev_bbox, _ in self._recent:
            if self._compute_iou(bbox, prev_bbox) >= self.iou_threshold:
                return True
        return False

    def add_detection(self, bbox: tuple, timestamp: float) -> None:
        self._prune(timestamp)
        self._recent.append((bbox, timestamp))

    def _prune(self, now: float) -> None:
        cutoff = now - self.time_window
        self._recent = [(b, t) for b, t in self._recent if t >= cutoff]

    @staticmethod
    def _compute_iou(box1: tuple, box2: tuple) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter_w = max(0, x2 - x1)
        inter_h = max(0, y2 - y1)
        inter_area = inter_w * inter_h
        area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
        area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
        union_area = area1 + area2 - inter_area
        return inter_area / union_area if union_area > 0 else 0.0
```

**依赖**: 无外部依赖 (仅使用内置类型)

**验证**: `python -c "from app.services.cascade.deduplicator import DetectionDeduplicator; d = DetectionDeduplicator(0.5, 3.0); print(d)"`

---

### Step 4: 提取视频写入器到 `video_writer.py`

**内容**:
```python
import threading
import cv2
from queue import Queue
from typing import Tuple

class AsyncVideoWriter:
    """异步视频写入器，使用独立线程避免阻塞主采集循环"""
    def __init__(self, filename: str, fourcc, fps: float, frame_size: Tuple[int, int]):
        self.writer = cv2.VideoWriter(filename, fourcc, fps, frame_size)
        self.frame_queue = Queue(maxsize=300)
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.worker_thread.start()

    def _write_loop(self):
        while not self.stop_event.is_set() or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=0.1)
                self.writer.write(frame)
                self.frame_queue.task_done()
            except: continue
        self.writer.release()

    def write(self, frame):
        try: self.frame_queue.put_nowait(frame)
        except: pass

    def release(self):
        self.stop_event.set()
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
```

**依赖**: cv2, threading, queue (已有)

**验证**: `python -c "from app.services.cascade.video_writer import AsyncVideoWriter; print(AsyncVideoWriter)"`

---

### Step 5: 提取图像处理到 `image_processor.py`

**内容**:
```python
import numpy as np
import cv2

def get_vlm_roi(image: np.ndarray, bbox: tuple, margin: float = 0.15, target_size: int = 512) -> np.ndarray:
    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    cx1, cy1 = max(0, int(x1 - mx)), max(0, int(y1 - my))
    cx2, cy2 = min(img_w, int(x2 + mx)), min(img_h, int(y2 + my))
    crop = image[cy1:cy2, cx1:cx2]
    if crop.size == 0: return np.zeros((target_size, target_size, 3), dtype=np.uint8)
    scale = min(target_size / crop.shape[1], target_size / crop.shape[0])
    resized = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    pad_x, pad_y = (target_size - resized.shape[1]) // 2, (target_size - resized.shape[0]) // 2
    canvas[pad_y:pad_y + resized.shape[0], pad_x:pad_x + resized.shape[1]] = resized
    return canvas
```

**依赖**: cv2, numpy (已有)

**验证**: `python -c "from app.services.cascade.image_processor import get_vlm_roi; print(get_vlm_roi)"`

---

### Step 6: 重构主引擎到 `engine.py`

**内容**: 将原 `CascadeEngine` 类完整复制，修改以下导入:

```python
# 原导入
from app.services.cascade_engine import PendingDefect, DetectionDeduplicator, AsyncVideoWriter, get_vlm_roi

# 新导入 (相对导入)
from app.services.cascade.types import PendingDefect
from app.services.cascade.deduplicator import DetectionDeduplicator
from app.services.cascade.video_writer import AsyncVideoWriter
from app.services.cascade.image_processor import get_vlm_roi
```

**注意**: 保留 `from app.core.config import settings` 等外部导入

**验证**: `python -c "from app.services.cascade.engine import CascadeEngine; print(CascadeEngine)"`

---

### Step 7: 创建向后兼容入口 `__init__.py`

**关键**: 确保现有导入路径继续工作

```python
# backend/app/services/cascade/__init__.py
"""
FabricEye 级联检测引擎包
提供 Flash + Plus 双阶段检测流水线
"""
import warnings

# 类型导出
from app.services.cascade.types import PendingDefect

# 组件导出
from app.services.cascade.deduplicator import DetectionDeduplicator
from app.services.cascade.video_writer import AsyncVideoWriter
from app.services.cascade.image_processor import get_vlm_roi

# 主引擎导出
from app.services.cascade.engine import CascadeEngine

# 向后兼容: 从旧路径导入时发出警告
__all__ = [
    "PendingDefect",
    "DetectionDeduplicator", 
    "AsyncVideoWriter",
    "get_vlm_roi",
    "CascadeEngine",
]
```

**验证**:
```bash
# 新路径 (推荐)
python -c "from app.services.cascade import CascadeEngine; print('OK: cascade module')"

# 旧路径 (兼容)
python -c "from app.services.cascade_engine import CascadeEngine; print('OK: backward compat')"
```

---

### Step 8: 创建旧文件的兼容重定向 (可选但推荐)

**方案A**: 保留原文件作为简单重定向

```python
# backend/app/services/cascade_engine.py (新内容)
"""
向后兼容重定向模块
警告: 此模块已弃用，请使用 app.services.cascade
"""
import warnings
warnings.warn(
    "app.services.cascade_engine 已弃用，请使用 app.services.cascade",
    DeprecationWarning,
    stacklevel=2
)

# 重导出所有内容
from app.services.cascade import (
    PendingDefect,
    DetectionDeduplicator,
    AsyncVideoWriter,
    get_vlm_roi,
    CascadeEngine,
)

__all__ = ["PendingDefect", "DetectionDeduplicator", "AsyncVideoWriter", "get_vlm_roi", "CascadeEngine"]
```

**方案B**: 直接删除原文件，仅依赖 `__init__.py` 重导出

推荐 **方案B**，因为:
- 减少代码重复
- 所有导入统一通过 `cascade/` 包
- 如需恢复，使用 git 快速回滚

---

### Step 9: 更新消费者导入

修改 `app/routers/rolls.py`:

```python
# 原导入
from app.services.cascade_engine import CascadeEngine

# 新导入 (二选一)
# 方案1: 使用新包路径 (推荐)
from app.services.cascade import CascadeEngine

# 方案2: 继续使用旧路径 (如果保留重定向)
from app.services.cascade_engine import CascadeEngine
```

---

### Step 10: 测试验证

#### 10.1 单元测试

```bash
# 测试各模块可导入
python -c "
from app.services.cascade import (
    PendingDefect,
    DetectionDeduplicator,
    AsyncVideoWriter,
    get_vlm_roi,
    CascadeEngine
)
print('All imports OK')
"

# 测试向后兼容
python -c "
import warnings
warnings.simplefilter('always')
from app.services.cascade_engine import CascadeEngine
print('Backward compatibility OK')
"
```

#### 10.2 功能测试

```bash
# 运行现有测试
cd backend
python -m pytest test_video_feature.py -v

# 或手动验证
python -c "
import asyncio
from app.services.cascade import CascadeEngine

async def test():
    engine = CascadeEngine(roll_id=999)
    status = engine.get_status()
    print(f'Status: {status}')
    assert status['roll_id'] == 999
    print('Test passed!')

asyncio.run(test())
"
```

---

## 4. 风险识别与缓解

### 4.1 高风险项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 循环导入 | 运行时崩溃 | 使用 `TYPE_CHECKING` 或延迟导入 |
| 类型引用断裂 | IDE/运行时错误 | 保留完整类型注解 |
| 异步上下文丢失 | 死锁 | 保持原有的 `asyncio.new_event_loop()` 模式 |
| 旧导入路径断裂 | 生产故障 | 保留 `cascade_engine.py` 重导出 |

### 4.2 中风险项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 测试覆盖不足 | 隐藏bug | 运行完整功能测试 |
| 配置访问失败 | 引擎启动失败 | 验证 settings 导入路径 |

### 4.3 回滚方案

```bash
# 快速回滚命令
cd backend/app/services
rm -rf cascade/
git checkout cascade_engine.py

# 验证回滚
python -c "from app.services.cascade_engine import CascadeEngine; print('Rollback OK')"
```

---

## 5. 测试策略

### 5.1 回归测试

| 测试文件 | 覆盖内容 | 优先级 |
|----------|----------|--------|
| `test_video_feature.py` | 端到端录制、检测、保存 | P0 |
| `test_api.py` | API端点集成 | P1 |

### 5.2 单元测试 (新增)

```python
# tests/test_cascade_types.py
import pytest
from app.services.cascade.types import PendingDefect

def test_pending_defect_creation():
    import numpy as np
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    pd = PendingDefect(
        cascade_id=1, frame_index=100,
        flash_confidence=0.8, roi_crop=img,
        timestamp=123456.0, bbox=(0, 0, 50, 50),
        defect_type="stain", severity="minor",
        created_at=123456.0
    )
    assert pd.status == "pending"
    assert pd.plus_confidence is None

# tests/test_cascade_deduplicator.py
def test_deduplicator_iou():
    from app.services.cascade.deduplicator import DetectionDeduplicator
    d = DetectionDeduplicator(iou_threshold=0.5, time_window=3.0)
    box1 = (0, 0, 10, 10)
    box2 = (5, 5, 15, 15)  # 重叠
    assert d._compute_iou(box1, box2) > 0.5
```

---

## 6. 依赖图与构建顺序

```
Step 2: types.py        ──┐
Step 3: deduplicator.py  ─┤
Step 4: video_writer.py  ─┤
Step 5: image_processor.py┤
                       ├─ 独立模块，无相互依赖
Step 6: engine.py       ─┤ 依赖上面4个模块
                       ─┤
Step 7: __init__.py     ─┤ 依赖 engine.py
                       ─┘
```

---

## 7. 验收标准

| # | 标准 | 验证方法 |
|---|------|----------|
| 1 | 新路径导入成功 | `from app.services.cascade import CascadeEngine` |
| 2 | 旧路径兼容 | `from app.services.cascade_engine import CascadeEngine` |
| 3 | 单模块 < 150行 | `wc -l cascade/*.py` |
| 4 | 现有测试通过 | `pytest test_video_feature.py` |
| 5 | 向后兼容无警告 | 运行生产导入脚本 |

---

## 8. 执行检查清单

```markdown
- [ ] Step 1: 创建 cascade/ 目录结构
- [ ] Step 2: 创建 types.py 并验证导入
- [ ] Step 3: 创建 deduplicator.py 并验证导入
- [ ] Step 4: 创建 video_writer.py 并验证导入
- [ ] Step 5: 创建 image_processor.py 并验证导入
- [ ] Step 6: 创建 engine.py 并验证导入
- [ ] Step 7: 创建 __init__.py 统一导出
- [ ] Step 8: 决定是否保留 cascade_engine.py
- [ ] Step 9: 更新 rolls.py 导入路径
- [ ] Step 10: 运行完整测试套件
```

---

**文档结束**
