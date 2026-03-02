# FabricEye 离线视频检测功能开发文档

> **文档版本**: v1.0  
> **编制日期**: 2026年3月2日  
> **目标读者**: 全栈开发工程师  
> **功能描述**: 支持上传现有视频文件进行AI缺陷检测，替代或补充实时摄像头检测  
> **预估开发周期**: 5-7个工作日

---

## 一、功能概述

### 1.1 功能背景
当前系统仅支持实时摄像头检测，用户提出需要支持：
- **历史视频补检**: 对之前未使用AI检测的视频进行回溯分析
- **客户送检**: 接收客户上传的视频文件进行远程质检
- **批量处理**: 一次性处理多个历史视频文件
- **重新分析**: 对已有视频使用新的检测参数重新跑检

### 1.2 核心差异对比

| 特性 | 实时检测模式 | 离线文件模式 |
|------|-------------|-------------|
| 视频源 | USB摄像头/工业相机 | 上传的视频文件(MP4/AVI/MOV) |
| 处理速度 | 实时(受限于AI调用频率) | 最大速度(受限于硬件性能) |
| 交互方式 | WebSocket实时推送 | 后台异步处理+轮询进度 |
| 停止控制 | 用户手动点击停止 | 自动检测文件结束 |
| 进度显示 | 当前帧计数 | 百分比进度条 |
| 适用场景 | 生产线在线质检 | 历史视频补检/客户送检 |

### 1.3 业务流程

```
用户上传视频
    │
    ▼
┌─────────────────┐
│ 1. 文件接收与校验 │ ← 验证格式、大小、完整性
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 创建业务记录  │ ← 布卷记录 + 视频记录(状态:PENDING)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 启动后台任务  │ ← 异步启动CascadeEngine(文件模式)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 逐帧分析处理  │ ← 读取文件帧 → AI检测 → 保存缺陷
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 完成与通知   │ ← 状态更新为COMPLETED，用户查看结果
└─────────────────┘
```

---

## 二、技术架构设计

### 2.1 架构调整思路

在现有架构基础上进行**非侵入式扩展**：

1. **视频采集层**: 新增`FileCamera`类，实现与`OpenCVCamera`相同的接口
2. **引擎层**: 扩展`CascadeEngine`，通过参数切换Camera/File模式
3. **服务层**: 新建上传处理服务，管理异步任务生命周期
4. **API层**: 新增上传、状态查询、重新处理等接口
5. **前端层**: 新建上传页面，支持拖拽上传和进度展示

### 2.2 核心类图

```
┌─────────────────────────────────────────────────────────────┐
│                      视频采集层 (BaseCamera)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ OpenCVCamera    │  │ FileCamera      │  │ MockCamera   │ │
│  │ (实时摄像头)     │  │ (文件输入)      │  │ (模拟数据)   │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘ │
│           │                    │                   │         │
└───────────┼────────────────────┼───────────────────┼─────────┘
            │                    │                   │
            └────────────────────┴───────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │ VideoCaptureService │
                    │   (create_camera)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   CascadeEngine     │
                    │  ├─ source_type     │
                    │  ├─ source_path     │
                    │  └─ is_file_mode    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌──────────┐ ┌──────────────────┐
    │ _capture_loop   │ │_flash_loop│ │ _plus_loop       │
    │ (支持文件结束检测)│ │ (常规)   │ │ (常规)           │
    └─────────────────┘ └──────────┘ └──────────────────┘
```

### 2.3 数据流向

```
上传视频文件
    │
    ▼
storage/uploaded/  ←── 物理存储
    │
    ▼
FileCamera.open(file_path)
    │
    ▼
CascadeEngine(文件模式)
    │
    ├───► _capture_loop ────► 逐帧读取文件
    │                              │
    │                              ▼
    │                         frame_buffer
    │                              │
    ├───► _flash_loop ◄────────────┘
    │         │
    │         ▼
    │    AI分析(Flash)
    │         │
    │         ▼
    │    verification_queue
    │         │
    └───► _plus_loop ◄─────────────┘
              │
              ▼
         AI验证(Plus)
              │
              ▼
         保存Defect记录
              │
              ▼
         SQLite数据库
```

---

## 三、后端开发指南

### 3.1 修改文件1: video_capture.py

**位置**: `backend/app/services/video_capture.py`

**修改内容**: 在`CameraFactory`之前添加`FileCamera`类

```python
class FileCamera(BaseCamera):
    """
    文件相机实现 - 从视频文件读取帧
    用于离线视频文件检测
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_opened = False
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 30.0
        self.width = 0
        self.height = 0
        
    def open(self) -> bool:
        """打开视频文件"""
        try:
            self.cap = cv2.VideoCapture(self.file_path)
            if not self.cap.isOpened():
                logger.error(f"无法打开视频文件: {self.file_path}")
                return False
            
            # 获取视频元数据
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.is_opened = True
            
            logger.info(f"FileCamera已打开: {self.file_path}, "
                       f"总帧数: {self.total_frames}, FPS: {self.fps}, "
                       f"分辨率: {self.width}x{self.height}")
            return True
            
        except Exception as e:
            logger.error(f"打开视频文件失败: {e}")
            return False
    
    def close(self) -> None:
        """关闭视频文件"""
        if self.cap:
            self.cap.release()
            self.cap = None
            self.is_opened = False
            logger.info(f"FileCamera已关闭: {self.file_path}")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """读取下一帧"""
        if not self.is_opened or not self.cap:
            return None
        
        ret, frame = self.cap.read()
        if ret:
            self.current_frame += 1
            return frame
        else:
            # 文件读取完毕
            logger.info(f"FileCamera: 文件读取完毕 ({self.current_frame}/{self.total_frames})")
            return None
    
    def get_progress(self) -> float:
        """获取处理进度 (0-100)"""
        if self.total_frames == 0:
            return 0.0
        return (self.current_frame / self.total_frames) * 100
    
    def seek(self, frame_number: int) -> bool:
        """跳转到指定帧（用于重新分析时定位）"""
        if not self.cap:
            return False
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number
        return True
```

