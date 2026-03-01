from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Optional
import os
from fastapi.responses import FileResponse

from app.core.database import get_db
from app.models.defect import Defect, DefectType, DefectTypeCN, DefectSeverity, ReviewResult
from app.utils.response import success, error

router = APIRouter(
    prefix="/defects",
    tags=["Defects"],
    responses={404: {"description": "Not found"}},
)

def _serialize_defect(d: Defect) -> dict:
    """Convert a Defect ORM instance to a plain dict for JSON response."""
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
        "imageUrl": f"/api/defects/image/{d.id}"
    }

@router.get("/")
async def read_defects(
    rollId: int = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * pageSize
    query = select(Defect).order_by(Defect.detected_at.desc())
    count_stmt = select(func.count()).select_from(Defect)

    if rollId is not None:
        query = query.where(Defect.roll_id == rollId)
        count_stmt = count_stmt.where(Defect.roll_id == rollId)

    if severity is not None:
        try:
            sev_enum = DefectSeverity(severity.lower())
            query = query.where(Defect.severity == sev_enum)
            count_stmt = count_stmt.where(Defect.severity == sev_enum)
        except ValueError:
            pass

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    query = query.offset(skip).limit(pageSize)
    result = await db.execute(query)
    defects = result.scalars().all()

    return success({
        "list": [_serialize_defect(d) for d in defects],
        "total": total,
    })

@router.get("/stats")
async def get_defect_stats(
    rollId: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    base_filter = []
    if rollId is not None:
        base_filter.append(Defect.roll_id == rollId)

    total_stmt = select(func.count()).select_from(Defect)
    for f in base_filter:
        total_stmt = total_stmt.where(f)
    total = (await db.execute(total_stmt)).scalar()

    sev_stmt = (
        select(Defect.severity, func.count())
        .group_by(Defect.severity)
    )
    for f in base_filter:
        sev_stmt = sev_stmt.where(f)
    sev_result = await db.execute(sev_stmt)
    sev_counts = {row[0]: row[1] for row in sev_result.all()}

    return success({
        "total": total,
        "critical": sev_counts.get(DefectSeverity.SEVERE, 0),
        "major": sev_counts.get(DefectSeverity.MODERATE, 0),
        "minor": sev_counts.get(DefectSeverity.MINOR, 0),
    })

@router.get("/categories")
async def get_defect_categories(
    rollId: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Defect.defect_type, func.count())
        .group_by(Defect.defect_type)
    )
    if rollId is not None:
        query = query.where(Defect.roll_id == rollId)

    result = await db.execute(query)
    rows = result.all()
    total = sum(row[1] for row in rows)

    categories = []
    for defect_type_enum, count in rows:
        percentage = round((count / total * 100), 2) if total > 0 else 0.0
        categories.append({
            "type": defect_type_enum.value if defect_type_enum else "unknown",
            "name": DefectTypeCN.get_cn(defect_type_enum) if defect_type_enum else "未知",
            "count": count,
            "percentage": percentage,
        })

    return success(categories)

@router.get("/image/{defect_id}")
async def get_defect_image(defect_id: str, db: AsyncSession = Depends(get_db)):
    """获取缺陷截图 - 支持数据库ID或级联临时ID(以cid_开头)"""
    # 检查是否是级联临时ID
    if defect_id.startswith("cid_"):
        image_path = os.path.join(os.getcwd(), "storage", "debug_crops", f"{defect_id}.jpg")
        if os.path.exists(image_path):
            return FileResponse(image_path, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail=f"临时图片不存在: {image_path}")

    # 否则查询数据库
    try:
        did = int(defect_id)
        result = await db.execute(select(Defect).where(Defect.id == did))
        defect = result.scalar_one_or_none()
        
        if not defect or not defect.snapshot_path:
            raise HTTPException(status_code=404, detail="缺陷或截图不存在")
        
        # 使用绝对路径
        image_path = os.path.abspath(defect.snapshot_path)
        if os.path.exists(image_path):
            return FileResponse(image_path, media_type="image/jpeg")
    except ValueError:
        pass
        
    raise HTTPException(status_code=404, detail="图片文件不存在")
@router.post("/{defect_id}/mark")
async def mark_defect(defect_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Defect).where(Defect.id == defect_id))
    defect = result.scalar_one_or_none()
    if defect is None:
        return error("缺陷不存在", code=404)

    result_str = data.get("result", "")
    try:
        review_result = ReviewResult(result_str)
    except ValueError:
        return error(f"无效的复核结果: {result_str}，可选值: confirmed, false_positive, uncertain")

    defect.reviewed = True
    defect.reviewed_result = review_result

    try:
        await db.commit()
        await db.refresh(defect)
    except Exception as e:
        await db.rollback()
        return error(f"标记失败: {str(e)}")

    return success(_serialize_defect(defect), message="标记成功")

@router.delete("/{defect_id}")
async def delete_defect(defect_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Defect).where(Defect.id == defect_id))
    defect = result.scalar_one_or_none()
    if defect is None:
        return error("缺陷不存在", code=404)

    await db.delete(defect)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        return error(f"删除失败: {str(e)}")

    return success(message="删除成功")
