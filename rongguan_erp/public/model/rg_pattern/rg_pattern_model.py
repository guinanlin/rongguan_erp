from datetime import date
from pydantic import BaseModel
from typing import Optional

class RGPattern(BaseModel):
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
    # 纸样编号 : Data
    pattern_no: Optional[str] = None
    # 款式图片 : Attach Image
    style_image: Optional[str] = None
    # 款式名称 : Link - Item
    style_name: Optional[str] = None
    # 版本号 : Data
    version_no: Optional[str] = None
    # 尺码范围 : Data
    size_range: Optional[str] = None
    # 创建时间 : Date
    creation_date: Optional[date] = None
    # 创建人 : Data
    created_by: Optional[str] = None
    # 状态 : Select
    status: Optional[str] = None
    # Amended From : Link - RG Pattern
    amended_from: Optional[str] = None
