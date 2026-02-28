from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.roll import RollStatus

def to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

class RollBase(BaseModel):
    roll_number: str = Field(..., alias="rollNumber")
    fabric_type: Optional[str] = Field(None, alias="fabricType")
    batch_number: Optional[str] = Field(None, alias="batchNumber")
    length_meters: Optional[float] = Field(None, alias="lengthMeters")
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel
    )

class RollCreate(RollBase):
    pass

class RollUpdate(BaseModel):
    fabric_type: Optional[str] = Field(None, alias="fabricType")
    length_meters: Optional[float] = Field(None, alias="lengthMeters")
    status: Optional[RollStatus] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel
    )

class RollResponse(RollBase):
    id: int
    status: RollStatus
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel
    )
