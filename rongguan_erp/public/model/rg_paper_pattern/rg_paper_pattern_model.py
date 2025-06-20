from .rg_paper_material_usage_model import RGPaperMaterialUsage
from pydantic import BaseModel
from typing import List
from typing import Optional

class RGPaperPattern(BaseModel):
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
    # 款式 : Data
    style_no: str
    # 款号 : Link - Item
    style_name: str
    # 款式编号 : Data
    style_code: str
    # 客户 : Link - Customer
    customer: str
    # 面里料用量 : Table - RG Paper Material Usage
    material_usages: List[RGPaperMaterialUsage] = []
    # 面料图片 : Attach
    fabric_images: Optional[str] = None
    # 里料图片 : Attach
    lining_images: Optional[str] = None
    # 面料信息及缩率 : Text
    fabric_info: Optional[str] = None
    # 里料信息及缩率 : Text
    lining_info: Optional[str] = None
    # 生产注意事项 : Text
    process_instructions: Optional[str] = None
    # 备注 : Text
    remarks: Optional[str] = None
    # Amended From : Link - RG Paper Pattern
    amended_from: Optional[str] = None
