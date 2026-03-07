"""
FabricEye 测试数据注入脚本

用于生成一个包含模拟四分制评分的验布报告，方便前端调试。
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from app.core.database import SessionLocal
from app.models.roll import Roll, RollStatus
from app.models.defect import Defect, DefectType, DefectSeverity

# 模拟快照图片目录
SNAPSHOT_BASE = str(Path(__file__).parent / "snapshots" / "defects")

async def inject_mock_data():
    from app.core.database import create_tables
    await create_tables()
    async with SessionLocal() as session:
        # 1. 创建模拟布卷
        roll = Roll(
            roll_number=f"TEST_4POINT_{datetime.now().strftime('%H%M%S')}",
            fabric_type="棉麻混纺",
            batch_number="BATCH-TEST",
            length_meters=50.0,
            width_cm=160.0,  # 约 63 英寸
            status=RollStatus.COMPLETED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(roll)
        await session.commit()
        await session.refresh(roll)

        print(f"✅ 创建模拟布卷成功: ID={roll.id}, 编号={roll.roll_number}")

        # 2. 插入测试缺陷（严重缺陷带模拟截图路径）
        mock_defects = [
            # 1分缺陷 (<= 7.5cm)  — 轻微，无截图
            {"type": DefectType.STAIN,       "severity": DefectSeverity.MINOR,    "len": 1.5,  "pos_m": 1.25,  "snap": None},
            {"type": DefectType.COLOR_VARIANCE, "severity": DefectSeverity.MINOR, "len": 5.0,  "pos_m": 8.50,  "snap": None},
            # 2分缺陷 (7.5 - 15cm) — 中等，无截图
            {"type": DefectType.WEFT_BREAK,  "severity": DefectSeverity.MODERATE, "len": 12.0, "pos_m": 15.30, "snap": None},
            # 3分缺陷 (15 - 23cm) — 严重，有截图
            {"type": DefectType.WARP_BREAK,  "severity": DefectSeverity.SEVERE,   "len": 20.0, "pos_m": 22.15,
             "snap": os.path.join(SNAPSHOT_BASE, "defect_warp_20cm.jpg")},
            # 4分缺陷 (> 23cm) — 严重，有截图
            {"type": DefectType.STAIN,       "severity": DefectSeverity.SEVERE,   "len": 35.0, "pos_m": 28.90,
             "snap": os.path.join(SNAPSHOT_BASE, "defect_stain_35cm.jpg")},
            # 破洞缺陷 — 严重，有截图
            {"type": DefectType.HOLE,        "severity": DefectSeverity.SEVERE,   "len": 0.5,  "pos_m": 35.45,
             "snap": os.path.join(SNAPSHOT_BASE, "defect_hole_01.jpg")},
            {"type": DefectType.HOLE,        "severity": DefectSeverity.SEVERE,   "len": 1.5,  "pos_m": 42.60,
             "snap": os.path.join(SNAPSHOT_BASE, "defect_hole_02.jpg")},
        ]

        from app.services.four_point_scoring import FourPointScorer
        scorer = FourPointScorer()

        for d in mock_defects:
            point_score = scorer.score_defect(d["type"].value, d["len"])
            defect = Defect(
                roll_id=roll.id,
                defect_type=d["type"],
                defect_type_cn=d["type"].value,
                severity=d["severity"],
                confidence=0.95,
                defect_length_cm=d["len"],
                point_score=point_score,
                bbox_x1=0,
                bbox_y1=0,
                bbox_x2=0,
                bbox_y2=0,
                position_meter=d["pos_m"],
                snapshot_path=d["snap"],
                timestamp=0.0
            )
            session.add(defect)

        await session.commit()
        print(f"✅ 插入了 {len(mock_defects)} 个测试缺陷")
        severe_count = sum(1 for d in mock_defects if d["snap"])
        print(f"   其中 {severe_count} 个严重缺陷已关联模拟截图")

        print(f"\n访问接口查看报告：")
        print(f"  JSON: http://localhost:8000/api/rolls/{roll.id}/report")
        print(f"  PDF:  http://localhost:8000/api/rolls/{roll.id}/report/pdf")
        print(f"  前端: http://localhost:5173/reports")

if __name__ == "__main__":
    asyncio.run(inject_mock_data())