**修改CameraFactory**:

```python
class CameraFactory:
    """
    相机工厂，支持多种视频源
    """
    @staticmethod
    def create_camera(
        source_type: str = "auto",
        file_path: Optional[str] = None
    ) -> BaseCamera:
        """
        创建相机实例
        
        Args:
            source_type: "auto" | "opencv" | "file" | "mock"
            file_path: 当source_type="file"时，指定视频文件路径
        """
        if source_type == "file":
            if not file_path:
                raise ValueError("文件模式必须提供file_path参数")
            return FileCamera(file_path=file_path)
            
        elif source_type == "opencv":
            return OpenCVCamera(
                device_id=settings.CAMERA_ID,
                width=settings.CAMERA_WIDTH,
                height=settings.CAMERA_HEIGHT,
                fps=settings.CAMERA_FPS
            )
            
        elif source_type == "mock":
            return MockCamera(
                width=settings.CAMERA_WIDTH,
                height=settings.CAMERA_HEIGHT
            )
            
        else:  # auto模式
            cam_type = settings.CAMERA_TYPE.lower()
            if cam_type == "opencv":
                return CameraFactory.create_camera("opencv")
            elif cam_type == "mock":
                return CameraFactory.create_camera("mock")
            else:
                logger.warning(f"未知的相机类型: {cam_type}，使用MockCamera")
                return CameraFactory.create_camera("mock")
```

### 3.2 修改文件2: cascade_engine.py

**位置**: `backend/app/services/cascade_engine.py`

**修改__init__方法**:

```python
class CascadeEngine:
    def __init__(
        self,
        roll_id: int,
        source_type: str = "camera",
        source_path: Optional[str] = None
    ):
        """
        初始化级联检测引擎
        
        Args:
            roll_id: 布卷ID
            source_type: "camera" | "file" - 视频源类型
            source_path: 当source_type="file"时，指定视频文件路径
        """
        self.roll_id = roll_id
        self.source_type = source_type
        self.source_path = source_path
        self.is_file_mode = (source_type == "file")
        
        # 根据模式创建视频服务
        if self.is_file_mode:
            from app.services.video_capture import CameraFactory
            self.video_service = CameraFactory.create_camera("file", file_path=source_path)
        else:
            self.video_service = VideoCaptureService()
        
        self.analyzer = AIAnalyzerService()
        self.frame_buffer = collections.deque(maxlen=settings.FRAME_BUFFER_SIZE)
        self._frame_index = 0
        self.verification_queue = queue.Queue(maxsize=settings.VERIFICATION_QUEUE_SIZE)
        self._pending_lock = threading.Lock()
        self.pending_defects: Dict[int, PendingDefect] = {}
        self._cascade_id_counter = 0
        self.deduplicator = DetectionDeduplicator(
            settings.DEDUP_IOU_THRESHOLD,
            settings.DEDUP_TIME_WINDOW
        )
        
        # 运行状态
        self.is_running = False
        self._capture_thread = None
        self._flash_thread = None
        self._plus_thread = None
        
        # 文件模式特有属性
        self.file_progress = 0.0
        self.is_file_complete = False
        self.total_file_frames = 0
```

**修改_capture_loop方法**:

```python
def _capture_loop(self) -> None:
    """
    采集循环
    摄像头模式: 持续采集直到手动停止
    文件模式: 采集到文件结束自动停止
    """
    mode_str = "(文件模式)" if self.is_file_mode else ""
    print(f"--- 采集线程启动 {mode_str} ---", flush=True)
    
    while self.is_running:
        try:
            frame = self.video_service.get_frame()
            
            if frame is not None:
                self.frame_buffer.append((self._frame_index, frame))
                self._frame_index += 1
                
                # 文件模式: 更新进度
                if self.is_file_mode:
                    self.file_progress = self.video_service.get_progress()
                    
            elif self.is_file_mode:
                # 文件读取完毕
                print(f"--- 文件处理完成: {self.file_progress:.1f}% ---", flush=True)
                self.is_file_complete = True
                
                # 等待分析队列处理完毕（给Flash和Plus线程时间）
                wait_count = 0
                while (not self.verification_queue.empty() or 
                       any(d.status == "pending" for d in self.pending_defects.values())):
                    time.sleep(0.5)
                    wait_count += 1
                    if wait_count > 20:  # 最多等待10秒
                        break
                
                print("--- 所有帧处理完毕，自动停止引擎 ---", flush=True)
                self.stop()
                break
                    
        except Exception as e:
            logger.error(f"采集错误: {e}")
            if self.is_file_mode:
                # 文件模式出错也停止
                self.stop()
                break
                
        time.sleep(0.01)
```

**修改get_status方法**:

