# 代码结构示例

本文档展示如何正确拆分大型文件，供AI代理参考。

---

## 示例1: 拆分大型Vue组件

### ❌ 错误：单文件500行

```vue
<!-- VideoPlayback.vue (500行) -->
<template>
  <div class="video-playback">
    <!-- 100行：视频播放器 -->
    <div class="player-container">
      <video ...></video>
      <svg ...>...200行SVG逻辑...</svg>
    </div>
    
    <!-- 150行：时间轴 -->
    <div class="timeline" ...></div>
    
    <!-- 150行：缺陷列表 -->
    <el-table ...>...150行...</el-table>
    
    <!-- 100行：详情弹窗 -->
    <el-dialog ...>...100行...</el-dialog>
  </div>
</template>

<script setup>
// 300行脚本：数据处理、播放器控制、标记渲染、导出逻辑...
</script>
```

### ✅ 正确：拆分为多个文件（每个<200行）

```
views/VideoPlayback/
├── index.vue                    # 80行：只组装
├── components/
│   ├── VideoPlayer.vue          # 150行：播放器+控制
│   ├── DefectOverlay.vue        # 100行：SVG标记层
│   ├── DefectTimeline.vue       # 120行：时间轴
│   ├── DefectList.vue           # 130行：缺陷列表
│   └── ExportDialog.vue         # 80行：导出对话框
└── composables/
    ├── useVideoPlayer.ts        # 80行：播放器逻辑
    ├── useDefectMarkers.ts      # 60行：标记计算
    └── useTimeline.ts           # 50行：时间轴逻辑
```

**index.vue（主页面，80行）：**
```vue
<template>
  <div class="video-playback">
    <PageHeader title="视频回放" />
    
    <VideoPlayer 
      :video-url="videoUrl"
      :defects="currentDefects"
      @timeupdate="onTimeUpdate"
    />
    
    <DefectTimeline 
      :defects="defects"
      :current-time="currentTime"
      @seek="seekTo"
    />
    
    <DefectList 
      :defects="defects"
      @jump="jumpToDefect"
      @show-detail="showDefectDetail"
    />
    
    <ExportDialog v-model="showExport" :video-id="videoId" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import VideoPlayer from './components/VideoPlayer.vue'
import DefectTimeline from './components/DefectTimeline.vue'
import DefectList from './components/DefectList.vue'
import ExportDialog from './components/ExportDialog.vue'
import { useVideoStore } from '@/stores/videos'

const route = useRoute()
const videoStore = useVideoStore()

const videoId = computed(() => route.query.videoId as string)
const videoUrl = computed(() => videoStore.videoUrl)
const defects = computed(() => videoStore.defects)
const currentTime = computed(() => videoStore.currentTime)
const currentDefects = computed(() => videoStore.currentDefects)

const showExport = ref(false)

onMounted(() => {
  videoStore.loadVideo(videoId.value)
  videoStore.loadDefects(videoId.value)
})

function onTimeUpdate(time: number) {
  videoStore.setCurrentTime(time)
}

function seekTo(timestamp: number) {
  videoStore.seekTo(timestamp)
}

function jumpToDefect(defect: Defect) {
  videoStore.seekTo(defect.timestamp)
}

function showDefectDetail(defect: Defect) {
  // 显示详情
}
</script>
```

**VideoPlayer.vue（播放器组件，150行）：**
```vue
<template>
  <div class="video-player">
    <video 
      ref="videoRef"
      :src="videoUrl"
      controls
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoaded"
    />
    
    <DefectOverlay 
      v-if="currentDefects.length > 0"
      :defects="currentDefects"
      @click-defect="$emit('click-defect', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import DefectOverlay from './DefectOverlay.vue'
import { useVideoPlayer } from '../composables/useVideoPlayer'

interface Props {
  videoUrl: string
  defects: Defect[]
}

const props = defineProps<Props>()
const emit = defineEmits(['timeupdate', 'click-defect'])

const videoRef = ref<HTMLVideoElement>()
const { currentTime, seekTo } = useVideoPlayer(videoRef)

function onTimeUpdate(e: Event) {
  const video = e.target as HTMLVideoElement
  emit('timeupdate', video.currentTime)
}

function onLoaded(e: Event) {
  const video = e.target as HTMLVideoElement
  emit('timeupdate', video.currentTime)
}

// 计算当前时间附近的缺陷
const currentDefects = computed(() => {
  const window = 2
  return props.defects.filter(d => 
    Math.abs(d.timestamp - currentTime.value) <= window
  )
})
</script>
```

