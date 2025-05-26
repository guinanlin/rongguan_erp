from .rg_size_details_model import RGSizeDetails
from .rgbom_item_model import RGBOMItem
from .rgbom_operation_model import RGBOMOperation
from datetime import date
from pydantic import BaseModel
from typing import List
from typing import Optional

class RGProductionOrders(BaseModel):
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
    # 生产制造工单号 : Data
    production_order_number: Optional[str] = None
    # 客户ID : Link - Customer
    customer: Optional[str] = None
    # 业务类型 : Select
    business_type: Optional[str] = None
    # 订单类型 : Select
    order_type: Optional[str] = None
    # 订单号 : Data
    order_number: Optional[str] = None
    # 离厂期 : Date
    departure_date: Optional[date] = None
    # 款号 : Link - Item
    style_number: Optional[str] = None
    # 产品名称 : Data
    product_name: Optional[str] = None
    # 订单状态 : Select
    status: Optional[str] = None
    # 订单ID : Data
    order_id: Optional[str] = None
    # 订单日期 : Date
    order_date: Optional[date] = None
    # 交货日期 : Date
    delivery_date: Optional[date] = None
    # 合同号 : Data
    contract_number: Optional[str] = None
    # 跟单员ID : Link - Employee
    merchandiser: Optional[str] = None
    # 销售员ID : Link - Employee
    salesperson: Optional[str] = None
    # 纸样号 : Data
    pattern_number: Optional[str] = None
    # 国家单 : Data
    national_order: Optional[str] = None
    # 工厂ID : Link - Supplier
    factory: Optional[str] = None
    # 图片 : Attach
    image: Optional[str] = None
    # 款式 : Link - Item
    item: Optional[str] = None
    # 公司 : Link - Company
    company: Optional[str] = None
    # CB0 : Data
    cb0: Optional[str] = None
    # 项目 : Data
    project: Optional[str] = None
    # 颜色 : Link - Item Attribute
    rg_color: Optional[str] = None
    # 单位 : Link - UOM
    uom: Optional[str] = None
    # 数量 : Data
    quantity: Optional[str] = None
    # 尺码 : Link - Item Attribute
    rg_size: Optional[str] = None
    # 是否激活 : Data
    is_active: Optional[str] = None
    # 是否默认 : Data
    is_default: Optional[str] = None
    # 允许替代物品 : Data
    allow_alternative_item: Optional[str] = None
    # 基于BOM设置子组件物品费率 : Data
    set_rate_of_sub_assembly_item_based_on_bom: Optional[str] = None
    # 货币详情 : Data
    currency_detail: Optional[str] = None
    # 物料列表 : Table - RG BOM Item
    items: List[RGBOMItem] = []
    # 尺码表 : Table - RG Size Details
    rg_size_details: List[RGSizeDetails] = []
    # 工艺路线 : Link - Routing
    工艺路线: Optional[str] = None
    #  : Table - RG BOM Operation
    operations: List[RGBOMOperation] = []
    # Amended From : Link - RG Production Orders
    amended_from: Optional[str] = None
    #  : Table - RG BOM Item
    table_mbev: List[RGBOMItem] = []
    # 前图示 : Attach Image
    front_picture: Optional[str] = None
    # 后图示 : Attach Image
    backend_picture: Optional[str] = None
    # 商标位置图 : Attach Image
    trademark_position_diagram_picture: Optional[str] = None
    # 产地标/尺码标 : Attach Image
    origin_label_size_label: Optional[str] = None