```python
def get_status(self) -> dict:
    """获取引擎状态"""
    with self._pending_lock:
        p = sum(1 for d in self.pending_defects.values() if d.status == "pending")
        c = sum(1 for d in self.pending_defects.values() if d.status == "confirmed")
        r = sum(1 for d in self.pending_defects.values() if d.status == "rejected")
        e = sum(1 for d in self.pending_defects.values() if d.status == "expired")
    
    status = {
        "is_running": self.is_running,
        "roll_id": self.roll_id,
        "source_type": self.source_type,
        "buffer_size": len(self.frame_buffer),
        "buffer_capacity": settings.FRAME_BUFFER_SIZE,
        "verification_queue_size": self.verification_queue.qsize(),
        "pending_count": p,
        "confirmed_count": c,
        "rejected_count": r,
        "expired_count": e,
        "total_frames_captured": self._frame_index,
        "cascade_id_counter": self._cascade_id_counter
    }
    
    # 文件模式添加额外信息
    if self.is_file_mode:
        status.update({
            "is_file_complete": self.is_file_complete,
            "file_progress": round(self.file_progress, 1),
            "file_path": self.source_path
        })
    
    return status
```

### 3.3 新建文件3: video_upload.py

**位置**: `backend/app/routers/video_upload.py`

```python
"""
视频上传与离线处理 API
支持上传视频文件进行离线AI缺陷检测
"""

import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import asyncio

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.models.video import Video, VideoStatus
from app.models.roll import Roll, RollStatus
from app.models.defect import Defect
from app.services.cascade_engine import CascadeEngine
from app.utils.response import success, error
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Video Upload"])

# 全局存储正在进行的离线处理任务
# 格式: {video_id: CascadeEngine}
offline_tasks: Dict[int, CascadeEngine] = {}

# 允许上传的视频格式
ALLOWED_VIDEO_TYPES = [
    "video/mp4",
    "video/avi",
    "video/quicktime",      # .mov
    "video/x-msvideo",
    "video/x-matroska"      # .mkv
]

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}

# 最大文件大小: 2GB
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


def validate_video_file(file: UploadFile) -> tuple[bool, str]:
    """
    验证视频文件
    返回: (是否有效, 错误信息)
    """
    # 验证MIME类型
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        return False, f"不支持的文件类型: {file.content_type}"
    
    # 验证文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"不支持的文件扩展名: {file_ext}"
    
    return True, ""


@router.post("/video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    roll_number: str = Form(..., description="布卷编号"),
    fabric_type: Optional[str] = Form(None, description="面料类型"),
    batch_number: Optional[str] = Form(None, description="批次号"),
    db: AsyncSession = Depends(get_db)
):
    """
    上传视频文件进行离线检测
    
    流程：
    1. 验证文件格式和大小
    2. 保存文件到 storage/uploaded/
    3. 创建或关联布卷记录
    4. 创建视频记录（状态：PENDING）
    5. 后台启动离线检测任务
    
    返回：
    - video_id: 视频ID
    - roll_id: 布卷ID
    - status: processing（正在处理）
    """
    
    # 1. 验证文件
    is_valid, error_msg = validate_video_file(file)
    if not is_valid:
        return error(error_msg, 400)
    
    # 2. 检查文件大小
    file.file.seek(0, 2)  # 移动到末尾
    file_size = file.file.tell()
    file.file.seek(0)     # 重置到开头
    
    if file_size > MAX_FILE_SIZE:
        return error(f"文件大小超过2GB限制", 400)
    
    if file_size == 0:
        return error("文件为空", 400)
    
    try:
        # 3. 生成文件名并保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = os.path.splitext(file.filename)[1].lower()
        safe_filename = f"uploaded_{timestamp}_{roll_number}{file_ext}"
        upload_dir = "storage/uploaded"
        file_path = os.path.join(upload_dir, safe_filename)
        
        os.makedirs(upload_dir, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"视频文件已保存: {file_path}, 大小: {file_size} bytes")
        
        # 4. 查找或创建布卷
        result = await db.execute(
            select(Roll).where(Roll.roll_number == roll_number)
        )
        roll = result.scalar_one_or_none()
        
        if roll:
            # 更新现有布卷
            if fabric_type:
                roll.fabric_type = fabric_type
            if batch_number:
                roll.batch_number = batch_number
            roll.status = RollStatus.PENDING
            roll.updated_at = datetime.utcnow()
        else:
            # 创建新布卷
            roll = Roll(
                roll_number=roll_number,
                fabric_type=fabric_type or "未知面料",
                batch_number=batch_number,
                status=RollStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(roll)
        
        await db.commit()
        await db.refresh(roll)
        
        # 5. 创建视频记录
        video = Video(
            roll_id=roll.id,
            file_path=file_path,
            file_size=file_size,
            status=VideoStatus.PENDING,
            started_at=datetime.utcnow()
        )
        db.add(video)
        await db.commit()
        await db.refresh(video)
        
        # 6. 后台启动离线检测
        background_tasks.add_task(
            process_uploaded_video_task,
            video.id,
            roll.id,
            file_path
        )
        
        return success({
            "video_id": video.id,
            "roll_id": roll.id,
            "roll_number": roll_number,
            "file_path": file_path,
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "status": "processing",
            "message": "视频上传成功，正在后台处理"
        })
        
    except Exception as e:
        logger.exception("视频上传失败")
        # 清理已保存的文件
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return error(f"上传失败: {str(e)}", 500)


async def process_uploaded_video_task(video_id: int, roll_id: int, file_path: str):
    """
    后台处理上传的视频任务
    
    这是实际的异步处理函数，在后台线程中运行
    """
    logger.info(f"开始离线处理视频: video_id={video_id}, roll_id={roll_id}, path={file_path}")
    
    async def run_detection():
        nonlocal video_id, roll_id, file_path
        
        try:
            # 更新视频状态为处理中
            async with SessionLocal() as session:
                video = await session.get(Video, video_id)
                if video:
                    video.status = VideoStatus.PROCESSING
                    await session.commit()
            
            # 创建离线检测引擎（文件模式）
            engine = CascadeEngine(
                roll_id=roll_id,
                source_type="file",
                source_path=file_path
            )
            
            # 存储到全局任务列表
            offline_tasks[video_id] = engine
            
            # 启动检测
            if engine.start():
                logger.info(f"离线引擎启动成功: video_id={video_id}")
                
                # 等待处理完成（文件模式会自动停止）
                check_interval = 1  # 每秒检查一次
                max_wait_time = 3600  # 最大等待1小时
                waited = 0
                
                while engine.is_running and waited < max_wait_time:
                    await asyncio.sleep(check_interval)
                    waited += check_interval
                    
                    # 定期更新进度到数据库
                    if waited % 5 == 0:  # 每5秒更新一次
                        async with SessionLocal() as session:
                            video = await session.get(Video, video_id)
                            if video:
                                # 使用duration_seconds存储进度百分比
                                video.duration_seconds = engine.file_progress
                                await session.commit()
                
                # 处理完成或超时
                if waited >= max_wait_time:
                    logger.warning(f"视频处理超时: video_id={video_id}")
                    engine.stop()
                
                # 更新完成状态
                async with SessionLocal() as session:
                    video = await session.get(Video, video_id)
                    if video:
                        # 获取视频实际信息
                        import cv2
                        cap = cv2.VideoCapture(file_path)
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        cap.release()
                        
                        video.status = VideoStatus.COMPLETED
                        video.fps = fps
                        video.resolution = f"{width}x{height}"
                        video.duration_seconds = frame_count / fps if fps > 0 else 0
                        video.completed_at = datetime.utcnow()
                        
                        # 更新布卷状态为已完成
                        roll = await session.get(Roll, roll_id)
                        if roll:
                            roll.status = RollStatus.COMPLETED
                            roll.updated_at = datetime.utcnow()
                        
                        await session.commit()
                        
                        logger.info(f"视频处理完成: video_id={video_id}, "
                                  f"检测到 {engine.get_status()['confirmed_count']} 个缺陷")
            else:
                raise Exception("引擎启动失败")
                
        except Exception as e:
            logger.exception(f"离线处理失败: video_id={video_id}")
            
            # 更新失败状态
            try:
                async with SessionLocal() as session:
                    video = await session.get(Video, video_id)
                    if video:
                        video.status = VideoStatus.FAILED
                        # 使用file_size字段存储错误信息（临时方案）
                        # 或添加新字段 error_message
                        await session.commit()
            except:
                pass
        finally:
            # 从全局任务列表移除
            if video_id in offline_tasks:
                del offline_tasks[video_id]
    
    # 运行异步任务
    await run_detection()


@router.get("/status/{video_id}")
async def get_upload_status(
    video_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    查询上传视频的处理状态和进度
    
    返回：
    - status: pending/processing/completed/failed
    - progress: 处理进度 (0-100)
    - defect_count: 已检测到的缺陷数量
    """
    video = await db.get(Video, video_id)
    if not video:
        return error("视频不存在", 404)
    
    # 获取实时进度
    progress = 0
    defect_count = 0
    
    if video_id in offline_tasks:
        engine = offline_tasks[video_id]
        progress = engine.file_progress
        status_info = engine.get_status()
        defect_count = status_info.get("confirmed_count", 0)
    else:
        # 从数据库读取
        progress = video.duration_seconds if video.status == VideoStatus.PROCESSING else (100 if video.status == VideoStatus.COMPLETED else 0)
        
        # 查询缺陷数量
        result = await db.execute(
            select(Defect).where(Defect.video_id == video_id)
        )
        defect_count = len(result.scalars().all())
    
    return success({
        "video_id": video_id,
        "roll_id": video.roll_id,
        "status": video.status.value,
        "progress": round(progress, 1),
        "defect_count": defect_count,
        "file_path": video.file_path,
        "file_size_mb": round(video.file_size / 1024 / 1024, 2) if video.file_size else 0,
        "created_at": video.started_at.isoformat() if video.started_at else None,
        "completed_at": video.completed_at.isoformat() if video.completed_at else None
    })


@router.get("/tasks")
async def list_processing_tasks(
    db: AsyncSession = Depends(get_db)
):
    """
    列出所有正在处理的任务
    """
    tasks = []
    for video_id, engine in offline_tasks.items():
        status = engine.get_status()
        tasks.append({
            "video_id": video_id,
            "roll_id": engine.roll_id,
            "progress": round(engine.file_progress, 1),
            "frames_processed": status.get("total_frames_captured", 0),
            "defects_found": status.get("confirmed_count", 0),
            "is_file_complete": engine.is_file_complete
        })
    
    return success({
        "active_tasks": len(tasks),
        "tasks": tasks
    })


@router.post("/reprocess/{video_id}")
async def reprocess_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    重新处理已上传的视频
    
    使用场景：
    - 之前处理失败，需要重试
    - 更新了AI模型，需要重新分析
    - 调整了检测阈值，需要重新跑检
    """
    video = await db.get(Video, video_id)
    if not video:
        return error("视频不存在", 404)
    
    if not os.path.exists(video.file_path):
        return error("视频文件不存在，可能已被删除", 404)
    
    # 检查是否正在处理中
    if video_id in offline_tasks:
        return error("该视频正在处理中，请勿重复提交", 400)
    
    try:
        # 清空之前的缺陷数据
        async with SessionLocal() as session:
            result = await session.execute(
                select(Defect).where(Defect.video_id == video_id)
            )
            old_defects = result.scalars().all()
            for defect in old_defects:
                await session.delete(defect)
            
            # 重置视频状态
            video.status = VideoStatus.PENDING
            video.completed_at = None
            await session.commit()
        
        # 重新启动处理
        background_tasks.add_task(
            process_uploaded_video_task,
            video.id,
            video.roll_id,
            video.file_path
        )
        
        return success({
            "message": "已重新启动处理",
            "video_id": video_id,
            "status": "processing"
        })
        
    except Exception as e:
        logger.exception("重新处理失败")
        return error(f"重新处理失败: {str(e)}", 500)


@router.delete("/cancel/{video_id}")
async def cancel_processing(
    video_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    取消正在进行的处理任务
    """
    if video_id not in offline_tasks:
        return error("该视频未在处理中", 400)
    
    try:
        # 停止引擎
        engine = offline_tasks[video_id]
        engine.stop()
        
        # 更新状态
        async with SessionLocal() as session:
            video = await session.get(Video, video_id)
            if video:
                video.status = VideoStatus.FAILED
                await session.commit()
        
        return success({"message": "处理已取消"})
        
    except Exception as e:
        return error(f"取消失败: {str(e)}", 500)


@router.post("/batch")
async def batch_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="多个视频文件"),
    roll_prefix: str = Form("", description="布卷编号前缀"),
    fabric_type: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    批量上传多个视频文件
    
    布卷编号规则：
    - 如果提供了roll_prefix，布卷编号为 {roll_prefix}_01, {roll_prefix}_02 ...
    - 否则尝试从文件名提取（去掉扩展名）
    """
    results = []
    
    for idx, file in enumerate(files, 1):
        try:
            # 确定布卷编号
            if roll_prefix:
                roll_number = f"{roll_prefix}_{idx:03d}"
            else:
                # 从文件名提取
                roll_number = os.path.splitext(file.filename)[0]
                # 清理非法字符
                roll_number = "".join(c for c in roll_number if c.isalnum() or c in "-_")
            
            # 复用单文件上传逻辑
            result = await upload_video(
                background_tasks=background_tasks,
                file=file,
                roll_number=roll_number,
                fabric_type=fabric_type,
                db=db
            )
            
            results.append({
                "filename": file.filename,
                "roll_number": roll_number,
                "success": result.get("code") == 0,
                "data": result.get("data"),
                "message": result.get("message")
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "message": str(e)
            })
    
    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    
    return success({
        "total": len(files),
        "success": success_count,
        "failed": len(files) - success_count,
        "results": results
    })
```

