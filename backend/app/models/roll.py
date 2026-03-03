from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Float, DateTime, Enum as SQLEnum, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video import Video
    from app.models.defect import Defect

class RollStatus(str, Enum):
    """布卷状态枚举"""
    PENDING = "pending"           # 待处理
    INSPECTING = "inspecting"     # 验布中
    RECORDING = "recording"      # 录制中
    ANALYZING = "analyzing"      # 分析中
    COMPLETED = "completed"      # 完成
    ERROR = "error"              # 错误

class Roll(Base):
    """
    布卷模型类
    存储布卷的基本信息，如编号、面料类型、批次、长度、状态等。
    """
    __tablename__ = "rolls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    roll_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False, comment="布卷编号")
    fabric_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="面料类型")
    batch_number: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="批次号")
    length_meters: Mapped[float | None] = mapped_column(Float, nullable=True, comment="布卷长度（米）")

    status: Mapped[RollStatus] = mapped_column(
        SQLEnum(RollStatus, native_enum=False),
        default=RollStatus.PENDING,
        nullable=False,
        comment="状态"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间"
    )

    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="扩展字段")

    # ERP 关联字段
    erp_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="ERP 系统关联 ID")
    erp_sync_status: Mapped[str | None] = mapped_column(String(20), default="pending", nullable=True, comment="ERP 同步状态")
    
    videos: Mapped[list["Video"]] = relationship("Video", back_populates="roll", cascade="all, delete-orphan")
    defects: Mapped[list["Defect"]] = relationship("Defect", back_populates="roll", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_rolls_status", "status"),
        Index("ix_rolls_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Roll(id={self.id}, roll_number={self.roll_number}, status={self.status})>"
