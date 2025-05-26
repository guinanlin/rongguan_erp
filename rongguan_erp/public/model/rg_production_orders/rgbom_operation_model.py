from pydantic import BaseModel
from typing import Optional

class RGBOMOperation(BaseModel):
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
    # 序列ID : Int
    sequence_id: Optional[int] = None
    # 操作 : Link - Operation
    operation: str
    # 工厂 : Link - RG Factory
    工厂: Optional[str] = None
    # 工作站类型 : Link - Workstation Type
    workstation_type: Optional[str] = None
    # 工作站 : Link - Workstation
    workstation: Optional[str] = None
    # 操作时间 : Float - In minutes
    time_in_mins: float
    # 固定时间 : Check - Operation time does not depend on quantity to produce
    fixed_time: Optional[bool] = None
    # 小时费率 : Currency
    hour_rate: Optional[float] = None
    # 基本小时费率(公司货币) : Currency
    base_hour_rate: Optional[float] = None
    # 操作成本 : Currency
    operating_cost: Optional[float] = None
    # 基本操作成本(公司货币) : Currency
    base_operating_cost: Optional[float] = None
    # 批量大小 : Int
    batch_size: Optional[int] = None
    # 基于BOM数量设置操作成本 : Check
    set_cost_based_on_bom_qty: Optional[bool] = None
    # 单位成本 : Float
    cost_per_unit: Optional[float] = None
    # 基本单位成本 : Float
    base_cost_per_unit: Optional[float] = None
    # 描述 : Text Editor
    description: Optional[str] = None
    # 图像 : Attach
    image: Optional[str] = None