### 3.4 修改文件4: main.py

**位置**: `backend/app/main.py`

**添加路由导入**:

```python
from app.routers import video_upload

# ... 在app创建后添加 ...
app.include_router(video_upload.router)
```

### 3.5 修改文件5: Video模型

**位置**: `backend/app/models/video.py`

**添加字段**（可选，如果需要更详细的状态跟踪）:

```python
# 在Video类中添加以下字段（可选）
processing_progress: Mapped[float | None] = mapped_column(
    Float, 
    nullable=True, 
    comment="处理进度(0-100)"
)

error_message: Mapped[str | None] = mapped_column(
    String(500), 
    nullable=True, 
    comment="错误信息"
)
```

### 3.6 创建上传目录

在项目根目录创建：

```bash
mkdir -p backend/storage/uploaded
```

---

## 四、前端开发指南

### 4.1 新建文件1: VideoUpload.vue

**位置**: `frontend/src/views/VideoUpload.vue`

```vue
<template>
  <div class="video-upload-page">
    <el-page-header @back="goBack" content="上传视频检测" />
    
    <div class="content-wrapper">
      <!-- 左侧：上传区域 -->
      <div class="upload-section">
        <el-card class="upload-card">
          <div slot="header">
            <span>上传视频</span>
          </div>
          
          <!-- 文件上传组件 -->
          <el-upload
            ref="uploadRef"
            class="upload-area"
            drag
            :action="uploadUrl"
            :headers="uploadHeaders"
            :data="uploadForm"
            :on-success="onUploadSuccess"
            :on-error="onUploadError"
            :on-progress="onUploadProgress"
            :before-upload="beforeUpload"
            :auto-upload="false"
            accept=".mp4,.avi,.mov,.mkv"
            multiple
          >
            <i class="el-icon-upload"></i>
            <div class="el-upload__text">
              将视频文件拖到此处，或<em>点击上传</em>
            </div>
            <div class="el-upload__tip" slot="tip">
              支持格式：MP4, AVI, MOV, MKV；单个文件最大 2GB
            </div>
          </el-upload>
          
          <!-- 表单 -->
          <el-form :model="uploadForm" label-width="100px" class="upload-form">
            <el-form-item label="布卷编号" required>
              <el-input 
                v-model="uploadForm.roll_number" 
                placeholder="请输入布卷编号，如 FL20240302001"
              />
            </el-form-item>
            
            <el-form-item label="面料类型">
              <el-select v-model="uploadForm.fabric_type" placeholder="请选择" clearable>
                <el-option label="涤纶" value="涤纶" />
                <el-option label="棉布" value="棉布" />
                <el-option label="涤棉混纺" value="涤棉混纺" />
                <el-option label="真丝" value="真丝" />
                <el-option label="羊毛" value="羊毛" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="批次号">
              <el-input v-model="uploadForm.batch_number" placeholder="可选" />
            </el-form-item>
          </el-form>
          
          <!-- 操作按钮 -->
          <div class="upload-actions">
            <el-button type="primary" @click="submitUpload" :loading="uploading">
              开始上传并检测
            </el-button>
            <el-button @click="clearFiles">清空</el-button>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧：任务列表 -->
      <div class="tasks-section">
        <el-card>
          <div slot="header">
            <span>处理任务</span>
            <el-button 
              style="float: right; padding: 3px 0" 
              type="text"
              @click="refreshTasks"
            >
              刷新
            </el-button>
          </div>
          
          <el-empty v-if="processingTasks.length === 0" description="暂无处理任务" />
          
          <div v-else class="task-list">
            <div 
              v-for="task in processingTasks" 
              :key="task.video_id"
              class="task-item"
            >
              <div class="task-header">
                <span class="roll-number">{{ task.roll_number }}</span>
                <el-tag :type="getStatusType(task.status)" size="small">
                  {{ getStatusLabel(task.status) }}
                </el-tag>
              </div>
              
              <div class="task-info">
                <span class="filename">{{ task.filename }}</span>
                <span class="file-size">{{ task.file_size_mb }}MB</span>
              </div>
              
              <!-- 进度条 -->
              <div class="task-progress" v-if="task.status === 'processing'">
                <el-progress 
                  :percentage="task.progress" 
                  :status="task.progress === 100 ? 'success' : ''"
                />
                <span class="progress-text">{{ task.progress }}%</span>
              </div>
              
              <!-- 统计信息 -->
              <div class="task-stats" v-if="task.defect_count > 0">
                <i class="el-icon-warning"></i>
                已发现 {{ task.defect_count }} 个缺陷
              </div>
              
              <!-- 操作按钮 -->
              <div class="task-actions">
                <el-button 
                  v-if="task.status === 'completed'"
                  type="text"
                  size="small"
                  @click="viewResult(task)"
                >
                  查看结果
                </el-button>
                <el-button 
                  v-if="task.status === 'failed'"
                  type="text"
                  size="small"
                  @click="retryProcess(task)"
                >
                  重新处理
                </el-button>
                <el-button 
                  v-if="task.status === 'processing'"
                  type="text"
                  size="small"
                  @click="cancelProcess(task)"
                >
                  取消
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'VideoUpload',
  
  data() {
    return {
      uploadUrl: '/api/upload/video',
      uploadHeaders: {
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      uploadForm: {
        roll_number: '',
        fabric_type: '',
        batch_number: ''
      },
      uploading: false,
      uploadProgress: 0,
      processingTasks: [],
      pollingIntervals: {}  // 存储轮询定时器
    }
  },
  
  mounted() {
    // 加载历史任务（从localStorage或API）
    this.loadHistoryTasks()
  },
  
  beforeDestroy() {
    // 清理所有轮询
    Object.values(this.pollingIntervals).forEach(interval => {
      clearInterval(interval)
    })
  },
  
  methods: {
    beforeUpload(file) {
      // 验证文件类型
      const allowedTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska']
      const allowedExts = ['.mp4', '.avi', '.mov', '.mkv']
      
      const fileExt = '.' + file.name.split('.').pop().toLowerCase()
      
      if (!allowedTypes.includes(file.type) && !allowedExts.includes(fileExt)) {
        this.$message.error(`不支持的文件格式: ${file.name}`)
        return false
      }
      
      // 验证文件大小 (2GB)
      const maxSize = 2 * 1024 * 1024 * 1024
      if (file.size > maxSize) {
        this.$message.error(`文件大小超过2GB限制: ${file.name}`)
        return false
      }
      
      // 验证布卷编号
      if (!this.uploadForm.roll_number) {
        this.$message.error('请输入布卷编号')
        return false
      }
      
      return true
    },
    
    onUploadSuccess(response, file) {
      this.uploading = false
      
      if (response.code === 0) {
        this.$message.success(`${file.name} 上传成功，开始处理`)
        
        // 添加到任务列表
        const task = {
          video_id: response.data.video_id,
          roll_id: response.data.roll_id,
          roll_number: response.data.roll_number,
          filename: file.name,
          file_size_mb: response.data.file_size_mb,
          progress: 0,
          status: 'processing',
          defect_count: 0
        }
        
        this.processingTasks.unshift(task)
        this.saveHistoryTasks()
        
        // 开始轮询进度
        this.startPolling(response.data.video_id)
      } else {
        this.$message.error(response.message || '上传失败')
      }
    },
    
    onUploadError(error, file) {
      this.uploading = false
      this.$message.error(`${file.name} 上传失败: ${error.message}`)
    },
    
    onUploadProgress(event, file) {
      this.uploadProgress = Math.round(event.percent)
    },
    
    submitUpload() {
      if (!this.uploadForm.roll_number) {
        this.$message.error('请输入布卷编号')
        return
      }
      
      this.uploading = true
      this.$refs.uploadRef.submit()
    },
    
    clearFiles() {
      this.$refs.uploadRef.clearFiles()
      this.uploadForm = {
        roll_number: '',
        fabric_type: '',
        batch_number: ''
      }
    },
    
    startPolling(videoId) {
      // 立即查询一次
      this.pollStatus(videoId)
      
      // 每3秒轮询一次
      const interval = setInterval(() => {
        this.pollStatus(videoId)
      }, 3000)
      
      this.pollingIntervals[videoId] = interval
    },
    
    async pollStatus(videoId) {
      try {
        const res = await this.$http.get(`/upload/status/${videoId}`)
        
        if (res.data.code === 0) {
          const data = res.data.data
          const task = this.processingTasks.find(t => t.video_id === videoId)
          
          if (task) {
            task.progress = Math.round(data.progress)
            task.status = data.status
            task.defect_count = data.defect_count
            
            // 处理完成或失败，停止轮询
            if (['completed', 'failed'].includes(data.status)) {
              clearInterval(this.pollingIntervals[videoId])
              delete this.pollingIntervals[videoId]
              this.saveHistoryTasks()
              
              if (data.status === 'completed') {
                this.$notify.success({
                  title: '处理完成',
                  message: `${task.roll_number} 检测完成，发现 ${task.defect_count} 个缺陷`
                })
              }
            }
          }
        }
      } catch (e) {
        console.error('轮询状态失败:', e)
      }
    },
    
    viewResult(task) {
      this.$router.push({
        path: `/playback/${task.roll_id}`,
        query: { 
          videoId: task.video_id,
          source: 'upload'
        }
      })
    },
    
    async retryProcess(task) {
      try {
        const res = await this.$http.post(`/upload/reprocess/${task.video_id}`)
        
        if (res.data.code === 0) {
          this.$message.success('已重新启动处理')
          task.status = 'processing'
          task.progress = 0
          task.defect_count = 0
          this.startPolling(task.video_id)
        }
      } catch (e) {
        this.$message.error('重新处理失败')
      }
    },
    
    async cancelProcess(task) {
      try {
        await this.$http.delete(`/upload/cancel/${task.video_id}`)
        this.$message.success('处理已取消')
        task.status = 'failed'
        clearInterval(this.pollingIntervals[task.video_id])
        delete this.pollingIntervals[task.video_id]
      } catch (e) {
        this.$message.error('取消失败')
      }
    },
    
    getStatusType(status) {
      const map = {
        'pending': 'info',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger'
      }
      return map[status] || 'info'
    },
    
    getStatusLabel(status) {
      const map = {
        'pending': '等待中',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '失败'
      }
      return map[status] || status
    },
    
    loadHistoryTasks() {
      // 从localStorage加载历史任务
      const saved = localStorage.getItem('upload_tasks')
      if (saved) {
        try {
          this.processingTasks = JSON.parse(saved)
          
          // 对进行中的任务恢复轮询
          this.processingTasks.forEach(task => {
            if (task.status === 'processing') {
              this.startPolling(task.video_id)
            }
          })
        } catch (e) {
          console.error('加载历史任务失败:', e)
        }
      }
    },
    
    saveHistoryTasks() {
      // 保存到localStorage（只保留最近20个）
      const toSave = this.processingTasks.slice(0, 20)
      localStorage.setItem('upload_tasks', JSON.stringify(toSave))
    },
    
    refreshTasks() {
      this.processingTasks.forEach(task => {
        if (task.status === 'processing') {
          this.pollStatus(task.video_id)
        }
      })
      this.$message.success('已刷新')
    },
    
    goBack() {
      this.$router.back()
    }
  }
}
</script>

<style scoped lang="scss">
.video-upload-page {
  padding: 20px;
  
  .content-wrapper {
    display: flex;
    gap: 20px;
    margin-top: 20px;
  }
  
  .upload-section {
    flex: 1;
  }
  
  .tasks-section {
    width: 400px;
  }
  
  .upload-card {
    .upload-area {
      margin-bottom: 20px;
      
      /deep/ .el-upload {
        width: 100%;
      }
      
      /deep/ .el-upload-dragger {
        width: 100%;
        height: 200px;
      }
    }
    
    .upload-form {
      margin-bottom: 20px;
    }
    
    .upload-actions {
      text-align: center;
    }
  }
  
  .task-list {
    .task-item {
      padding: 15px;
      border-bottom: 1px solid #ebeef5;
      
      &:last-child {
        border-bottom: none;
      }
      
      .task-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        
        .roll-number {
          font-weight: bold;
          color: #303133;
        }
      }
      
      .task-info {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: #909399;
        margin-bottom: 10px;
        
        .filename {
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
      
      .task-progress {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
        
        .el-progress {
          flex: 1;
        }
        
        .progress-text {
          font-size: 12px;
          color: #606266;
          min-width: 40px;
        }
      }
      
      .task-stats {
        font-size: 12px;
        color: #e6a23c;
        margin-bottom: 8px;
        
        i {
          margin-right: 5px;
        }
      }
      
      .task-actions {
        text-align: right;
      }
    }
  }
}
</style>
```

