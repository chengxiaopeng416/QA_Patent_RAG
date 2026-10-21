
from typing import Optional, Any

from pydantic import BaseModel


# 创建API接口的响应体
class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None



