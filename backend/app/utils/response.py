from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

def success(data: Any = None, message: str = "success") -> dict:
    return ResponseModel(code=200, message=message, data=data).model_dump()

def error(message: str = "error", code: int = 400, data: Any = None) -> dict:
    return ResponseModel(code=code, message=message, data=data).model_dump()
from pydantic import BaseModel

T = TypeVar("T")

class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

def success(data: Any = None, message: str = "success") -> ResponseModel:
    return ResponseModel(code=200, message=message, data=data)

def error(message: str = "error", code: int = 400, data: Any = None) -> ResponseModel:
    return ResponseModel(code=code, message=message, data=data)