### 4.2 修改文件2: 路由配置

**位置**: `frontend/src/router/index.js`

```javascript
{
  path: '/upload',
  name: 'VideoUpload',
  component: () => import('@/views/VideoUpload.vue'),
  meta: { 
    title: '上传视频检测',
    requiresAuth: true
  }
}
```

### 4.3 修改文件3: 导航菜单

**位置**: `frontend/src/layout/components/Sidebar.vue` 或相关菜单配置

```javascript
{
  title: '视频检测',
  icon: 'el-icon-video-camera',
  children: [
    {
      title: '实时监控',
      path: '/monitor'
    },
    {
      title: '上传视频检测',
      path: '/upload'
    }
  ]
}
```

---

## 五、数据库变更

### 5.1 Video表字段更新（可选）

如果需要在数据库中跟踪处理进度和错误信息：

```sql
-- 添加处理进度字段
ALTER TABLE videos ADD COLUMN processing_progress FLOAT DEFAULT 0;

-- 添加错误信息字段
ALTER TABLE videos ADD COLUMN error_message VARCHAR(500);
```

或者在SQLAlchemy模型中添加（见3.5节）

---

## 六、测试清单

### 6.1 功能测试

| 测试项 | 测试步骤 | 预期结果 |
|--------|----------|----------|
| 上传MP4文件 | 选择MP4文件，填写布卷编号，点击上传 | 上传成功，开始处理，进度更新 |
| 上传AVI文件 | 选择AVI文件 | 上传成功，正常处理 |
| 上传大文件 | 选择1.5GB视频 | 上传成功，处理正常 |
| 上传超大文件 | 选择3GB视频 | 提示超过大小限制 |
| 上传非视频文件 | 选择.jpg文件 | 提示格式不支持 |
| 空布卷编号 | 不填布卷编号直接上传 | 提示请输入布卷编号 |
| 重复布卷编号 | 使用已存在的布卷编号 | 关联到现有布卷，清空旧缺陷 |
| 查看处理结果 | 点击已完成任务的"查看结果" | 跳转到回放页面 |
| 重新处理 | 点击失败任务的"重新处理" | 重新开始检测 |
| 取消处理 | 点击进行中的"取消" | 任务停止，状态变失败 |

