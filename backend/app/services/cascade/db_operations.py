"""
FabricEye 级联检测引擎 - 数据库操作
缺陷数据持久化操作。
"""

from datetime import datetime
from typing import Optional

from app.core.database import SessionLocal
from app.models.defect import Defect, DefectType, DefectTypeCN, DefectSeverity
from app.services.cascade.types import PendingDefect


async def save_defect_to_db(
    defect: PendingDefect,
    plus_confidence: float,
    snapshot_path: Optional[str],
    roll_id: int,
    video_id: Optional[int],
    timestamp: float
) -> bool:
    """
    保存确认的缺陷到数据库。
    
    Args:
        defect: 待确认缺陷对象
        plus_confidence: Plus阶段置信度
        snapshot_path: 截图路径
        roll_id: 布卷ID
        video_id: 视频ID
        timestamp: 时间戳
    
    Returns:
        是否保存成功
    """
    try:
        matched_enum = _match_defect_type(defect.defect_type)
        matched_severity = _match_severity(defect.severity)
        
        db_defect = Defect(
            roll_id=roll_id,
            video_id=video_id,
            defect_type=matched_enum,
            defect_type_cn=DefectTypeCN.get_cn(matched_enum),
            confidence=plus_confidence,
            severity=matched_severity,
            bbox_x1=defect.bbox[0],
            bbox_y1=defect.bbox[1],
            bbox_x2=defect.bbox[2],
            bbox_y2=defect.bbox[3],
            snapshot_path=snapshot_path,
            timestamp=timestamp,
            detected_at=datetime.utcnow(),
            reviewed=False
        )
        
        async with SessionLocal() as session:
            session.add(db_defect)
            await session.commit()
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save defect: {e}", flush=True)
        return False


def _match_defect_type(defect_type: str) -> DefectType:
    """匹配缺陷类型。"""
    try:
        return DefectType(defect_type.lower())
    except:
        return DefectType.STAIN


def _match_severity(severity: str) -> DefectSeverity:
    """匹配严重程度。"""
    try:
        return DefectSeverity(severity.lower())
    except:
        return DefectSeverity.MINOR
