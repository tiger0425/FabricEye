import asyncio
import io
import time
import random
import colorsys
import base64
import uuid
import os
from datetime import datetime
from typing import List, Optional

import numpy as np
from PIL import Image, ImageDraw
import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, Header, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.utils.response import success, error
from app.models.video import Video
from app.models.defect import Defect
from app.services.video_exporter import start_export_task, get_export_status

router = APIRouter(
    prefix="/videos",
    tags=["Videos"],
    responses={404: {"description": "Not found"}},
)

# 全局帧生成器字典
active_streams = {}

def generate_demo_frame(width=640, height=480, frame_num=0):
    """生成演示帧 - 显示当前时间、帧号和动态背景"""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # 动态背景色
    hue = (frame_num * 2) % 360
    bg_color = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue/360, 0.3, 0.9))
    draw.rectangle([0, 0, width, height], fill=bg_color)
    
    # 绘制网格线模拟验布场景
    draw.line([(0, height//2), (width, height//2)], fill=(200, 200, 200), width=2)
    for i in range(0, width, 80):
        draw.line([(i, 0), (i, height)], fill=(180, 180, 180), width=1)
    
    # 绘制文字
    current_time = time.strftime('%H:%M:%S')
    text_color = (255, 255, 255)
    draw.text((20, 20), "FabricEye AI 验布系统", fill=text_color)
    draw.text((20, 50), f"帧号: {frame_num}", fill=text_color)
    draw.text((20, 80), f"时间: {current_time}", fill=text_color)
    
    # 模拟布匹移动效果
    offset = (frame_num * 3) % 100
    for i in range(5):
        y = height//2 - 30 + i * 15
        draw.rectangle([offset + i*20, y, offset + i*20 + 15, y+10], fill=(100, 150, 200))
    
    # 随机模拟检测框（偶尔显示）
    if random.random() < 0.05:
        x = random.randint(100, width-100)
        y = random.randint(100, height-100)
        draw.rectangle([x, y, x+80, y+60], outline=(255, 0, 0), width=3)
        draw.text((x, y-20), "缺陷检测", fill=(255, 0, 0))
    
    # 转换为JPEG
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', quality=85)
    img_bytes.seek(0)
    return img_bytes.getvalue()

from app.services.video_capture import VideoCaptureService
import cv2

video_service = VideoCaptureService()

async def video_stream_generator(video_id: int):
    """MJPEG流生成器 - 优先使用真实摄像头"""
    try:
        # 尝试启动摄像头
        video_service.start_capture()
        
        while True:
            if video_id not in active_streams or not active_streams[video_id]:
                break
                
            # 获取真实帧
            frame_arr = video_service.get_frame()
            
            if frame_arr is not None:
                # 编码为 JPEG
                _, jpeg = cv2.imencode('.jpg', frame_arr)
                frame = jpeg.tobytes()
            else:
                # 回退到演示帧
                frame = generate_demo_frame()
                
            # MJPEG格式: JPEG帧 + 分隔符
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            # 控制帧率 (~5 FPS)
            await asyncio.sleep(0.2)
            await asyncio.sleep(0.067)
    except asyncio.CancelledError:
        pass
    finally:
        if video_id in active_streams:
            active_streams[video_id] = False
        # 注意：这里我们不停止 capture，因为可能还有其他流在使用，或者 streaming engine 在使用
        # video_service.stop_capture()
# 视频列表 (分页)
@router.get("/")
async def read_videos(
    rollId: int = Query(None), 
    page: int = Query(1, ge=1), 
    pageSize: int = Query(10, ge=1), 
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(Video)
        if rollId:
            query = query.where(Video.roll_id == rollId)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页和排序
        query = query.order_by(Video.started_at.desc()).offset((page - 1) * pageSize).limit(pageSize)
        result = await db.execute(query)
        videos = result.scalars().all()
        
        return success({
            "list": videos,
            "total": total
        })
    except Exception as e:
        return error(str(e))

# 获取录制列表 (与 / 类似)
@router.get("/recordings")
async def get_recordings(
    rollId: Optional[int] = Query(None), 
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(Video)
        if rollId:
            query = query.where(Video.roll_id == rollId)
        
        query = query.order_by(Video.started_at.desc())
        result = await db.execute(query)
        videos = result.scalars().all()
        
        return success({
            "list": videos,
            "total": len(videos)
        })
    except Exception as e:
        return error(str(e))

# 视频流播放
@router.get("/{video_id}/play")
async def play_video(video_id: int, db: AsyncSession = Depends(get_db)):
    try:
        query = select(Video).where(Video.id == video_id)
        result = await db.execute(query)
        video = result.scalar_one_or_none()
        
        if not video:
            return error("视频未找到", code=404)
        
        if not video.file_path or not os.path.exists(video.file_path):
            return error("视频文件不存在", code=404)
            
        return FileResponse(video.file_path, media_type="video/mp4")
    except Exception as e:
        return error(str(e))

# 视频详情
@router.get("/{video_id}/detail")
async def get_video_detail(video_id: int, db: AsyncSession = Depends(get_db)):
    try:
        query = select(Video).where(Video.id == video_id)
        result = await db.execute(query)
        video = result.scalar_one_or_none()
        
        if not video:
            return error("视频未找到", code=404)
            
        return success(video)
    except Exception as e:
        return error(str(e))

# 视频缺陷时间轴
@router.get("/{video_id}/defects")
async def get_video_defects(video_id: int, db: AsyncSession = Depends(get_db)):
    try:
        # 检查视频是否存在
        video_query = select(Video).where(Video.id == video_id)
        video_result = await db.execute(video_query)
        if not video_result.scalar_one_or_none():
            return error("视频未找到", code=404)

        # 获取关联的所有缺陷
        defect_query = select(Defect).where(Defect.video_id == video_id).order_by(Defect.timestamp.asc())
        result = await db.execute(defect_query)
        defects = result.scalars().all()
        
        data = []
        for d in defects:
            data.append({
                "id": d.id,
                "type": d.defect_type,
                "typeCn": d.defect_type_cn,
                "severity": d.severity,
                "confidence": d.confidence,
                "timestamp": d.timestamp,
                "bbox": {
                    "x1": d.bbox_x1,
                    "y1": d.bbox_y1,
                    "x2": d.bbox_x2,
                    "y2": d.bbox_y2
                }
            })
            
        return success(data)
    except Exception as e:
        return error(str(e))

# MJPEG 实时流相关接口保持不变
@router.get("/{video_id}/stream")
async def get_video_stream(video_id: int):
    """获取MJPEG视频流"""
    active_streams[video_id] = True
    return StreamingResponse(
        video_stream_generator(video_id),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@router.post("/{video_id}/start")
async def start_video_stream(video_id: int, db: AsyncSession = Depends(get_db)):
    active_streams[video_id] = True
    return success(message="视频流已启动")

@router.post("/{video_id}/stop")
async def stop_video_stream(video_id: int, db: AsyncSession = Depends(get_db)):
    active_streams[video_id] = False
    return success(message="视频流已停止")

@router.get("/{video_id}/status")
async def get_video_status(video_id: int, db: AsyncSession = Depends(get_db)):
    is_active = active_streams.get(video_id, False)
    return success({"status": "connected" if is_active else "disconnected"})

@router.get("/{video_id}/snapshot")
async def get_video_snapshot(
    video_id: int, 
    db: AsyncSession = Depends(get_db),
    accept: str = Header(None)
):
    video_service.start_capture()
    frame_arr = video_service.get_frame()
    
    if frame_arr is not None:
        _, jpeg = cv2.imencode('.jpg', frame_arr)
        frame = jpeg.tobytes()
    else:
        frame = generate_demo_frame()
    
    if accept and ('image/jpeg' in accept or 'image/*' in accept):
        return StreamingResponse(
            io.BytesIO(frame),
            media_type='image/jpeg'
        )
    
    b64 = base64.b64encode(frame).decode()
    return success({"image": f"data:image/jpeg;base64,{b64}"})

@router.get("/roll/{roll_id}")
async def get_roll_videos(roll_id: int, db: AsyncSession = Depends(get_db)):
    """获取布卷的所有视频"""
    result = await db.execute(
        select(Video).where(Video.roll_id == roll_id).order_by(Video.started_at.desc())
    )
    videos = result.scalars().all()
    return success([{
        "id": v.id,
        "file_path": v.file_path,
        "duration_seconds": v.duration_seconds,
        "resolution": v.resolution,
        "fps": v.fps,
        "status": v.status.value,
        "started_at": v.started_at.isoformat() if v.started_at else None
    } for v in videos])

@router.get("/stream/{video_id}")
async def stream_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """视频流播放（支持范围请求，用于前端 <video> 标签）"""
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(404, "视频不存在")
    
    if not video.file_path or not os.path.exists(video.file_path):
        raise HTTPException(404, "视频文件不存在")
    
    return FileResponse(
        video.file_path,
        media_type="video/mp4"
    )

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
        "status": video.status.value,
        "file_size_mb": round(video.file_size / 1024 / 1024, 2) if video.file_size else 0,
        "started_at": video.started_at.isoformat() if video.started_at else None,
        "completed_at": video.completed_at.isoformat() if video.completed_at else None
    })

@router.get("/{video_id}/defects/timeline")
async def get_video_defects_timeline(
    video_id: int, 
    roll_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取视频缺陷时间轴数据
    用于前端播放器叠加缺陷标记
    """
    # 如果提供了roll_id，获取该布卷的所有缺陷
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
        # 计算相对坐标中心点作为位置
        pos_x = int((d.bbox_x1 + d.bbox_x2) / 2) if d.bbox_x1 is not None else 0
        pos_y = int((d.bbox_y1 + d.bbox_y2) / 2) if d.bbox_y1 is not None else 0
        
        timeline.append({
            "id": d.id,
            "timestamp": d.timestamp or 0,
            "duration": 2.0,
            "bbox": [d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
            "type": d.defect_type.value if d.defect_type else "unknown",
            "defectType": d.defect_type.value if d.defect_type else "unknown",
            "typeCn": d.defect_type_cn,
            "confidence": d.confidence,
            "severity": d.severity.value.lower() if d.severity else "minor",
            "position": f"({pos_x}, {pos_y})",
            "snapshot_path": d.snapshot_path,
            "imageUrl": f"/api/defects/image/{d.id}"
        })
    
    return success({
        "video_id": video_id,
        "total_defects": len(timeline),
        "defects": timeline
    })

@router.post("/{video_id}/export-marked")
async def export_marked_video(
    video_id: int,
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
    
    # 获取缺陷列表（关联到此视频的）
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
        "timestamp": d.timestamp or 0,
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

@router.get("/{video_id}/old") # 重命名旧的 read_video 避免冲突
async def read_video_old(video_id: int, db: AsyncSession = Depends(get_db)):
    return success({"id": video_id})