### 6.2 性能测试

| 测试项 | 测试条件 | 预期结果 |
|--------|----------|----------|
| 长视频处理 | 30分钟视频 | 正常处理完成，内存不溢出 |
| 并发上传 | 同时上传3个视频 | 都能正常处理，不互相干扰 |
| 进度更新 | 观察进度条 | 每3秒更新，数值准确 |
| 后台稳定性 | 处理10个视频 | 无内存泄漏，无崩溃 |

### 6.3 异常测试

| 测试项 | 测试步骤 | 预期结果 |
|--------|----------|----------|
| 文件损坏 | 上传损坏的视频文件 | 检测失败，状态变failed |
| 磁盘满 | 磁盘空间不足时上传 | 提示上传失败 |
| 处理中断 | 处理过程中重启服务器 | 任务丢失（后续可优化为持久化） |
| 网络中断 | 上传过程中断网 | 上传失败，可重新上传 |

---

## 七、部署注意事项

### 7.1 目录权限

确保以下目录存在并有写权限：

```bash
mkdir -p backend/storage/uploaded
chmod 755 backend/storage/uploaded
```

### 7.2 上传大小限制

如果使用Nginx反向代理，需要调整配置：

```nginx
# nginx.conf
client_max_body_size 2G;
```

### 7.3 临时文件清理

