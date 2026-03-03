# FabricEye 视频回放与标记功能开发说明文档

> **文档版本**: v1.0  
> **编制日期**: 2026年3月2日  
> **目标读者**: 前后端开发工程师  
> **开发周期预估**: 10-14个工作日

---

## 一、现状分析

### 1.1 当前已实现
- ✅ 视频流采集（用于AI实时分析）
- ✅ 缺陷检测与数据存储（含时间戳、边界框坐标）
- ✅ 缺陷截图保存（`storage/snapshots/`）

### 1.2 当前缺失
- ❌ **视频文件保存**：只分析了帧，没有保存完整视频
- ❌ **视频回放功能**：无法观看验布过程
- ❌ **缺陷标记展示**：无法在视频中标识缺陷位置
- ❌ **视频导出功能**：无法生成带标记的视频给客户

### 1.3 数据模型现状
```python
# Defect模型已有字段（可直接使用）
defect = {
    "timestamp": 125.5,        # 视频时间戳（秒）✅
    "bbox_x1~y2": [100,200,300,400],  # 边界框坐标 ✅
    "defect_type": "破洞",      # 缺陷类型 ✅
    "confidence": 0.95,        # 置信度 ✅
    "snapshot_path": "..."     # 截图路径 ✅
}

# Video模型已有字段
video = {
    "file_path": "...",        # 需要填充
    "duration_seconds": 300,   # 需要填充
    "fps": 30,                # 需要填充
    "resolution": "1920x1080"  # 需要填充
}
```

---

## 二、功能需求总览

### 2.1 功能清单

| 功能模块 | 功能点 | 优先级 | 技术方案 | 备注 |
|---------|--------|--------|----------|------|
| **基础功能** | 视频文件保存 | P0 | OpenCV VideoWriter | 缺失的基础功能 |
| **回放功能** | 视频播放页面 | P0 | 前端方案A | 动态叠加缺陷标记 |
| **回放功能** | 缺陷时间轴导航 | P1 | 前端组件 | 快速跳转到缺陷位置 |
| **回放功能** | 缺陷详情弹窗 | P1 | 前端组件 | 点击标记查看详情 |
| **导出功能** | 生成标记视频 | P2 | 后端方案B | FFmpeg处理 |
| **导出功能** | 下载标记视频 | P2 | 文件下载API | - |

### 2.2 用户场景

#### 场景1：内部质检回放
```
质检员李老板想复盘刚验完的布卷：
1. 打开"布卷详情"页面
2. 点击"回放视频"按钮
3. 观看视频，看到红色方框标记的缺陷位置
4. 点击缺陷标记，弹出详情（类型、置信度、截图）
5. 在时间轴上点击另一个缺陷，视频跳转到对应位置
```

#### 场景2：导出视频给客户
```
李老板需要把质检视频发给客户：
1. 在"布卷详情"页面点击"导出标记视频"
2. 系统后台处理（显示进度条）
3. 处理完成后下载MP4文件
4. 视频上永久嵌入了缺陷标记和说明
```

---

## 三、技术方案详解

### 3.1 基础功能：视频保存（必须先实现）

#### 3.1.1 后端修改

**文件**: `backend/app/services/cascade_engine.py`

