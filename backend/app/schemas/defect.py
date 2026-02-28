from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.defect import DefectType, DefectSeverity, ReviewResult

def to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

class DefectBase(BaseModel):
    roll_id: int = Field(..., alias="rollId")
    video_id: Optional[int] = Field(None, alias="videoId")
    defect_type: DefectType = Field(..., alias="defectType")
    defect_type_cn: str = Field(..., alias="defectTypeCn")
    confidence: float
    severity: DefectSeverity
    position_meter: Optional[float] = Field(None, alias="positionMeter")
    timestamp: Optional[float] = None
    bbox_x1: Optional[float] = Field(None, alias="bboxX1")
    bbox_y1: Optional[float] = Field(None, alias="bboxY1")
    bbox_x2: Optional[float] = Field(None, alias="bboxX2")
    bbox_y2: Optional[float] = Field(None, alias="bboxY2")
    snapshot_path: Optional[str] = Field(None, alias="snapshotPath")

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel
    )

class DefectResponse(DefectBase):
    id: int
    detected_at: datetime = Field(..., alias="detectedAt")
    reviewed: bool
    reviewed_result: Optional[ReviewResult] = Field(None, alias="reviewedResult")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel
    )