建议添加定时任务清理上传目录：

```python
# 添加到定期任务（Celery Beat或系统cron）
@celery.task
def cleanup_old_uploads(days=30):
    """清理30天前的上传文件"""
    import os
    from datetime import datetime, timedelta
    
    cutoff = datetime.now() - timedelta(days=days)
    upload_dir = "storage/uploaded/"
    
    for filename in os.listdir(upload_dir):
        filepath = os.path.join(upload_dir, filename)
        file_time = datetime.fromtimestamp(os.path.getctime(filepath))
        
        if file_time < cutoff:
            os.remove(filepath)
            logger.info(f"清理旧文件: {filename}")
```

---

## 八、接口汇总

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 上传视频 | POST | `/api/upload/video` | 上传并启动离线检测 |
| 查询状态 | GET | `/api/upload/status/{video_id}` | 获取处理状态和进度 |
| 任务列表 | GET | `/api/upload/tasks` | 列出所有正在处理的任务 |
| 重新处理 | POST | `/api/upload/reprocess/{video_id}` | 重新分析已上传视频 |
| 取消处理 | DELETE | `/api/upload/cancel/{video_id}` | 取消正在进行的任务 |
| 批量上传 | POST | `/api/upload/batch` | 一次性上传多个视频 |

---

## 九、已知限制与后续优化

