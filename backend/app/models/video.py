from __future__ import annotations

from typing import TYPE_CHECKING

"""
FabricEye AI验布系统 - 视频模型
定义视频相关的 ORM 模型。
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Float, DateTime, BigInteger, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.roll import Roll
    from app.models.defect import Defect



class VideoStatus(str, Enum):
    """视频状态枚举"""
    RECORDING = "recording"      # 录制中
    COMPLETED = "completed"      # 完成
    FAILED = "failed"           # 失败


class Video(Base):
    """
    视频模型类
    存储录制的视频文件信息，如路径、时长、分辨率、关联布卷等。
    """
    __tablename__ = "videos"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 外键
    roll_id: Mapped[int] = mapped_column(
        ForeignKey("rolls.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="关联布卷ID"
    )

    # 文件信息
    file_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, comment="视频文件绝对路径")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小（字节）")

    # 媒体信息
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True, comment="视频时长（秒）")
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="分辨率（如：1920x1080）")
    fps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="帧率")

    # 状态
    status: Mapped[VideoStatus] = mapped_column(
        SQLEnum(VideoStatus, native_enum=False),
        default=VideoStatus.RECORDING,
        nullable=False,
        comment="状态"
    )

    # 时间戳
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")

    # 关系
    roll: Mapped["Roll"] = relationship("Roll", back_populates="videos")
    defects: Mapped[list["Defect"]] = relationship("Defect", back_populates="video", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("ix_videos_roll_id_status", "roll_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, roll_id={self.roll_id}, status={self.status})>"
