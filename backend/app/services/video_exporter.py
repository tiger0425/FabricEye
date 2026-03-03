import cv2
import os
import threading
import numpy as np
from typing import List, Dict
from datetime import datetime
from queue import Queue

class VideoExporter:
    """视频导出服务 - 使用OpenCV绘制标记"""
    
    def __init__(self, video_path: str, defects: List[Dict], output_path: str):
        self.video_path = video_path
        self.defects = defects
        self.output_path = output_path
        self.progress = 0
        self.status = "pending"  # pending, processing, completed, failed
        self.error_message = None

    def export(self):
        """开始执行视频导出任务"""
        cap = None
        out = None
        try:
            self.status = "processing"
            
            # 1. 打开原视频
            if not os.path.exists(self.video_path):
                raise FileNotFoundError(f"Video file not found: {self.video_path}")
            
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise Exception("Could not open video source")

            # 2. 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 3. 创建输出目录并初始化 VideoWriter
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            # 优先使用 avc1 (H.264)，如果失败尝试 mp4v
            fourcc = cv2.VideoWriter.fourcc(*'avc1')
            out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                # 尝试备用编码 mp4v
                fourcc = cv2.VideoWriter.fourcc(*'mp4v')
                out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
            # 4. 预处理缺陷数据：按帧号分组
            defects_by_frame = {}
            for d in self.defects:
                timestamp = d.get('timestamp', 0)
                frame_idx = int(timestamp * fps)
                if frame_idx not in defects_by_frame:
                    defects_by_frame[frame_idx] = []
                defects_by_frame[frame_idx].append(d)

            # 5. 逐帧处理
            processed_frames = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 如果当前帧有缺陷，绘制标记
                if processed_frames in defects_by_frame:
                    frame = self._draw_defects_on_frame(frame, defects_by_frame[processed_frames])
                
                out.write(frame)
                processed_frames += 1
                
                # 更新进度
                if total_frames > 0:
                    self.progress = int((processed_frames / total_frames) * 100)

            self.status = "completed"
            return True

        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            return False
            
        finally:
            if cap:
                cap.release()
            if out:
                out.release()

    def _draw_defects_on_frame(self, frame: np.ndarray, defects: List[Dict]):
        """在帧上绘制缺陷标记"""
        for d in defects:
            # bbox 坐标 [x1, y1, x2, y2]
            bbox = d.get('bbox', [0, 0, 0, 0])
            if len(bbox) != 4:
                continue
                
            x1, y1, x2, y2 = map(int, bbox)
            severity = d.get('severity', 'minor')
            type_cn = d.get('type_cn', '未知缺陷')
            confidence = d.get('confidence', 0.0)

            # 根据 severity 选择颜色 (B, G, R)
            if severity == 'severe':
                color = (0, 0, 255)  # 红色
            elif severity == 'moderate':
                color = (0, 165, 255)  # 橙色
            else:
                color = (0, 255, 0)  # 绿色

            # 1. 绘制矩形框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 2. 准备标签
            label = f"{type_cn} {confidence:.0%}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 1
            
            # 计算文字大小
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # 3. 绘制标签背景矩形
            cv2.rectangle(frame, (x1, y1 - text_h - 10), (x1 + text_w, y1), color, -1)
            
            # 4. 绘制标签文字
            cv2.putText(frame, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
            
        return frame

# 全局任务管理器
export_tasks: Dict[str, VideoExporter] = {}

def start_export_task(task_id: str, video_path: str, defects: List[Dict], output_path: str):
    """启动导出任务"""
    exporter = VideoExporter(video_path, defects, output_path)
    export_tasks[task_id] = exporter
    
    def run_export():
        exporter.export()
    
    thread = threading.Thread(target=run_export, daemon=True)
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