### 9.1 当前限制

1. **任务不持久化**: 服务器重启会丢失正在处理的任务状态
2. **单机处理**: 不支持分布式处理大视频
3. **无断点续传**: 上传失败需要重新上传
4. **无通知机制**: 处理完成不会主动通知用户（需要轮询）

### 9.2 后续优化方向

1. **任务持久化**: 使用Redis存储任务状态，支持断点续处理
2. **WebSocket通知**: 处理完成主动推送给前端
3. **分片上传**: 支持超大视频的分片上传
4. **分布式处理**: 将视频分片分配给多个Worker处理
5. **断点续处理**: 支持从上次中断的帧继续处理

---

## 十、开发时间安排

| 阶段 | 任务 | 工作量 | 备注 |
|------|------|--------|------|
| Day 1 | 后端：FileCamera实现 | 0.5天 | 扩展video_capture.py |
| Day 1 | 后端：CascadeEngine扩展 | 0.5天 | 支持文件模式 |
| Day 2 | 后端：上传API开发 | 1天 | video_upload.py完整接口 |
| Day 3 | 前端：上传页面开发 | 1天 | VideoUpload.vue完整功能 |
| Day 4 | 前端：任务列表+轮询 | 0.5天 | 进度展示 |
| Day 4 | 集成测试 | 0.5天 | 联调测试 |
| Day 5 | Bug修复+优化 | 0.5天 | 边界情况处理 |
| Day 5 | 文档+部署 | 0.5天 | 更新部署文档 |
| **总计** | | **5天** | 单人开发 |

---

**文档结束**

如有疑问，请联系项目负责人。