---

## 示例2: 拆分大型Python模块

### ❌ 错误：单文件400行

```python
# cascade_engine.py (400行)

class PendingDefect:
    ...

class DetectionDeduplicator:
    ...

class AsyncVideoWriter:
    ...

def get_vlm_roi(image, bbox, ...):
    ...

class CascadeEngine:
    def __init__(self): ...
    def start(self): ...
    def stop(self): ...
    def _init_video_recording(self): ...
    def _capture_loop(self): ...
    def _flash_loop(self): ...
    def _plus_loop(self): ...
    def _save_defect_to_db(self): ...
    def _expire_pending(self): ...
    def get_status(self): ...
```

### ✅ 正确：拆分为多个模块（每个<150行）

```
services/cascade/
├── __init__.py              # 30行：统一导出
├── engine.py                # 120行：主引擎
├── deduplicator.py          # 60行：去重逻辑
├── video_writer.py          # 50行：视频写入
├── timestamp_calculator.py  # 40行：时间戳计算
└── utils.py                 # 50行：工具函数
```

**__init__.py（统一导出）：**
```python
"""级联检测服务

提供Flash+Plus双阶段缺陷检测功能。
"""

from .engine import CascadeEngine
from .deduplicator import DetectionDeduplicator
from .video_writer import AsyncVideoWriter
from .timestamp_calculator import TimestampCalculator
from .utils import get_vlm_roi, PendingDefect

__all__ = [
    'CascadeEngine',
    'DetectionDeduplicator', 
    'AsyncVideoWriter',
    'TimestampCalculator',
    'get_vlm_roi',
    'PendingDefect'
]
```

**engine.py（主引擎，120行）：**
```python
"""级联检测引擎

负责调度Flash和Plus两个检测阶段。
"""

import asyncio
import threading
from typing import Optional
from datetime import datetime

from .deduplicator import DetectionDeduplicator
from .video_writer import AsyncVideoWriter
from .timestamp_calculator import TimestampCalculator
from .utils import PendingDefect
from app.services.video_capture import VideoCaptureService
from app.services.ai_analyzer import AIAnalyzerService


class CascadeEngine:
    """级联检测引擎主类
    
    协调视频采集、Flash初筛、Plus确认、去重、存储等流程。
    
    Attributes:
        roll_id: 当前验布的布卷ID
        is_running: 引擎运行状态
        video_writer: 异步视频写入器
    """
    
    def __init__(
        self,
        roll_id: int,
        video_service: VideoCaptureService,
        analyzer: AIAnalyzerService,
        deduplicator: DetectionDeduplicator,
        video_writer: AsyncVideoWriter,
        timestamp_calc: TimestampCalculator
    ):
        self.roll_id = roll_id
        self.video_service = video_service
        self.analyzer = analyzer
        self.deduplicator = deduplicator
        self.video_writer = video_writer
        self.timestamp_calc = timestamp_calc
        
        self.is_running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._flash_thread: Optional[threading.Thread] = None
        self._plus_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """启动级联检测引擎"""
        if self.is_running:
            return
        
        self.is_running = True
        self._init_video_recording()
        
        # 启动三个工作线程
        self._capture_thread = threading.Thread(target=self._capture_loop)
        self._flash_thread = threading.Thread(target=self._flash_loop)
        self._plus_thread = threading.Thread(target=self._plus_loop)
        
        self._capture_thread.start()
        self._flash_thread.start()
        self._plus_thread.start()
    
    def stop(self) -> None:
        """停止级联检测引擎"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 等待线程结束
        if self._capture_thread:
            self._capture_thread.join(timeout=5)
        if self._flash_thread:
            self._flash_thread.join(timeout=5)
        if self._plus_thread:
            self._plus_thread.join(timeout=5)
        
        # 释放资源
        if self.video_writer:
            self.video_writer.release()
    
    def get_status(self) -> dict:
        """获取当前运行状态"""
        return {
            'is_running': self.is_running,
            'roll_id': self.roll_id
        }
```

