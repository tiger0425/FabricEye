from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import random

from app.core.database import get_db
from app.models.roll import Roll, RollStatus
from app.models.defect import Defect, DefectType, DefectTypeCN, DefectSeverity
from app.schemas.roll import RollCreate, RollUpdate, RollResponse
from app.utils.response import success, error
from app.services.cascade_engine import CascadeEngine

router = APIRouter(
    prefix="/rolls",
    tags=["Rolls"],
    responses={404: {"description": "Not found"}},
)

# 全局存储正在运行的引擎实例
active_engines: Dict[int, CascadeEngine] = {}

@router.post("/")
async def create_roll(roll: RollCreate, db: AsyncSession = Depends(get_db)):
    db_roll = Roll(
        roll_number=roll.roll_number,
        fabric_type=roll.fabric_type,
        batch_number=roll.batch_number,
        length_meters=roll.length_meters,
        status=RollStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_roll)
    try:
        await db.commit()
        await db.refresh(db_roll)
    except Exception as e:
        await db.rollback()
        return error(f"创建失败: {str(e)}")
    return success(RollResponse.model_validate(db_roll))

@router.get("/")
async def list_rolls(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    status: Optional[RollStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * pageSize
    query = select(Roll).offset(skip).limit(pageSize).order_by(Roll.created_at.desc())
    if status:
        query = query.where(Roll.status == status)
    result = await db.execute(query)
    rolls = result.scalars().all()
    count_stmt = select(func.count()).select_from(Roll)
    if status:
        count_stmt = count_stmt.where(Roll.status == status)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    return success({
        "list": [RollResponse.model_validate(r) for r in rolls],
        "total": total
    })

@router.get("/{roll_id}")
async def get_roll(roll_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    roll = result.scalar_one_or_none()
    if roll is None:
        return error("布卷不存在", code=404)
    return success(RollResponse.model_validate(roll))

@router.put("/{roll_id}")
async def update_roll(roll_id: int, roll_update: RollUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    update_data = roll_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_roll, key, value)
    db_roll.updated_at = datetime.utcnow()
    try:
        await db.commit()
        await db.refresh(db_roll)
    except Exception as e:
        await db.rollback()
        return error(f"更新失败: {str(e)}")
    return success(RollResponse.model_validate(db_roll))

@router.delete("/{roll_id}")
async def delete_roll(roll_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    if roll_id in active_engines:
        active_engines[roll_id].stop()
        del active_engines[roll_id]
    await db.delete(db_roll)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        return error(f"删除失败: {str(e)}")
    return success(message="删除成功")

@router.post("/{roll_id}/start")
async def start_roll_inspection(roll_id: int, db: AsyncSession = Depends(get_db)):
    """开始验布 - 真实引擎模式"""
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    
    # 检查是否已在验布中
    if roll_id in active_engines:
        return error(f"该布卷已在验布中")
    
    try:
        # 初始化并启动级联检测引擎
        engine = CascadeEngine(roll_id)
        if not engine.start():
            return error("启动失败: 无法打开摄像头或初始化模型")
            
        active_engines[roll_id] = engine
        
        # 更新布卷状态
        db_roll.status = RollStatus.INSPECTING
        db_roll.updated_at = datetime.utcnow()
        await db.commit()
        
        return success(message="已开始验布")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error(f"启动失败: {str(e)}")

@router.post("/{roll_id}/stop")
async def stop_roll_inspection(roll_id: int, db: AsyncSession = Depends(get_db)):
    """停止验布"""
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    
    # 从活跃引擎中移除并停止
    if roll_id in active_engines:
        engine = active_engines[roll_id]
        engine.stop()
        del active_engines[roll_id]
    
    # 更新布卷状态
    db_roll.status = RollStatus.COMPLETED
    db_roll.updated_at = datetime.utcnow()
    await db.commit()
    
    return success(message="已停止验布")

@router.get("/{roll_id}/cascade-status")
async def get_cascade_status(roll_id: int):
    """获取级联状态"""
    if roll_id not in active_engines:
        return success({
            "is_running": False,
            "roll_id": roll_id,
            "status": "stopped"
        })
    
    engine = active_engines[roll_id]
    return success(engine.get_status())

@router.get("/{roll_id}/report")
async def get_roll_report(roll_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    roll = result.scalar_one_or_none()
    if roll is None:
        return error("布卷不存在", code=404)
    defects_result = await db.execute(
        select(Defect)
        .where(Defect.roll_id == roll_id)
        .order_by(Defect.detected_at.desc())
    )
    defects = defects_result.scalars().all()
    severe_count = sum(1 for d in defects if d.severity == DefectSeverity.SEVERE)
    moderate_count = sum(1 for d in defects if d.severity == DefectSeverity.MODERATE)
    minor_count = sum(1 for d in defects if d.severity == DefectSeverity.MINOR)
    type_counts: Dict[DefectType, int] = {}
    for d in defects:
        if d.defect_type is not None:
            type_counts[d.defect_type] = type_counts.get(d.defect_type, 0) + 1
    total_defects = len(defects)
    by_type = []
    for dt, count in type_counts.items():
        percentage = round((count / total_defects * 100), 2) if total_defects > 0 else 0.0
        by_type.append({
            "type": dt.value,
            "type_cn": DefectTypeCN.get_cn(dt),
            "count": count,
            "percentage": percentage,
        })
    quality_score = max(0, 100 - (severe_count * 10) - (moderate_count * 5) - (minor_count * 2))
    def _serialize_defect(d: Defect) -> dict:
        return {
            "id": d.id,
            "roll_id": d.roll_id,
            "defect_type": d.defect_type.value if d.defect_type else None,
            "defect_type_cn": d.defect_type_cn,
            "confidence": d.confidence,
            "severity": d.severity.value if d.severity else None,
            "position_meter": d.position_meter,
            "timestamp": d.timestamp,
            "bbox_x1": d.bbox_x1,
            "bbox_y1": d.bbox_y1,
            "bbox_x2": d.bbox_x2,
            "bbox_y2": d.bbox_y2,
            "snapshot_path": d.snapshot_path,
            "detected_at": d.detected_at.isoformat() if d.detected_at else None,
            "reviewed": d.reviewed,
            "reviewed_result": d.reviewed_result.value if d.reviewed_result else None,
        }
    report = {
        "roll": {
            "id": roll.id,
            "roll_number": roll.roll_number,
            "fabric_type": roll.fabric_type,
            "batch_number": roll.batch_number,
            "length_meters": roll.length_meters,
            "status": roll.status.value if roll.status else None,
            "created_at": roll.created_at.isoformat() if roll.created_at else None,
        },
        "summary": {
            "total_defects": total_defects,
            "by_severity": {
                "severe": severe_count,
                "moderate": moderate_count,
                "minor": minor_count,
            },
            "by_type": by_type,
            "quality_score": quality_score,
        },
        "defects": [_serialize_defect(d) for d in defects],
        "generated_at": datetime.utcnow().isoformat(),
    }
    return success(report)
