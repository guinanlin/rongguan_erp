from pydantic import BaseModel
from typing import Optional

class RGSizeDetails(BaseModel):
    name: str
    creation: str
    modified: str
    owner: str
    modified_by: str
    docstatus: int
    parent: Optional[str] = None
    parentfield: Optional[str] = None
    parenttype: Optional[str] = None
    idx: Optional[int] = None
    # 尺码 : Data
    尺码: Optional[str] = None
    # 数量 : Int
    数量: Optional[int] = None