**timestamp_calculator.py（时间戳计算，40行）：**
```python
"""时间戳计算工具

计算缺陷相对于视频开始的时间戳。
"""

import time
from typing import Optional


class TimestampCalculator:
    """计算相对于视频开始的时间戳
    
    使用线程安全的方式获取录制开始时间，避免线程间变量不可见问题。
    
    Example:
        calc = TimestampCalculator()
        calc.set_start_time(time.time())
        
        # 稍后在线程中
        timestamp = calc.calculate()  # 返回从start_time到现在的时间差
    """
    
    def __init__(self):
        self._start_time: Optional[float] = None
        self._lock = threading.Lock()
    
    def set_start_time(self, start_time: float) -> None:
        """设置录制开始时间"""
        with self._lock:
            self._start_time = start_time
    
    def calculate(self, fallback_timestamp: float = 0) -> float:
        """计算当前时间戳
        
        Args:
            fallback_timestamp: 如果start_time未设置，返回的默认值
            
        Returns:
            从start_time到现在的时间差（秒），保留2位小数
        """
        with self._lock:
            start_time = self._start_time
        
        if start_time is None:
            return fallback_timestamp
        
        return round(time.time() - start_time, 2)
```

---

## 示例3: 数据格式隔离

### ❌ 错误：直接暴露后端格式

```typescript
// 后端返回 snake_case
const data = await fetch('/api/defects')
// 前端直接使用，到处都是 data.type_cn, data.bbox_x1
```

### ✅ 正确：通过隔离层转换

**types/defect.ts（类型定义+转换函数）：**
```typescript
/**
 * 缺陷类型定义
 * 
 * 单一真相源：所有代码都使用此接口，不直接使用后端原始数据。
 */

// 后端原始格式
export interface BackendDefect {
  id: number;
  timestamp: number | null;
  bbox_x1: number;
  bbox_y1: number;
  bbox_x2: number;
  bbox_y2: number;
  type: string;
  type_cn: string;
  defect_type: string;
  confidence: number;
  severity: string;
}

// 前端使用格式
export interface Defect {
  id: number;
  timestamp: number;
  bbox: [number, number, number, number];  // [x1, y1, x2, y2]
  type: string;
  typeCn: string;
  confidence: number;
  severity: 'minor' | 'moderate' | 'severe';
  position: string;  // "(x, y)" 格式
}

/**
 * 将后端数据转换为前端格式
 * 
 * 隔离后端API变化，统一在前端处理格式差异。
 */
export function normalizeDefect(raw: BackendDefect): Defect {
  // 确保bbox是数组格式
  const bbox: [number, number, number, number] = [
    raw.bbox_x1 ?? 0,
    raw.bbox_y1 ?? 0,
    raw.bbox_x2 ?? 0,
    raw.bbox_y2 ?? 0
  ]
  
  // 计算中心点位置
  const centerX = Math.round((bbox[0] + bbox[2]) / 2)
  const centerY = Math.round((bbox[1] + bbox[3]) / 2)
  
  return {
    id: raw.id,
    timestamp: raw.timestamp ?? 0,
    bbox,
    type: raw.defect_type || raw.type || 'unknown',
    typeCn: raw.type_cn || '未知',
    confidence: raw.confidence ?? 0,
    severity: normalizeSeverity(raw.severity),
    position: `(${centerX}, ${centerY})`
  }
}

function normalizeSeverity(severity: string): Defect['severity'] {
  const map: Record<string, Defect['severity']> = {
    'minor': 'minor',
    'moderate': 'moderate',
    'severe': 'severe',
    '轻微': 'minor',
    '中等': 'moderate',
    '严重': 'severe'
  }
  return map[severity] || 'minor'
}
```

**stores/videos.ts（Store中使用隔离层）：**
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { videoApi } from '@/api/videos'
import { normalizeDefect, type Defect } from '@/types/defect'

export const useVideoStore = defineStore('video', () => {
  const defects = ref<Defect[]>([])
  
  async function loadDefects(videoId: string) {
    const res = await videoApi.getDefects(videoId)
    
    // ✅ 使用转换函数隔离后端格式变化
    defects.value = (res.defects || []).map(normalizeDefect)
  }
  
  return {
    defects,
    loadDefects
  }
})
```

---

## 总结

**核心原则：**
1. **文件大小**：Vue < 200行，Python < 150行
2. **单一职责**：每个文件只做一件事
3. **接口隔离**：数据格式转换在隔离层完成
4. **测试先行**：每步都要测试验证
5. **用户确认**：每步完成后必须用户确认

**拆分顺序：**
1. 提取类型定义（types/）
2. 提取工具函数（utils/）
3. 提取业务逻辑（composables/ 或 services/）
4. 拆分组件/模块
5. 主文件只负责组装（index.vue 或 __init__.py）
