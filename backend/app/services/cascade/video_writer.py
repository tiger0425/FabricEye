"""
FabricEye 级联检测引擎 - 异步视频写入器
使用独立线程避免阻塞主采集循环。
"""

import threading
from queue import Queue
from typing import Tuple

import cv2


class AsyncVideoWriter:
    """异步视频写入器，使用独立线程避免阻塞主采集循环。"""
    
    def __init__(self, filename: str, fourcc, fps: float, frame_size: Tuple[int, int]):
        self.writer = cv2.VideoWriter(filename, fourcc, fps, frame_size)
        self.frame_queue = Queue(maxsize=300)
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.worker_thread.start()

    def _write_loop(self):
        """写入线程主循环。"""
        while not self.stop_event.is_set() or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=0.1)
                self.writer.write(frame)
                self.frame_queue.task_done()
            except:
                continue
        self.writer.release()

    def write(self, frame):
        """写入帧（非阻塞）。"""
        try:
            self.frame_queue.put_nowait(frame)
        except:
            pass

    def release(self):
        """释放资源。"""
        self.stop_event.set()
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
