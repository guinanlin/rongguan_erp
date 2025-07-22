import frappe
from frappe import _
from frappe.utils import nowdate, add_days

@frappe.whitelist()
def create_material_request(**kwargs):
    """创建采购计划（Material Request）"""
    
    # 处理JSON数据
    if frappe.request and frappe.request.json:
        data = frappe.request.json
        if 'json_data' in data:
            kwargs.update(data['json_data'])
        else:
            kwargs.update(data)
    
    # 验证必需参数
    if not kwargs.get('company'):
        kwargs['company'] = frappe.defaults.get_global_default("company")
    
    if not kwargs.get('transaction_date'):
        kwargs['transaction_date'] = nowdate()
    
    if not kwargs.get('schedule_date'):
        kwargs['schedule_date'] = add_days(nowdate(), 7)
    
    if not kwargs.get('material_request_type'):
        kwargs['material_request_type'] = "Purchase"
    
    if not kwargs.get('status'):
        kwargs['status'] = "Draft"
    
    # 验证是否有物料项
    if not kwargs.get('items') or not isinstance(kwargs['items'], list):
        frappe.throw("items参数是必需的，且必须是列表格式")
    
    # 创建新的Material Request
    material_request = frappe.new_doc("Material Request")
    
    # 设置主文档字段
    main_fields = [
        "material_request_type", "company", "transaction_date", 
        "schedule_date", "status", "title", "customer"
    ]
    
    for field in main_fields:
        if field in kwargs:
            material_request.set(field, kwargs[field])
    
    # 添加物料项
    for item_data in kwargs['items']:
        material_request.append("items", item_data)
    
    material_request.insert()
    
    return {
        "status": "success",
        "message": f"采购计划已创建: {material_request.name}",
        "material_request": material_request.name,
        "doc": material_request.as_dict()
    }

@frappe.whitelist()
def create_material_request_simple(company, item_code, qty, warehouse=None):
    """简单的bench execute方法，用于快速创建采购计划"""
    
    # 创建物料项
    items = [{
        "item_code": item_code,
        "qty": qty,
        "warehouse": warehouse or "仓库 - D"
    }]
    
    # 调用主方法
    return create_material_request(
        company=company,
        items=items
    )

@frappe.whitelist()
def create_material_request_bench(*args):
    """专门用于bench execute的创建采购计划方法"""
    
    print(f"DEBUG: 接收到的参数: {args}")
    print(f"DEBUG: 参数类型: {type(args)}")
    print(f"DEBUG: 参数长度: {len(args)}")
    
    # bench execute会把JSON字符串解析成键值对，我们需要重新组合
    if len(args) >= 2:
        # 重新构建JSON字符串
        import json
        data_dict = {}
        for i in range(0, len(args), 2):
            if i + 1 < len(args):
                key = args[i]
                value = args[i + 1]
                # 尝试解析值为JSON
                try:
                    if value.startswith('{') or value.startswith('['):
                        value = json.loads(value)
                except:
                    pass
                data_dict[key] = value
        print(f"DEBUG: 重新组合的字典: {data_dict}")
    else:
        data_dict = args[0] if args else {}
    
    if isinstance(data_dict, str):
        import json
        print(f"DEBUG: 解析JSON字符串: {data_dict}")
        data_dict = json.loads(data_dict)
        print(f"DEBUG: JSON解析结果: {data_dict}")
    
    print(f"DEBUG: 最终传递给create_material_request的参数: {data_dict}")
    
    return create_material_request(**data_dict)

@frappe.whitelist()
def create_material_request_from_dict(data_dict=None):
    """从字典数据创建采购计划"""
    
    # 处理JSON数据
    if not data_dict and frappe.request and frappe.request.json:
        data = frappe.request.json
        if 'data_dict' in data:
            data_dict = data['data_dict']
        elif 'json_data' in data:
            data_dict = data['json_data']
        else:
            data_dict = data
    
    if isinstance(data_dict, str):
        import json
        data_dict = json.loads(data_dict)
    
    if not data_dict:
        frappe.throw("data_dict参数是必需的")
    
    # 创建新的Material Request
    material_request = frappe.new_doc("Material Request")
    
    # 设置主文档字段
    main_fields = [
        "material_request_type", "company", "transaction_date", 
        "schedule_date", "status", "title", "customer"
    ]
    
    for field in main_fields:
        if field in data_dict:
            material_request.set(field, data_dict[field])
    
    # 添加物料项
    if "items" in data_dict:
        for item_data in data_dict["items"]:
            material_request.append("items", item_data)
    
    material_request.insert()
    
    return {
        "status": "success", 
        "message": f"采购计划已创建: {material_request.name}",
        "material_request": material_request.name,
        "doc": material_request.as_dict()
    }
