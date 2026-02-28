from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
from typing import List, Optional, Dict
from datetime import datetime

from app.core.database import get_db
from app.models.roll import Roll, RollStatus
from app.schemas.roll import RollCreate, RollUpdate, RollResponse
from app.utils.response import success, error
from app.services.streaming import StreamingEngine

router = APIRouter(
    prefix="/rolls",
    tags=["Rolls"],
    responses={404: {"description": "Not found"}},
)

# 全局存储正在运行的引擎实例
active_engines: Dict[int, StreamingEngine] = {}

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

    # 获取总数用于分页
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
        active_engines[roll_id].stop_engine()
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
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)

    if roll_id in active_engines:
        return error("该布卷已在验布中")

    engine = StreamingEngine(roll_id)
    if engine.start_engine():
        active_engines[roll_id] = engine
        db_roll.status = RollStatus.INSPECTING
        db_roll.updated_at = datetime.utcnow()
        await db.commit()
        return success(message="已开始验布")
    else:
        return error("开启验布引擎失败，请检查摄像头连接")

@router.post("/{roll_id}/stop")
async def stop_roll_inspection(roll_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)

    if roll_id in active_engines:
        active_engines[roll_id].stop_engine()
        del active_engines[roll_id]

    db_roll.status = RollStatus.COMPLETED
    db_roll.updated_at = datetime.utcnow()
    await db.commit()
    return success(message="已停止验布")
