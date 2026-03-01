import asyncio
import io
import time
import random
import colorsys
import base64
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import numpy as np
from PIL import Image, ImageDraw

from app.core.database import get_db
from app.utils.response import success, error

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
# 根路由
@router.get("/")
async def read_videos(
    rollId: int = Query(None), 
    page: int = Query(1, ge=1), 
    pageSize: int = Query(10, ge=1), 
    db: AsyncSession = Depends(get_db)
):
    return success({
        "list": [],
        "total": 0
    })

# 特定路由必须在动态路由 {video_id} 之前
@router.get("/recordings")
async def get_recordings(rollId: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    return success([])

# 动态路由
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
    # 尝试获取真实帧
    video_service.start_capture()
    frame_arr = video_service.get_frame()
    
    if frame_arr is not None:
        _, jpeg = cv2.imencode('.jpg', frame_arr)
        frame = jpeg.tobytes()
    else:
        frame = generate_demo_frame()
    
    # 如果请求直接要图片（Accept: image/jpeg），返回原始图片
    if accept and ('image/jpeg' in accept or 'image/*' in accept):
        return StreamingResponse(
            io.BytesIO(frame),
            media_type='image/jpeg'
        )
    
    # 如果请求直接要图片（Accept: image/jpeg），返回原始图片
    if accept and 'image/jpeg' in accept:
        return StreamingResponse(
            io.BytesIO(frame),
            media_type='image/jpeg'
        )
    
    # 否则返回JSON格式
    b64 = base64.b64encode(frame).decode()
    return success({"image": f"data:image/jpeg;base64,{b64}"})

@router.get("/{video_id}")
async def read_video(video_id: int, db: AsyncSession = Depends(get_db)):
    return success({"id": video_id})
