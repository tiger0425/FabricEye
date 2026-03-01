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
    支持多种分析提供者：Mock, Kimi (Moonshot), Qwen (DashScope), DeepSeek
    """
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self.is_loaded = False
        self.session: Optional[aiohttp.ClientSession] = None

    def load_model(self) -> bool:
        """
        加载模型或初始化 API 客户端。
        对于 API 提供者，这只是确认配置是否正确。
        """
        logger.info(f"Initializing AI Analyzer with provider: {self.provider}")
        if self.provider == "mock":
            self.is_loaded = True
            return True
        # cascade 模式使用 QWEN_API_KEY，其他模式使用 AI_API_KEY
        if self.provider == "cascade":
            if not settings.QWEN_API_KEY:
                logger.error("QWEN_API_KEY is missing for cascade provider")
                self.provider = "mock"
                self.is_loaded = True
                return True
        elif not settings.AI_API_KEY:
            logger.error(f"AI_API_KEY is missing for provider {self.provider}")
            self.provider = "mock"
            self.is_loaded = True
            return True

        self.is_loaded = True
        return True

    async def analyze_frame_async(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        异步分析视频帧。
        """
        if not self.is_loaded:
            return []

        if self.provider == "mock":
            return self._mock_analysis(frame)
        
        try:
            if self.provider == "kimi":
                return await self._analyze_with_kimi(frame)
            elif self.provider == "qwen":
                return await self._analyze_with_qwen(frame)
            else:
                return self._mock_analysis(frame)
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            return []

    def analyze_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        同步分析接口 (为了兼容现有的多线程模式)。
        使用 new_event_loop 避免与已有事件循环冲突。
        """
        if self.provider == "mock":
            return self._mock_analysis(frame)

        # 对于需要网络请求的 API，创建独立事件循环
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.analyze_frame_async(frame))
        except Exception as e:
            logger.error(f"Sync call to analyze_frame failed: {e}")
            return []
        finally:
            loop.close()

    async def _analyze_with_kimi(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        使用 Kimi (Moonshot) Vision API 进行分析。
        """
        # 1. 编码图像
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        base64_image = base64.b64encode(buffer).decode("utf-8")

        # 2. 构造请求
        url = f"{settings.AI_API_BASE_URL}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.AI_API_KEY}"
        }
        
        prompt = (
            "你是一个工业验布专家。请识别图中布匹的缺陷（如破洞、污渍、断经、断纬、色差等）。"
            "如果有缺陷，请返回 JSON 格式列表。每个元素包含: "
            "'type' (类型, 英文: hole, stain, warp_break, weft_break, color_variance), "
            "'severity' (严重程度: minor, moderate, severe), "
            "'location' (坐标 [x, y, w, h], 基于 1000x1000 归一化坐标), "
            "'confidence' (置信度 0.0-1.0)。"
            "如果没有任何缺陷，返回空列表 []. 不要说废话，只返回 JSON。"
        )

        payload = {
            "model": settings.AI_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.2
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Kimi API error: {response.status} - {text}")
                    return []
                
                result = await response.json()
                content = result['choices'][0]['message']['content']
                return self._parse_ai_response(content, frame.shape)

    async def _analyze_with_qwen(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        使用 Qwen (DashScope) Vision API 进行分析 (待实现具体细节)。
        """
        # 逻辑类似 Kimi，只是 endpoint 和 model 不同
        logger.warning("Qwen analyzer is partially implemented. Using Kimi logic as placeholder.")
        return await self._analyze_with_kimi(frame)

    def analyze_with_flash(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        同步接口：使用 Qwen3-VL Flash 模型快速扫描全帧。
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
        使用 Qwen3-VL Flash 模型进行快速缺陷初筛。
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
            "model": settings.QWEN_FLASH_MODEL,
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
                    logger.error(f"Qwen Flash API error: {response.status} - {text}")
                    return []

                result = await response.json()
                content = result['choices'][0]['message']['content']

        # 4. 解析响应
        defects = self._parse_ai_response(content, frame.shape)

        # 5. bbox 从 1000-scale 转为像素坐标（_parse_ai_response 已处理 location）
        #    补充 timestamp
        now = datetime.utcnow().isoformat()
        for d in defects:
            if 'timestamp' not in d:
                d['timestamp'] = now
            # 如果原始返回含 bbox 而非 location，做转换
            if 'bbox' in d and 'location' not in d:
                h, w = frame.shape[:2]
                bbox = d.pop('bbox')
                if len(bbox) == 4:
                    d['location'] = [
                        int(bbox[0] * w / 1000),
                        int(bbox[1] * h / 1000),
                        int(bbox[2] * w / 1000),
                        int(bbox[3] * h / 1000)
                    ]

        return defects

    def analyze_with_plus(self, roi_crop: np.ndarray) -> List[Dict[str, Any]]:
        """
        同步接口：使用 Qwen3-VL Plus 模型对裁剪区域进行精确验证。
        """
        try:
            if self.provider == "mock" or not settings.QWEN_API_KEY:
                # Mock 模式返回高置信度结果
                if np.random.random() > 0.90:
                    defect_types = ["hole", "stain", "color_variance", "warp_break", "weft_break"]
                    severities = ["minor", "moderate", "severe"]
                    return [{
                        "type": np.random.choice(defect_types),
                        "severity": np.random.choice(severities),
                        "confidence": float(np.random.uniform(0.9, 0.99)),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
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
        使用 Qwen3-VL Plus 模型对裁剪区域进行精确缺陷验证。
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
            "model": settings.QWEN_PLUS_MODEL,
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
                    logger.error(f"Qwen Plus API error: {response.status} - {text}")
                    return []

                result = await response.json()
                content = result['choices'][0]['message']['content']

        # 4. 解析响应（ROI 裁剪区域无需坐标转换）
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
            # 尝试解析 {"has_defect": ..., "defects": [...]} 格式
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
            
            # 坐标转换 (归一化 -> 像素)
            h, w = frame_shape[:2]
            for d in defects:
                loc = d.get('location', [0, 0, 0, 0])
                if len(loc) == 4:
                    d['location'] = [
                        int(loc[0] * w / 1000),
                        int(loc[1] * h / 1000),
                        int(loc[2] * w / 1000),
                        int(loc[3] * h / 1000)
                    ]
                d['timestamp'] = datetime.utcnow().isoformat()
            
            return defects
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}. Content: {content[:100]}...")
            return []

    def _mock_analysis(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """模拟检测逻辑"""
        if np.random.random() > 0.90:  # 降低频率，使调试更清晰
            defect_types = ["hole", "stain", "color_variance", "warp_break", "weft_break"]
            severities = ["minor", "moderate", "severe"]
            d_type = np.random.choice(defect_types)
            severity = np.random.choice(severities)
            
            return [{
                "type": d_type,
                "severity": severity,
                "location": [
                    int(np.random.randint(0, frame.shape[1]-50)),
                    int(np.random.randint(0, frame.shape[0]-50)),
                    50, 50
                ],
                "confidence": float(np.random.uniform(0.8, 0.99)),
                "timestamp": datetime.utcnow().isoformat()
            }]
        return []
