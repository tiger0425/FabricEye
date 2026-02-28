from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.utils.response import success, error

router = APIRouter(
    prefix="/defects",
    tags=["Defects"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def read_defects(
    rollId: int = Query(None), 
    page: int = Query(1, ge=1), 
    pageSize: int = Query(10, ge=1), 
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    # 占位实现
    return success({
        "list": [],
        "total": 0
    })

@router.get("/stats")
async def get_defect_stats(rollId: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    return success({
        "total": 0,
        "critical": 0,
        "major": 0,
        "minor": 0
    })

@router.get("/categories")
async def get_defect_categories(rollId: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    return success([])

@router.get("/{defect_id}")
async def read_defect(defect_id: int, db: AsyncSession = Depends(get_db)):
    return success({"id": defect_id})

@router.post("/{defect_id}/mark")
async def mark_defect(defect_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    return success(message="标记成功")

@router.delete("/{defect_id}")
async def delete_defect(defect_id: int, db: AsyncSession = Depends(get_db)):
    return success(message="删除成功")
