from __future__ import annotations

from typing import TYPE_CHECKING

"""
FabricEye AI验布系统 - 缺陷模型
定义缺陷相关的 ORM 模型。
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Float, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.roll import Roll
    from app.models.video import Video



class DefectType(str, Enum):
    """缺陷类型枚举"""
    HOLE = "hole"                       # 破洞
    STAIN = "stain"                     # 污渍
    COLOR_VARIANCE = "color_variance"   # 色差
    WARP_BREAK = "warp_break"           # 经断
    WEFT_BREAK = "weft_break"           # 纬断


class DefectTypeCN:
    """缺陷类型中文映射"""
    MAPPING = {
        DefectType.HOLE: "破洞",
        DefectType.STAIN: "污渍",
        DefectType.COLOR_VARIANCE: "色差",
        DefectType.WARP_BREAK: "经断",
        DefectType.WEFT_BREAK: "纬断",
    }

    @classmethod
    def get_cn(cls, defect_type: DefectType) -> str:
        return cls.MAPPING.get(defect_type, "未知")


class DefectSeverity(str, Enum):
    """缺陷严重程度枚举"""
    MINOR = "minor"         # 轻微
    MODERATE = "moderate"   # 中等
    SEVERE = "severe"      # 严重


class ReviewResult(str, Enum):
    """复核结果枚举"""
    CONFIRMED = "confirmed"         # 已确认
    FALSE_POSITIVE = "false_positive"  # 误报
    UNCERTAIN = "uncertain"         # 不确定


class Defect(Base):
    """
    缺陷模型类
    存储检测到的缺陷信息，如类型、位置、置信度、边界框坐标等。
    """
    __tablename__ = "defects"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 外键
    roll_id: Mapped[int] = mapped_column(
        ForeignKey("rolls.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联布卷ID"
    )
    video_id: Mapped[int | None] = mapped_column(
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联视频ID"
    )

    # 缺陷信息
    defect_type: Mapped[DefectType] = mapped_column(
        SQLEnum(DefectType, native_enum=False),
        nullable=False,
        comment="缺陷类型"
    )
    defect_type_cn: Mapped[str] = mapped_column(String(50), nullable=False, comment="中文名称")

    # 检测信息
    confidence: Mapped[float] = mapped_column(Float, nullable=False, comment="置信度（0-1）")
    severity: Mapped[DefectSeverity] = mapped_column(
        SQLEnum(DefectSeverity, native_enum=False),
        nullable=False,
        comment="严重程度"
    )

    # 位置信息
    position_meter: Mapped[float | None] = mapped_column(Float, nullable=True, comment="位置（米）")
    timestamp: Mapped[float | None] = mapped_column(Float, nullable=True, comment="视频时间戳（秒）")

    # 边界框坐标
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True, comment="边界框左上角X")
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True, comment="边界框左上角Y")
    bbox_x2: Mapped[float | None] = mapped_column(Float, nullable=True, comment="边界框右下角X")
    bbox_y2: Mapped[float | None] = mapped_column(Float, nullable=True, comment="边界框右下角Y")

    # 截图
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="缺陷截图路径")

    # 时间戳
    detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="检测时间"
    )

    # 复核信息
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否人工复核")
    reviewed_result: Mapped[ReviewResult | None] = mapped_column(
        SQLEnum(ReviewResult, native_enum=False),
        nullable=True,
        comment="复核结果"
    )

    # 关系
    roll: Mapped["Roll"] = relationship("Roll", back_populates="defects")
    video: Mapped["Video | None"] = relationship("Video", back_populates="defects")

    # 索引
    __table_args__ = (
        Index("ix_defects_roll_id", "roll_id"),
        Index("ix_defects_defect_type", "defect_type"),
        Index("ix_defects_severity", "severity"),
        Index("ix_defects_detected_at", "detected_at"),
    )

    def __repr__(self) -> str:
        return f"<Defect(id={self.id}, type={self.defect_type}, confidence={self.confidence})>"
