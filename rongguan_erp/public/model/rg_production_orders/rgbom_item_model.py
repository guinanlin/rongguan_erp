from pydantic import BaseModel
from typing import Optional

class RGBOMItem(BaseModel):
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
    # 物料代码 : Link - Item
    item_code: str
    # 物料名称 : Data
    item_name: Optional[str] = None
    # 物料操作 : Link - Operation
    operation: Optional[str] = None
    # 不展开 : Check
    do_not_explode: Optional[bool] = None
    # 物料清单编号 : Link - BOM
    bom_no: Optional[str] = None
    # 来源仓库 : Link - Warehouse
    source_warehouse: Optional[str] = None
    # 允许替代物料 : Check
    allow_alternative_item: Optional[bool] = None
    # 是否库存物料 : Check
    is_stock_item: Optional[bool] = None
    # 物料描述 : Text Editor
    description: Optional[str] = None
    # Image : Attach
    image: Optional[str] = None
    # Image View : Image
    image_view: Optional[str] = None
    # 数量 : Float
    qty: float
    # 单位 : Link - UOM
    uom: str
    # 库存数量 : Float
    stock_qty: Optional[float] = None
    # 库存单位 : Link - UOM
    stock_uom: Optional[str] = None
    # 转换系数 : Float
    conversion_factor: Optional[float] = None
    # 价格 : Currency
    rate: Optional[float] = None
    # 基本价格 (公司货币) : Currency
    base_rate: Optional[float] = None
    # 金额 : Currency
    amount: Optional[float] = None
    # 金额 (公司货币) : Currency
    base_amount: Optional[float] = None
    # Qty Consumed Per Unit : Float
    qty_consumed_per_unit: Optional[float] = None
    # Has Variants : Check
    has_variants: Optional[bool] = None
    # Include Item In Manufacturing : Check
    include_item_in_manufacturing: Optional[bool] = None
    # Original Item : Link - Item
    original_item: Optional[str] = None
    # 由供应商采购 : Check
    sourced_by_supplier: Optional[bool] = None