**修改点1**: 初始化时创建VideoWriter
```python
class CascadeEngine:
    def __init__(self, roll_id: int):
        # ... 现有代码 ...
        self.video_writer = None
        self.video_path = None
        self.recording_start_time = None
        
    def start(self) -> bool:
        # ... 现有代码 ...
        
        # 新增：初始化视频录制
        self._init_video_recording()
        
        return True
    
    def _init_video_recording(self):
        """初始化视频录制"""
        import os
        from datetime import datetime
        
        # 生成视频文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_path = f"storage/videos/roll_{self.roll_id}_{timestamp}.mp4"
        os.makedirs(os.path.dirname(self.video_path), exist_ok=True)
        
        # 等第一帧到来后再初始化VideoWriter（获取实际分辨率）
        self.recording_start_time = time.time()
    
    def _capture_loop(self) -> None:
        """修改后的采集循环"""
        while self.is_running:
            try:
                frame = self.video_service.get_frame()
                if frame is not None:
                    # 初始化VideoWriter（第一帧时）
                    if self.video_writer is None and self.video_path:
                        height, width = frame.shape[:2]
                        # 建议使用 avc1 (H.264) 以确保浏览器原生回放兼容性
                        fourcc = cv2.VideoWriter_fourcc(*'avc1')
                        self.video_writer = cv2.VideoWriter(
                            self.video_path, 
                            fourcc, 
                            30.0,  # fps
                            (width, height)
                        )
                    
                    # 写入视频帧 (注意：生产环境建议将此操作移至独立线程的队列中，避免阻塞采集)
                    if self.video_writer:
                        self.video_writer.write(frame)

                    self.frame_buffer.append((self._frame_index, frame))
                    self._frame_index += 1
            except: 
                pass
            time.sleep(0.01)
    
    def stop(self) -> None:
        """修改后的停止方法"""
        self.is_running = False
        
        # 释放视频写入器
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        # 保存视频信息到数据库
        asyncio.create_task(self._save_video_info())
        
        print(f"--- CascadeEngine stopping for roll {self.roll_id} ---", flush=True)
    
    async def _save_video_info(self):
        """保存视频信息到数据库"""
        if not self.video_path or not os.path.exists(self.video_path):
            return
        
        file_size = os.path.getsize(self.video_path)
        duration = time.time() - self.recording_start_time if self.recording_start_time else 0
        
        # 读取视频获取元数据
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # 创建Video记录
        from app.models.video import Video, VideoStatus
        from app.core.database import SessionLocal
        
        async with SessionLocal() as session:
            video = Video(
                roll_id=self.roll_id,
                file_path=self.video_path,
                file_size=file_size,
                duration_seconds=duration,
                resolution=f"{width}x{height}",
                fps=fps,
                status=VideoStatus.COMPLETED,
                started_at=datetime.fromtimestamp(self.recording_start_time),
                completed_at=datetime.utcnow()
            )
            session.add(video)
            await session.commit()
            
            # 更新defect的video_id关联
            # （可选，如果需要在停止后关联）
```

**文件**: `backend/app/models/defect.py`

**可选修改**: 添加frame_number字段（如果需要精确到帧）
```python
class Defect(Base):
    # ... 现有字段 ...
    
    # 新增字段（可选，用于更精确的定位）
    frame_number: Mapped[int | None] = mapped_column(
        Integer, 
        nullable=True, 
        comment="视频帧号"
    )
```

#### 3.1.2 目录结构
```
backend/storage/
├── videos/           # 新增：存放录制的视频
│   ├── roll_1_20240302_103000.mp4
│   └── roll_2_20240302_110500.mp4
├── snapshots/        # 已有：缺陷截图
└── marked_videos/    # 新增：导出的标记视频
```

---

### 3.2 方案A：前端动态渲染回放

#### 3.2.1 后端API

**文件**: `backend/app/routers/videos.py` （新建）

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.core.database import get_db
from app.models.video import Video
from app.models.defect import Defect
from app.utils.response import success, error

router = APIRouter(prefix="/videos", tags=["Videos"])

@router.get("/roll/{roll_id}")
async def get_roll_videos(roll_id: int, db: AsyncSession = Depends(get_db)):
    """获取布卷的所有视频"""
    result = await db.execute(
        select(Video).where(Video.roll_id == roll_id)
    )
    videos = result.scalars().all()
    return success([{
        "id": v.id,
        "file_path": v.file_path,
        "duration_seconds": v.duration_seconds,
        "resolution": v.resolution,
        "fps": v.fps,
        "status": v.status.value
    } for v in videos])

@router.get("/stream/{video_id}")
async def stream_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """视频流播放（支持范围请求）"""
    from fastapi.responses import FileResponse
    
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(404, "视频不存在")
    
    return FileResponse(
        video.file_path,
        media_type="video/mp4"
    )

