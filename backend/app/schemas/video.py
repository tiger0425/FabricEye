from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.video import VideoStatus

def to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

class VideoBase(BaseModel):
    roll_id: int = Field(..., alias="rollId")
    file_path: str = Field(..., alias="filePath")
    file_size: Optional[int] = Field(None, alias="fileSize")
    duration_seconds: Optional[float] = Field(None, alias="durationSeconds")
    resolution: Optional[str] = None
    fps: Optional[float] = None
    status: VideoStatus

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel
    )

class VideoResponse(VideoBase):
    id: int
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel
    )
