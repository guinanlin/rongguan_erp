from datetime import datetime
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
    # 款号 : Link - Item
    style_no: Optional[str] = None
    # 客户名称 : Link - Customer
    customer_name: Optional[str] = None
    # 打样开始时间 : Datetime
    sample_start_time: Optional[datetime] = None
    # 手工专机费用 : Currency
    handwork_machine_cost: Optional[float] = None
    # 版本 : Select
    version: Optional[str] = None
    # 样衣类型 : Select
    sample_type: Optional[str] = None
    # 年份 : Select
    year: Optional[str] = None
    # 状态 : Select
    status: Optional[str] = None
    # 款式名称 : Link - Item
    style_name: Optional[str] = None
    # 版型名称 : Data
    pattern_name: Optional[str] = None
    # 打样结束时间 : Datetime
    sample_end_time: Optional[datetime] = None
    # 特殊工艺费用 : Currency
    special_process_cost: Optional[float] = None
    # 季节 : Select
    season: Optional[str] = None
    # 样衣等级 : Select
    sample_grade: Optional[str] = None
    # 类别 : Select
    category: Optional[str] = None
    # 款式图上传 : Image
    images: Optional[str] = None
    # 备注 : Long Text
    remarks: Optional[str] = None
    # 版本图上传 : Image
    files: Optional[str] = None
    # 样衣工 : JSON
    sample_workers: Optional[str] = None
    # Amended From : Link - RG Pattern
    amended_from: Optional[str] = None