@router.get("/{video_id}/defects/timeline")
async def get_video_defects_timeline(
    video_id: int, 
    roll_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取视频缺陷时间轴数据
    用于前端播放器叠加缺陷标记
    """
    # 如果提供了roll_id，获取该布卷的所有缺陷
    # 否则只获取关联到此video_id的缺陷
    if roll_id:
        result = await db.execute(
            select(Defect)
            .where(Defect.roll_id == roll_id)
            .order_by(Defect.timestamp)
        )
    else:
        result = await db.execute(
            select(Defect)
            .where(Defect.video_id == video_id)
            .order_by(Defect.timestamp)
        )
    
    defects = result.scalars().all()
    
    timeline = []
    for d in defects:
        timeline.append({
            "id": d.id,
            "timestamp": d.timestamp,  # 出现时间（秒）
            "duration": 2.0,  # 持续时长（估算，可调整）
            "bbox": [d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
            "type": d.defect_type.value if d.defect_type else "unknown",
            "type_cn": d.defect_type_cn,
            "confidence": d.confidence,
            "severity": d.severity.value if d.severity else "minor",
            "snapshot_path": d.snapshot_path
        })
    
    return success({
        "video_id": video_id,
        "total_defects": len(timeline),
        "defects": timeline
    })

@router.get("/{video_id}/info")
async def get_video_info(video_id: int, db: AsyncSession = Depends(get_db)):
    """获取视频详细信息"""
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        return error("视频不存在", 404)
    
    return success({
        "id": video.id,
        "roll_id": video.roll_id,
        "file_path": video.file_path,
        "duration_seconds": video.duration_seconds,
        "resolution": video.resolution,
        "fps": video.fps,
        "file_size_mb": round(video.file_size / 1024 / 1024, 2) if video.file_size else 0
    })
```

**文件**: `backend/app/main.py`

添加路由：
```python
from app.routers import videos

app.include_router(videos.router)
```

#### 3.2.2 前端页面

**文件**: `frontend/src/views/VideoPlayback.vue` （新建）

```vue
<template>
  <div class="video-playback-page">
    <el-page-header @back="goBack" :content="`视频回放 - 布卷 ${rollId}`" />
    
    <div class="player-container">
      <!-- 视频播放区 -->
      <div class="video-wrapper">
        <video
          ref="videoPlayer"
          class="video-element"
          :src="videoUrl"
          controls
          @timeupdate="onTimeUpdate"
          @loadedmetadata="onVideoLoaded"
        />
        
        <!-- 缺陷标记层（SVG叠加） -->
        <svg 
          v-show="showDefects" 
          class="defect-overlay"
          :viewBox="`0 0 ${videoWidth} ${videoHeight}`"
          preserveAspectRatio="none"
        >
          <g v-for="defect in currentDefects" :key="defect.id">
            <!-- 边界框 -->
            <rect
              :x="defect.bbox[0]"
              :y="defect.bbox[1]"
              :width="defect.bbox[2] - defect.bbox[0]"
              :height="defect.bbox[3] - defect.bbox[1]"
              class="defect-box"
              :class="defect.severity"
              @click="showDefectDetail(defect)"
            />
            
            <!-- 标签背景 -->
            <rect
              :x="defect.bbox[0]"
              :y="Math.max(0, defect.bbox[1] - 25)"
              :width="120"
              :height="20"
              class="label-bg"
              :class="defect.severity"
            />
            
            <!-- 标签文字 -->
            <text
              :x="defect.bbox[0] + 5"
              :y="Math.max(15, defect.bbox[1] - 10)"
              class="defect-label"
            >
              {{ defect.type_cn }} {{ (defect.confidence * 100).toFixed(0) }}%
            </text>
          </g>
        </svg>
      </div>
      
      <!-- 控制栏 -->
      <div class="controls">
        <el-switch
          v-model="showDefects"
          active-text="显示缺陷标记"
          inactive-text="隐藏缺陷标记"
        />
        <el-button @click="exportMarkedVideo" :loading="exporting">
          导出标记视频
        </el-button>
      </div>
      
      <!-- 缺陷时间轴 -->
      <div class="timeline-container">
        <div class="timeline-label">缺陷时间轴：</div>
        <div class="timeline" @click="onTimelineClick">
          <!-- 时间轴背景 -->
          <div class="timeline-bg"></div>
          
          <!-- 缺陷标记点 -->
          <div
            v-for="defect in defectsTimeline"
            :key="defect.id"
            class="defect-point"
            :class="defect.severity"
            :style="{ left: `${(defect.timestamp / videoDuration) * 100}%` }"
            :title="`${defect.type_cn} @ ${formatTime(defect.timestamp)}`"
            @click.stop="jumpToDefect(defect)"
          />
          
          <!-- 当前播放位置 -->
          <div 
            class="playhead"
            :style="{ left: `${(currentTime / videoDuration) * 100}%` }"
          />
        </div>
        <div class="timeline-time">
          {{ formatTime(currentTime) }} / {{ formatTime(videoDuration) }}
        </div>
      </div>
    </div>
    
    <!-- 缺陷详情弹窗 -->
    <el-dialog
      :visible.sync="defectDetailVisible"
      title="缺陷详情"
      width="400px"
    >
      <div v-if="selectedDefect" class="defect-detail">
        <img 
          v-if="selectedDefect.snapshot_path" 
          :src="getSnapshotUrl(selectedDefect.snapshot_path)"
          class="defect-image"
        />
        <el-descriptions :column="1" border>
          <el-descriptions-item label="缺陷类型">
            {{ selectedDefect.type_cn }}
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            <el-progress 
              :percentage="selectedDefect.confidence * 100" 
              :color="getConfidenceColor"
            />
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(selectedDefect.severity)">
              {{ getSeverityLabel(selectedDefect.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="出现时间">
            {{ formatTime(selectedDefect.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="位置坐标">
            [{{ selectedDefect.bbox.join(', ') }}]
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'VideoPlayback',
  
  data() {
    return {
      rollId: null,
      videoId: null,
      videoUrl: '',
      videoDuration: 0,
      videoWidth: 1920,
      videoHeight: 1080,
      currentTime: 0,
      showDefects: true,
      
      defectsTimeline: [],
      currentDefects: [],
      
      defectDetailVisible: false,
      selectedDefect: null,
      exporting: false
    }
  },
  
  mounted() {
    this.rollId = this.$route.params.rollId
    this.videoId = this.$route.query.videoId
    this.loadData()
  },
  
  methods: {
    async loadData() {
      // 加载视频信息
      const videoRes = await this.$http.get(`/videos/${this.videoId}/info`)
      if (videoRes.data.code === 0) {
        const video = videoRes.data.data
        this.videoUrl = `/videos/stream/${this.videoId}`
        this.videoDuration = video.duration_seconds || 0
        const [w, h] = (video.resolution || '1920x1080').split('x').map(Number)
        this.videoWidth = w
        this.videoHeight = h
      }
      
      // 加载缺陷时间轴
      const defectsRes = await this.$http.get(
        `/videos/${this.videoId}/defects/timeline?roll_id=${this.rollId}`
      )
      if (defectsRes.data.code === 0) {
        this.defectsTimeline = defectsRes.data.data.defects
      }
    },
    
    onTimeUpdate() {
      this.currentTime = this.$refs.videoPlayer.currentTime
      this.updateCurrentDefects()
    },
    
    onVideoLoaded() {
      this.videoDuration = this.$refs.videoPlayer.duration
    },
    
    updateCurrentDefects() {
      // 显示当前时间±0.5秒内的缺陷
      const window = 0.5
      this.currentDefects = this.defectsTimeline.filter(d => 
        Math.abs(d.timestamp - this.currentTime) < window
      )
    },
    
    onTimelineClick(event) {
      const rect = event.currentTarget.getBoundingClientRect()
      const x = event.clientX - rect.left
      const percentage = x / rect.width
      const time = percentage * this.videoDuration
      this.$refs.videoPlayer.currentTime = time
    },
    
    jumpToDefect(defect) {
      this.$refs.videoPlayer.currentTime = defect.timestamp
      this.$refs.videoPlayer.play()
    },
    
    showDefectDetail(defect) {
      this.selectedDefect = defect
      this.defectDetailVisible = true
    },
    
    async exportMarkedVideo() {
      this.exporting = true
      try {
        const res = await this.$http.post(`/videos/${this.videoId}/export-marked`)
        if (res.data.code === 0) {
          this.$message.success('导出任务已创建，请稍后查看')
          // 轮询任务状态或跳转到下载页面
        }
      } finally {
        this.exporting = false
      }
    },
    
    formatTime(seconds) {
      if (!seconds) return '00:00'
      const mins = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    },
    
    getSnapshotUrl(path) {
      return `/api/${path}`
    },
    
    getSeverityType(severity) {
      const map = {
        'severe': 'danger',
        'moderate': 'warning',
        'minor': 'info'
      }
      return map[severity] || 'info'
    },
    
    getSeverityLabel(severity) {
      const map = {
        'severe': '严重',
        'moderate': '中等',
        'minor': '轻微'
      }
      return map[severity] || severity
    },
    
    goBack() {
      this.$router.back()
    }
  }
}
</script>

<style scoped>
.video-playback-page {
  padding: 20px;
}

.player-container {
  margin-top: 20px;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
}

.video-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.defect-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.defect-overlay rect {
  pointer-events: auto;
  cursor: pointer;
}

.defect-box {
  fill: transparent;
  stroke-width: 3;
}

.defect-box.severe {
  stroke: #ff4d4f;
}

.defect-box.moderate {
  stroke: #faad14;
}

.defect-box.minor {
  stroke: #52c41a;
}

.label-bg {
  stroke: none;
}

.label-bg.severe {
  fill: #ff4d4f;
}

.label-bg.moderate {
  fill: #faad14;
}

.label-bg.minor {
  fill: #52c41a;
}

.defect-label {
  fill: white;
  font-size: 12px;
  font-weight: bold;
  pointer-events: none;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #2a2a2a;
  color: white;
}

.timeline-container {
  padding: 15px 20px;
  background: #2a2a2a;
  border-top: 1px solid #3a3a3a;
}

.timeline-label {
  color: #999;
  font-size: 12px;
  margin-bottom: 8px;
}

.timeline {
  position: relative;
  height: 30px;
  background: #3a3a3a;
  border-radius: 4px;
  cursor: pointer;
}

.timeline-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.defect-point {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.2s;
}

.defect-point:hover {
  transform: translate(-50%, -50%) scale(1.5);
}

.defect-point.severe {
  background: #ff4d4f;
}

.defect-point.moderate {
  background: #faad14;
}

.defect-point.minor {
  background: #52c41a;
}

.playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: white;
  pointer-events: none;
}

.timeline-time {
  text-align: right;
  color: #999;
  font-size: 12px;
  margin-top: 8px;
}

.defect-detail {
  .defect-image {
    width: 100%;
    max-height: 200px;
    object-fit: contain;
    margin-bottom: 15px;
    border-radius: 4px;
  }
}
</style>
```

#### 3.2.3 入口集成

**文件**: `frontend/src/views/Rolls.vue` 或 `frontend/src/views/Report.vue`

添加回放按钮：
```vue
<el-button 
  v-if="scope.row.video_id" 
  type="primary" 
  size="small"
  @click="playVideo(scope.row)"
>
  回放
</el-button>

<script>
methods: {
  playVideo(row) {
    this.$router.push({
      path: `/playback/${row.roll_id}`,
      query: { videoId: row.video_id }
    })
  }
}
</script>
```

**文件**: `frontend/src/router/index.js`

添加路由：
```javascript
{
  path: '/playback/:rollId',
  name: 'VideoPlayback',
  component: () => import('@/views/VideoPlayback.vue'),
  meta: { title: '视频回放' }
}
```

---

### 3.3 方案B：后端FFmpeg导出标记视频

#### 3.3.1 导出任务API

**文件**: `backend/app/services/video_exporter.py` （新建）

```python
import cv2
import os
import subprocess
from typing import List, Dict
from datetime import datetime

class VideoExporter:
    """视频导出服务 - 使用OpenCV绘制标记"""
    
    def __init__(self, video_path: str, defects: List[Dict], output_path: str):
        self.video_path = video_path
        self.defects = defects
        self.output_path = output_path
        self.progress = 0
        self.status = "pending"  # pending, processing, completed, failed
        self.error_message = None
    
    def export(self) -> bool:
        """
        导出带标记的视频
        返回是否成功
        """
        try:
            self.status = "processing"
            
            # 打开原视频
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise Exception("无法打开原视频")
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 创建输出视频
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                raise Exception("无法创建输出视频")
            
            # 预处理缺陷数据：按时间戳分组
            defect_map = {}  # frame_number -> list of defects
            for defect in self.defects:
                timestamp = defect.get('timestamp', 0)
                frame_number = int(timestamp * fps)
                if frame_number not in defect_map:
                    defect_map[frame_number] = []
                defect_map[frame_number].append(defect)
            
            # 处理每一帧
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 检查当前帧是否有缺陷
                if frame_idx in defect_map:
                    frame = self._draw_defects_on_frame(
                        frame, defect_map[frame_idx]
                    )
                
                out.write(frame)
                
                # 更新进度
                frame_idx += 1
                self.progress = int((frame_idx / total_frames) * 100)
            
            cap.release()
            out.release()
            
            self.status = "completed"
            return True
            
        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            return False
    
    def _draw_defects_on_frame(self, frame, defects: List[Dict]) -> np.ndarray:
        """在帧上绘制缺陷标记"""
        for i, defect in enumerate(defects):
            bbox = defect.get('bbox', [0, 0, 0, 0])
            x1, y1, x2, y2 = map(int, bbox)
            
            # 根据严重程度选择颜色
            severity = defect.get('severity', 'minor')
            color_map = {
                'severe': (0, 0, 255),    # 红色 (BGR)
                'moderate': (0, 165, 255), # 橙色
                'minor': (0, 255, 0)       # 绿色
            }
            color = color_map.get(severity, (0, 255, 0))
            
            # 绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # 准备标签文字
            type_cn = defect.get('type_cn', defect.get('type', 'Unknown'))
            confidence = defect.get('confidence', 0)
            label = f"{type_cn} {confidence:.0%}"
            
            # 计算标签位置
            label_y = max(y1 - 10, 20)
            
            # 绘制标签背景
            (text_w, text_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                frame, 
                (x1, label_y - text_h - 5), 
                (x1 + text_w, label_y + 5),
                color, 
                -1
            )
            
            # 绘制标签文字
            cv2.putText(
                frame, label, (x1, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
            )
        
        return frame


# 全局任务管理器（简化版，生产环境建议用Redis+Celery）
export_tasks: Dict[str, VideoExporter] = {}

def start_export_task(task_id: str, video_path: str, defects: List[Dict], output_path: str):
    """启动导出任务"""
    exporter = VideoExporter(video_path, defects, output_path)
    export_tasks[task_id] = exporter
    
    # 在线程中执行（避免阻塞API）
    import threading
    def run_export():
        exporter.export()
    
    thread = threading.Thread(target=run_export)
    thread.start()
    
    return task_id

def get_export_status(task_id: str) -> Dict:
    """获取导出任务状态"""
    if task_id not in export_tasks:
        return {"status": "not_found"}
    
    exporter = export_tasks[task_id]
    return {
        "status": exporter.status,
        "progress": exporter.progress,
        "error": exporter.error_message,
        "output_path": exporter.output_path if exporter.status == "completed" else None
    }
```

**文件**: `backend/app/routers/videos.py` （添加导出接口）

```python
from fastapi import BackgroundTasks
from app.services.video_exporter import start_export_task, get_export_status
import uuid

@router.post("/{video_id}/export-marked")
async def export_marked_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    创建导出标记视频任务
    返回任务ID，用于轮询状态
    """
    # 获取视频信息
    video_result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = video_result.scalar_one_or_none()
    
    if not video:
        return error("视频不存在", 404)
    
    # 获取缺陷列表
    defects_result = await db.execute(
        select(Defect).where(Defect.video_id == video_id)
    )
    defects = defects_result.scalars().all()
    
    if not defects:
        return error("该视频没有缺陷数据", 400)
    
    # 准备输出路径
    task_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"marked_{video_id}_{timestamp}.mp4"
    output_path = f"storage/marked_videos/{output_filename}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 转换缺陷数据为字典列表
    defects_data = [{
        "timestamp": d.timestamp,
        "bbox": [d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
        "type": d.defect_type.value if d.defect_type else "unknown",
        "type_cn": d.defect_type_cn,
        "confidence": d.confidence,
        "severity": d.severity.value if d.severity else "minor"
    } for d in defects]
    
    # 启动导出任务
    start_export_task(task_id, video.file_path, defects_data, output_path)
    
    return success({
        "task_id": task_id,
        "status": "processing",
        "message": "导出任务已创建"
    })

@router.get("/export-status/{task_id}")
async def check_export_status(task_id: str):
    """查询导出任务状态"""
    status = get_export_status(task_id)
    return success(status)

@router.get("/download-marked/{task_id}")
async def download_marked_video(task_id: str):
    """下载已完成的标记视频"""
    from fastapi.responses import FileResponse
    
    status = get_export_status(task_id)
    
    if status["status"] != "completed":
        return error("视频尚未处理完成", 400)
    
    output_path = status.get("output_path")
    if not output_path or not os.path.exists(output_path):
        return error("视频文件不存在", 404)
    
    filename = os.path.basename(output_path)
    
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=filename
    )
```

#### 3.3.2 前端导出进度

**文件**: `frontend/src/views/VideoPlayback.vue` （添加轮询逻辑）

```javascript
methods: {
  async exportMarkedVideo() {
    // 创建导出任务
    const res = await this.$http.post(`/videos/${this.videoId}/export-marked`)
    if (res.data.code !== 0) {
      this.$message.error(res.data.message)
      return
    }
    
    const taskId = res.data.data.task_id
    this.exporting = true
    this.exportProgress = 0
    
    // 轮询进度
    this.exportInterval = setInterval(async () => {
      const statusRes = await this.$http.get(`/videos/export-status/${taskId}`)
      const status = statusRes.data.data
      
      this.exportProgress = status.progress
      
      if (status.status === 'completed') {
        clearInterval(this.exportInterval)
        this.exporting = false
        this.$message.success('导出完成！')
        
        // 自动下载
        window.open(`/videos/download-marked/${taskId}`)
      } else if (status.status === 'failed') {
        clearInterval(this.exportInterval)
        this.exporting = false
        this.$message.error(`导出失败: ${status.error}`)
      }
    }, 1000)
  }
}
```

---

## 四、增强功能建议

### 4.1 视频分段导出
只导出包含缺陷的片段，生成精简视频。

```python
def export_defect_segments(video_path, defects, padding=5):
    """
    导出缺陷片段
    padding: 前后保留的秒数
    """
    segments = []
    for defect in defects:
        start = max(0, defect['timestamp'] - padding)
        end = defect['timestamp'] + padding
        segments.append((start, end))
    
    # 合并重叠的片段
    # 使用FFmpeg concat 生成最终视频
```

### 4.2 多倍速播放
```vue
<el-select v-model="playbackRate" @change="changeSpeed">
  <el-option label="0.5x" :value="0.5" />
  <el-option label="1x" :value="1" />
  <el-option label="2x" :value="2" />
  <el-option label="4x" :value="4" />
</el-select>

changeSpeed(rate) {
  this.$refs.videoPlayer.playbackRate = rate
}
```

### 4.3 缺陷统计热力图
在时间轴上用热力图显示缺陷密集区域。

---

## 五、数据库迁移

如需添加新字段，创建迁移脚本：

```python
# backend/alembic/versions/xxx_add_video_fields.py
"""Add frame_number to defects and marked_video_path to videos

Revision ID: xxx
Revises: previous
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = 'xxx'
down_revision = 'previous'


def upgrade():
    # 添加frame_number字段（可选）
    op.add_column('defects', sa.Column('frame_number', sa.Integer(), nullable=True))
    
    # 添加标记视频路径字段
    op.add_column('videos', sa.Column('marked_video_path', sa.String(length=500), nullable=True))
    op.add_column('videos', sa.Column('marked_file_size', sa.BigInteger(), nullable=True))


def downgrade():
    op.drop_column('defects', 'frame_number')
    op.drop_column('videos', 'marked_video_path')
    op.drop_column('videos', 'marked_file_size')
```

---

## 六、接口汇总

| 接口 | 方法 | 说明 |
|------|------|------|
| `/videos/roll/{roll_id}` | GET | 获取布卷视频列表 |
| `/videos/stream/{video_id}` | GET | 视频流播放 |
| `/videos/{video_id}/info` | GET | 视频详细信息 |
| `/videos/{video_id}/defects/timeline` | GET | 缺陷时间轴数据 |
| `/videos/{video_id}/export-marked` | POST | 创建导出任务 |
| `/videos/export-status/{task_id}` | GET | 查询导出状态 |
| `/videos/download-marked/{task_id}` | GET | 下载标记视频 |

---

## 七、开发 checklist

### 后端开发
- [ ] 修改 `cascade_engine.py` 添加视频录制功能（建议使用独立线程+队列）
- [ ] 确保视频编码使用 H.264 (avc1) 并进行浏览器播放兼容性测试
- [ ] 新建 `videos.py` 路由文件
- [ ] 新建 `video_exporter.py` 导出服务
- [ ] 更新 `main.py` 添加路由
- [ ] 创建 `storage/videos/` 和 `storage/marked_videos/` 目录
- [ ] 测试视频录制功能
- [ ] 测试缺陷时间轴API
- [ ] 测试导出功能

### 前端开发
- [ ] 新建 `VideoPlayback.vue` 页面
- [ ] 更新路由配置
- [ ] 在布卷列表添加"回放"按钮
- [ ] 实现视频播放器组件
- [ ] 实现缺陷标记叠加层
- [ ] 实现时间轴组件
- [ ] 实现缺陷详情弹窗
- [ ] 实现导出进度显示

### 测试验证
- [ ] 录制视频能正常保存
- [ ] 回放页面能正确显示缺陷标记
- [ ] 点击时间轴能跳转到对应位置
- [ ] 导出的标记视频质量正常
- [ ] 长时间视频（>10分钟）处理正常

---

## 八、注意事项

1. **存储空间**：视频文件较大，建议定期清理或迁移旧视频
2. **导出性能**：长视频导出耗时较长，建议使用任务队列（Celery）
3. **浏览器兼容**：视频播放使用HTML5 Video，确保格式兼容（MP4/H.264）
4. **分辨率适配**：标记层需要随视频分辨率自适应
5. **并发导出**：限制同时进行的导出任务数，避免服务器过载

---
1281: 
1282: ## 九、架构审核与技术校准 (2026-03-02)
1283: 
1284: ### 9.1 录制性能：引入异步写入队列
1285: **风险**：`VideoWriter.write()` 为磁盘阻塞操作。在 30fps 采集频率下，磁盘 IO 波动会导致 `_capture_loop` 丢帧，进而影响 AI 检测。  
1286: **要求**：必须在 `CascadeEngine` 中实现 `video_queue = Queue(maxsize=300)`，并由独立线程负责从队列读取帧并写入磁盘。
1287: 
1288: ### 9.2 编码选型：为什么选择 H.264 而非 H.265
1289: **结论**：当前阶段**强制使用 H.264 (avc1)**。  
1290: **理由**：
1291: 1. **原生兼容**：H.264 在所有主流浏览器（Chrome/Safari/Edge）中均有完善的硬件加速解码支持。
1292: 2. **编码开销**：H.265 编码对 CPU 压力大，在边缘侧设备上容易导致实时验布系统过载。
1293: 3. **免转码回放**：使用 H.264 录制后，前端 `<video>` 标签可直接播放，无需后端进行昂贵的实时转码。
1294: 
1295: ### 9.3 状态一致性与防损
1296: **逻辑建议**：
1297: 1. **开始阶段**：在 `start()` 时立即向数据库写入 `Video` 记录，状态设为 `RECORDING`。
1298: 2. **异常保护**：`stop()` 方法中的 `release()` 操作应放入 `finally` 块，确保系统崩溃或异常停止时视频文件能正常闭合。
1299: 3. **自动恢复**：系统启动时应检查是否有残留的 `RECORDING` 状态记录，若有则标记为 `FAILED` 或尝试修复。
1300: 
1301: ---
1302: 
1303: **文档结束**

