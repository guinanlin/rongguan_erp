from pydantic import BaseModel
from typing import Optional

class RGPaperMaterialUsage(BaseModel):
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
    # 类型 : Select
    type: Optional[str] = None
    # 材料名称 : Link - Item
    name: str
    # 用量 : Float
    amount: float
    # 单位 : Select
    unit: Optional[str] = None
    # 备注 : Small Text
    remarks: Optional[str] = None
