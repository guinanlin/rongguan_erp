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
    
    print("=== 开始创建采购计划 ===")
    print(f"原始 data_dict: {data_dict}")
    
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
    
    print(f"处理后的 data_dict: {data_dict}")
    print(f"data_dict 中的 title 字段: {data_dict.get('title', '未设置')}")
    
    # 创建新的Material Request
    material_request = frappe.new_doc("Material Request")
    
    # 设置主文档字段
    main_fields = [
        "material_request_type", "company", "transaction_date", 
        "schedule_date", "status", "title", "customer","custom_sales_order_number"
    ]
    
    for field in main_fields:
        if field in data_dict:
            value = data_dict[field]
            material_request.set(field, value)
            if field == 'title':
                print(f"设置 title 字段为: {value}")
    
    print(f"设置字段后的 material_request.title: {material_request.title}")
    
    # 添加物料项
    if "items" in data_dict:
        for item_data in data_dict["items"]:
            material_request.append("items", item_data)
    
    print(f"插入前 material_request.title: {material_request.title}")
    print(f"物料项数量: {len(material_request.items)}")
    
    # 检查是否有物料项
    if not material_request.items:
        print("警告：没有物料项，无法创建采购计划")
        return {
            "status": "error",
            "message": "采购计划必须包含至少一个物料项",
            "error": "items 字段不能为空"
        }
    
    material_request.insert()
    print(f"插入后 material_request.title: {material_request.title}")
    
    # 提交采购计划
    try:
        material_request.submit()
        print(f"采购计划已提交: {material_request.name}")
        return {
            "status": "success", 
            "message": f"采购计划已创建并提交: {material_request.name}",
            "material_request": material_request.name,
            "doc": material_request.as_dict()
        }
    except Exception as e:
        print(f"提交采购计划失败: {str(e)}")
        return {
            "status": "partial_success",
            "message": f"采购计划已创建但提交失败: {material_request.name}",
            "material_request": material_request.name,
            "error": str(e),
            "doc": material_request.as_dict()
        }
