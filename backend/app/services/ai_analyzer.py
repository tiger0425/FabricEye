import numpy as np
import logging
from typing import List, Dict, Any, Optional
import cv2
import base64
import json
import asyncio
import aiohttp
import time
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class AIAnalyzerService:
    """
    AI 分析服务类
    支持多种分析提供者：Mock, Kimi (Moonshot), Qwen (DashScope), Cascade
    """
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self.is_loaded = False

    def load_model(self) -> bool:
        """
        加载模型或初始化 API 客户端。
        """
        logger.info(f"Initializing AI Analyzer with provider: {self.provider}")
        if self.provider == "cascade":
            if not settings.QWEN_API_KEY:
                print("!!! ERROR: QWEN_API_KEY is missing, falling back to mock !!!", flush=True)
                self.provider = "mock"
            else:
                print(f"--- AI Analyzer: Using REAL Cascade mode with Key {settings.QWEN_API_KEY[:5]}... ---", flush=True)
        
        self.is_loaded = True
        return True

    def analyze_with_flash(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        同步接口：使用 Qwen3.5 Flash 模型快速扫描全帧。
        """
        try:
            if self.provider == "mock" or not settings.QWEN_API_KEY:
                return self._mock_analysis(frame)

            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._analyze_with_qwen_flash(frame))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"analyze_with_flash failed: {e}")
            return []

    async def _analyze_with_qwen_flash(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        使用 Qwen3.5 Flash 模型进行快速缺陷初筛。
        """
        # 1. 编码图像
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        base64_image = base64.b64encode(buffer).decode("utf-8")

        # 2. 构造请求
        url = f"{settings.QWEN_API_BASE_URL}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.QWEN_API_KEY}"
        }

        system_prompt = "你是工业验布AI。快速扫描布匹图像，检测缺陷。"
        user_prompt = (
            "快速扫描这张布匹图像，检测是否存在缺陷（破洞、污渍、断经、断纬、色差等）。\n"
            "返回JSON格式：\n"
            '{"has_defect": true/false, "defects": [{"type": "hole", "severity": "moderate", '
            '"bbox": [xmin, ymin, xmax, ymax], "confidence": 0.85}]}\n'
            "bbox坐标归一化到[0, 1000]。如果没有缺陷，返回 "
            '{"has_defect": false, "defects": []}。'
        )

        payload = {
            "model": settings.PRIMARY_MODEL,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 512
        }

        # 3. 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"!!! QWEN API ERROR (Flash): {response.status} - {text} !!!", flush=True)
                    return []
                
                result = await response.json()
                content = result['choices'][0]['message']['content']
                print(f"--- QWEN Flash RAW: {content[:500]} ---", flush=True)
                print(f"--- QWEN API SUCCESS (Flash): Received response ---", flush=True)
                print(f"--- QWEN API SUCCESS (Flash): Received response ---", flush=True)
                content = result['choices'][0]['message']['content']

        # 4. 解析响应 - 坐标转换已在 _parse_ai_response 中处理
        defects = self._parse_ai_response(content, frame.shape)

        # 5. 补充 timestamp
        now = datetime.utcnow().isoformat()
        for d in defects:
            if 'timestamp' not in d:
                d['timestamp'] = now

        return defects

    def analyze_with_plus(self, roi_crop: np.ndarray) -> List[Dict[str, Any]]:
        """
        同步接口：使用 Qwen3.5 Plus 模型对裁剪区域进行精确验证。
        """
        try:
            if self.provider == "mock" or not settings.QWEN_API_KEY:
                return []

            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._analyze_with_qwen_plus(roi_crop))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"analyze_with_plus failed: {e}")
            return []

    async def _analyze_with_qwen_plus(self, roi_crop: np.ndarray) -> List[Dict[str, Any]]:
        """
        使用 Qwen3.5 Plus 模型对裁剪区域进行精确缺陷验证。
        """
        # 1. 编码图像
        _, buffer = cv2.imencode(".jpg", roi_crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
        base64_image = base64.b64encode(buffer).decode("utf-8")

        # 2. 构造请求
        url = f"{settings.QWEN_API_BASE_URL}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.QWEN_API_KEY}"
        }

        system_prompt = "你是工业验布专家AI。请仔细分析裁剪区域中的布匹缺陷，给出精确判断。"
        user_prompt = (
            "这是从布匹检测系统裁剪出的疑似缺陷区域。请仔细分析：\n"
            "1. 是否确实存在缺陷？\n"
            "2. 如果有，缺陷类型是什么？(hole/stain/color_variance/warp_break/weft_break)\n"
            "3. 严重程度？(minor/moderate/severe)\n"
            "4. 置信度（0.0-1.0）\n"
            "\n"
            '返回JSON列表格式：[{"type": "...", "severity": "...", "confidence": 0.95}]\n'
            "如果不是缺陷，返回空列表 []。"
        )

        payload = {
            "model": settings.SECONDARY_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.2,
            "max_tokens": 1024
        }

        # 3. 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"!!! QWEN API ERROR (Plus): {response.status} - {text} !!!", flush=True)
                    return []
                
                result = await response.json()
                content = result['choices'][0]['message']['content']
                print(f"--- QWEN Plus RAW CONTENT: {content} ---", flush=True)
                print(f"--- QWEN API SUCCESS (Plus): Received response ---", flush=True)
                print(f"--- QWEN API SUCCESS (Plus): Received response ---", flush=True)
                content = result['choices'][0]['message']['content']

        # 4. 解析响应
        defects = self._parse_ai_response(content, roi_crop.shape)

        # 5. 补充 timestamp
        now = datetime.utcnow().isoformat()
        for d in defects:
            if 'timestamp' not in d:
                d['timestamp'] = now

        return defects

    def _parse_ai_response(self, content: str, frame_shape: tuple) -> List[Dict[str, Any]]:
        """
        解析 AI 返回的文本内容为结构化数据。
        """
        try:
            brace_start = content.find('{')
            bracket_start = content.find('[')

            if brace_start != -1 and (bracket_start == -1 or brace_start < bracket_start):
                brace_end = content.rfind('}') + 1
                if brace_end > 0:
                    json_str = content[brace_start:brace_end]
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict) and 'defects' in parsed:
                        defects = parsed['defects']
                    elif isinstance(parsed, dict):
                        defects = [parsed]
                    else:
                        defects = []
                else:
                    return []
            elif bracket_start != -1:
                bracket_end = content.rfind(']') + 1
                if bracket_end == 0:
                    return []
                json_str = content[bracket_start:bracket_end]
                defects = json.loads(json_str)
            else:
                return []
            
            # 坐标处理：AI可能返回 bbox 或 location，统一处理
            # 注意：Qwen Flash返回的是像素坐标，不是归一化坐标
            h, w = frame_shape[:2]
            for d in defects:
                # 优先使用 bbox，如果没有则使用 location
                raw_loc = d.get('bbox') or d.get('location', [0, 0, 0, 0])
                if len(raw_loc) == 4 and not all(v == 0 for v in raw_loc):
                    # 检查是否是归一化坐标（如果最大值 > 图像尺寸）
                    if max(raw_loc) > max(w, h):
                        # 归一化坐标 -> 像素
                        d['location'] = [
                            int(raw_loc[0] * w / 1000),
                            int(raw_loc[1] * h / 1000),
                            int(raw_loc[2] * w / 1000),
                            int(raw_loc[3] * h / 1000)
                        ]
                    else:
                        # 已经是像素坐标
                        d['location'] = [int(raw_loc[0]), int(raw_loc[1]), int(raw_loc[2]), int(raw_loc[3])]
                # 删除 bbox 字段避免重复
                if 'bbox' in d:
                    del d['bbox']
                d['timestamp'] = datetime.utcnow().isoformat()
            
            return defects
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}. Content: {content[:100]}...")
            return []

    def _mock_analysis(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """模拟检测逻辑"""
        if np.random.random() > 0.95:
            return [{
                "type": "stain",
                "severity": "minor",
                "location": [100, 100, 50, 50],
                "confidence": 0.8,
                "timestamp": datetime.utcnow().isoformat()
            }]
        return []
