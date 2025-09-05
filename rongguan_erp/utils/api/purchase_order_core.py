import frappe
import json
from frappe import _
from frappe.utils import nowdate, add_days, getdate
from frappe.model.mapper import get_mapped_doc

def get_service_item_by_name(item_name="委外加工"):
    """
    根据服务项目名称获取项目代码
    
    参数:
    - item_name: 项目名称，默认为"委外加工"
    
    返回:
    - 项目代码，如果找不到则返回None
    """
    try:
        # 根据item_name查找item_code
        item_code = frappe.get_value("Item", {"item_name": item_name, "disabled": 0}, "item_code")
        if item_code:
            return item_code
        
        # 如果找不到，尝试模糊匹配
        items = frappe.get_all("Item", 
            filters={
                "item_name": ["like", f"%{item_name}%"],
                "disabled": 0,
                "is_stock_item": 0  # 服务项目通常是非库存项目
            },
            fields=["item_code", "item_name"],
            limit=1
        )
        
        if items:
            return items[0].item_code
        
        return None
        
    except Exception as e:
        frappe.log_error(f"获取服务项目代码失败: {str(e)}", "服务项目查询错误")
        return None

def create_subcontracting_order_from_po(purchase_order_name, supplier_warehouse=None):
    """
    从采购订单创建委外工单
    
    参数:
    - purchase_order_name: 采购订单名称
    - supplier_warehouse: 委外仓库（可选，默认为"委外仓库 - D"）
    
    返回:
    - 委外工单名称，如果创建失败则返回None
    """
    try:
        print(f"DEBUG: 开始从采购订单创建委外工单: {purchase_order_name}")
        
        # 检查采购订单是否存在且已提交
        po = frappe.get_doc("Purchase Order", purchase_order_name)
        print(f"DEBUG: 采购订单状态: {po.docstatus}")
        
        if po.docstatus != 1:
            print(f"DEBUG: 采购订单未提交，无法创建委外工单")
            frappe.throw(f"采购订单 {purchase_order_name} 尚未提交，无法创建委外工单")
        
        # 检查是否已经存在委外工单
        existing_sco = frappe.get_value("Subcontracting Order", {"purchase_order": purchase_order_name})
        print(f"DEBUG: 检查是否已存在委外工单: {existing_sco}")
        
        if existing_sco:
            print(f"DEBUG: 委外工单已存在，返回: {existing_sco}")
            return existing_sco
        
        # 导入创建委外工单的函数
        from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order
        
        print(f"DEBUG: 调用make_subcontracting_order函数")
        
        # 检查采购订单是否已经完全委外加工
        from erpnext.buying.doctype.purchase_order.purchase_order import is_po_fully_subcontracted
        is_fully_subcontracted = is_po_fully_subcontracted(purchase_order_name)
        print(f"DEBUG: 采购订单是否完全委外加工: {is_fully_subcontracted}")
        
        # 检查采购订单项目详情
        po_items = frappe.get_all("Purchase Order Item", 
            filters={"parent": purchase_order_name},
            fields=["name", "item_code", "qty", "subcontracted_quantity", "fg_item", "fg_item_qty"]
        )
        print(f"DEBUG: 采购订单项目详情: {json.dumps(po_items, indent=2, ensure_ascii=False)}")
        
        # 检查每个项目是否满足委外加工条件
        for item in po_items:
            print(f"DEBUG: 项目 {item['item_code']}: qty={item['qty']}, subcontracted_quantity={item['subcontracted_quantity']}, fg_item={item['fg_item']}")
            if item['qty'] == item['subcontracted_quantity']:
                print(f"DEBUG: 项目 {item['item_code']} 已经完全委外加工")
            elif not item['fg_item']:
                print(f"DEBUG: 项目 {item['item_code']} 没有成品项目，无法委外加工")
        
        # 创建委外工单
        try:
            # 先获取委外工单文档，然后设置supplier_warehouse
            subcontracting_order = make_subcontracting_order(
                source_name=purchase_order_name,
                save=False,  # 先不保存
                submit=False,
                notify=False
            )
            
            if subcontracting_order:
                # 设置supplier_warehouse
                if not subcontracting_order.supplier_warehouse:
                    # 优先使用传入的supplier_warehouse参数
                    if supplier_warehouse:
                        subcontracting_order.supplier_warehouse = supplier_warehouse
                    else:
                        # 尝试从采购订单获取supplier_warehouse
                        po_supplier_warehouse = frappe.get_value("Purchase Order", purchase_order_name, "supplier_warehouse")
                        if po_supplier_warehouse:
                            subcontracting_order.supplier_warehouse = po_supplier_warehouse
                        else:
                            # 如果没有，使用默认的委外仓库
                            subcontracting_order.supplier_warehouse = "委外仓库 - D"
                
                print(f"DEBUG: 设置supplier_warehouse: {subcontracting_order.supplier_warehouse}")
                
                # 现在保存
                subcontracting_order.save()
            
            print(f"DEBUG: make_subcontracting_order返回结果: {subcontracting_order}")
            
        except Exception as e:
            print(f"DEBUG: make_subcontracting_order抛出异常: {str(e)}")
            subcontracting_order = None
        
        if subcontracting_order:
            print(f"DEBUG: 委外工单创建成功: {subcontracting_order.name}")
            return subcontracting_order.name
        
        print(f"DEBUG: 委外工单创建失败，返回None")
        return None
        
    except Exception as e:
        frappe.log_error(f"从采购订单创建委外工单失败: {str(e)}", "委外工单创建错误")
        return None

@frappe.whitelist()
def create_subcontracting_service_purchase_order(**kwargs):
    """
    创建委外加工服务费的采购订单
    
    参数说明:
    - supplier: 供应商代码
    - supplier_name: 供应商名称（可选，会自动获取）
    - company: 公司代码（可选，会使用默认公司）
    - transaction_date: 交易日期（可选，默认为今天）
    - schedule_date: 计划日期（可选，默认为7天后）
    - qty: 数量
    - rate: 单价
    - description: 描述（可选）
    - warehouse: 仓库（可选，默认为"仓库 - D"）
    - cost_center: 成本中心（可选）
    - project: 项目（可选）
    - fg_item: 成品项目代码（必需，用于新委外加工流程）
    - fg_item_qty: 成品项目数量（可选，默认为1）
    - service_item_name: 服务项目名称（可选，默认为"委外加工"）
    - supplier_warehouse: 委外仓库（可选，默认为"委外仓库 - D"）
    - auto_create_sco: 是否自动创建委外工单（可选，默认为True）
    - submit_doc: 是否提交文档（可选，默认为True，True=提交，False=仅保存为草稿）
    """
    
    # 处理JSON数据
    if frappe.request and frappe.request.json:
        data = frappe.request.json
        if 'json_data' in data:
            kwargs.update(data['json_data'])
        else:
            kwargs.update(data)
    
    # 验证必需参数
    if not kwargs.get('supplier'):
        frappe.throw("供应商（supplier）是必需参数")
    
    if not kwargs.get('qty'):
        frappe.throw("数量（qty）是必需参数")
    
    if not kwargs.get('rate'):
        frappe.throw("单价（rate）是必需参数")
    
    # 新委外加工流程需要fg_item
    if not kwargs.get('fg_item'):
        frappe.throw("成品项目（fg_item）是必需参数，用于新委外加工流程")
    
    # 设置默认值
    if not kwargs.get('company'):
        kwargs['company'] = frappe.defaults.get_global_default("company")
    
    if not kwargs.get('transaction_date'):
        kwargs['transaction_date'] = nowdate()
    
    if not kwargs.get('schedule_date'):
        kwargs['schedule_date'] = add_days(nowdate(), 7)
    
    if not kwargs.get('warehouse'):
        kwargs['warehouse'] = "仓库 - D"
    
    # 获取供应商名称
    if not kwargs.get('supplier_name'):
        supplier_name = frappe.get_value("Supplier", kwargs['supplier'], "supplier_name")
        if supplier_name:
            kwargs['supplier_name'] = supplier_name
    
    # 获取服务项目代码
    service_item_name = kwargs.get('service_item_name', '委外加工')
    service_item_code = get_service_item_by_name(service_item_name)
    
    if not service_item_code:
        frappe.throw(f"找不到名称为 '{service_item_name}' 的服务项目，请检查项目名称或手动指定item_code")
    
    # 委外加工服务费的标准物料信息
    service_item = {
        "item_code": service_item_code,  # 动态获取的item_code
        "item_group": "服务",
        "item_name": service_item_name,  # 使用传入的item_name
        "qty": kwargs['qty'],
        "rate": kwargs['rate'],
        "warehouse": kwargs['warehouse'],
        "schedule_date": kwargs['schedule_date'],
        "description": kwargs.get('description', f'{service_item_name}服务费'),
        "expense_account": kwargs.get('expense_account', '5403 - 机械作业 - D'),
        "cost_center": kwargs.get('cost_center', '主 - D'),
        # 添加成品项目信息
        "fg_item": kwargs['fg_item'],
        "fg_item_qty": kwargs.get('fg_item_qty', 1)
    }
    
    # 创建采购订单数据
    purchase_order_data = {
        "doctype": "Purchase Order",
        "supplier": kwargs['supplier'],
        "supplier_name": kwargs.get('supplier_name', ''),
        "company": kwargs['company'],
        "transaction_date": kwargs['transaction_date'],
        "schedule_date": kwargs['schedule_date'],
        "currency": frappe.get_cached_value("Company", kwargs['company'], "default_currency"),
        "conversion_rate": 1,
        "is_subcontracted": 1,  # 标记为委外加工
        "is_old_subcontracting_flow": 0,  # 明确设置为新流程
        "custom_purchase_type": "委外加工",  # 使用自定义字段标记采购类型
        "status": "Draft",
        "items": [service_item]
    }
    
    # 添加可选字段
    if kwargs.get('project'):
        purchase_order_data['project'] = kwargs['project']
    
    if kwargs.get('cost_center'):
        purchase_order_data['cost_center'] = kwargs['cost_center']
    
    try:
        # 创建采购订单文档
        purchase_order = frappe.get_doc(purchase_order_data)
        
        # 设置缺失值
        purchase_order.set_missing_values()
        
        # 保存采购订单
        purchase_order.insert()
        
        # 计算税费和总计
        purchase_order.calculate_taxes_and_totals()
        purchase_order.save()
        
        # 根据参数决定是否提交采购订单
        submit_doc = kwargs.get('submit_doc', True)
        if submit_doc:
            purchase_order.submit()
            doc_status = "已提交"
        else:
            doc_status = "草稿"
        
        # 创建委外工单（只有已提交的采购订单才能创建委外工单）
        subcontracting_order_name = None
        auto_create_sco = kwargs.get('auto_create_sco', True)
        
        print(f"DEBUG: auto_create_sco = {auto_create_sco}")
        print(f"DEBUG: submit_doc = {submit_doc}")
        
        if auto_create_sco and submit_doc:
            print(f"DEBUG: 开始创建委外工单，采购订单: {purchase_order.name}")
            # 获取supplier_warehouse参数
            supplier_warehouse = kwargs.get('supplier_warehouse')
            subcontracting_order_name = create_subcontracting_order_from_po(purchase_order.name, supplier_warehouse)
            print(f"DEBUG: 委外工单创建结果: {subcontracting_order_name}")
        elif auto_create_sco and not submit_doc:
            print("DEBUG: 采购订单为草稿状态，跳过委外工单创建")
        else:
            print("DEBUG: 跳过委外工单创建")
        
        result = {
            "status": "success",
            "message": f"委外加工服务费采购订单已创建并{doc_status}: {purchase_order.name}",
            "purchase_order": purchase_order.name,
            "doc": purchase_order.as_dict(),
            "total_amount": purchase_order.grand_total,
            "base_total_amount": purchase_order.base_grand_total,
            "doc_status": doc_status
        }
        
        if subcontracting_order_name:
            result["subcontracting_order"] = subcontracting_order_name
            result["message"] += f"，委外工单已创建: {subcontracting_order_name}"
        elif auto_create_sco and not submit_doc:
            result["message"] += "（草稿状态，委外工单将在提交后创建）"
        
        return result
        
    except Exception as e:
        frappe.log_error(f"创建委外加工服务费采购订单失败: {str(e)}", "委外加工采购订单创建错误")
        return {
            "status": "error",
            "message": f"创建委外加工服务费采购订单失败: {str(e)}",
            "error": str(e)
        }

@frappe.whitelist()
def create_subcontracting_service_po_simple(supplier, qty, rate, **kwargs):
    """
    简单的委外加工服务费采购订单创建方法
    
    参数:
    - supplier: 供应商代码
    - qty: 数量
    - rate: 单价
    - **kwargs: 其他可选参数
    """
    
    kwargs.update({
        'supplier': supplier,
        'qty': qty,
        'rate': rate
    })
    
    return create_subcontracting_service_purchase_order(**kwargs)

@frappe.whitelist()
def create_subcontracting_service_po_from_dict(data_dict=None):
    """
    从字典数据创建委外加工服务费采购订单
    
    参数:
    - data_dict: 包含采购订单数据的字典
    """
    
    print("=== 开始创建委外加工服务费采购订单 ===")
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
    
    # 验证必需字段
    required_fields = ['supplier', 'qty', 'rate']
    for field in required_fields:
        if not data_dict.get(field):
            frappe.throw(f"字段 {field} 是必需的")
    
    # 新委外加工流程需要fg_item
    if not data_dict.get('fg_item'):
        frappe.throw("成品项目（fg_item）是必需参数，用于新委外加工流程")
    
    # 设置默认值
    if not data_dict.get('company'):
        data_dict['company'] = frappe.defaults.get_global_default("company")
    
    if not data_dict.get('transaction_date'):
        data_dict['transaction_date'] = nowdate()
    
    if not data_dict.get('schedule_date'):
        data_dict['schedule_date'] = add_days(nowdate(), 7)
    
    if not data_dict.get('warehouse'):
        data_dict['warehouse'] = "仓库 - D"
    
    # 获取供应商名称
    if not data_dict.get('supplier_name'):
        supplier_name = frappe.get_value("Supplier", data_dict['supplier'], "supplier_name")
        if supplier_name:
            data_dict['supplier_name'] = supplier_name
    
    # 获取服务项目代码
    service_item_name = data_dict.get('service_item_name', '委外加工')
    service_item_code = get_service_item_by_name(service_item_name)
    
    if not service_item_code:
        frappe.throw(f"找不到名称为 '{service_item_name}' 的服务项目，请检查项目名称或手动指定item_code")
    
    # 构建委外加工服务费项目
    service_item = {
        "item_code": service_item_code,  # 动态获取的item_code
        "item_group": "服务",
        "item_name": service_item_name,  # 使用传入的item_name
        "qty": data_dict['qty'],
        "rate": data_dict['rate'],
        "warehouse": data_dict['warehouse'],
        "schedule_date": data_dict['schedule_date'],
        "description": data_dict.get('description', f'{service_item_name}服务费'),
        "expense_account": data_dict.get('expense_account', '5403 - 机械作业 - D'),
        "cost_center": data_dict.get('cost_center', '主 - D'),
        # 添加成品项目信息
        "fg_item": data_dict['fg_item'],
        "fg_item_qty": data_dict.get('fg_item_qty', 1)
    }
    
    # 创建采购订单数据
    purchase_order_data = {
        "doctype": "Purchase Order",
        "supplier": data_dict['supplier'],
        "supplier_name": data_dict.get('supplier_name', ''),
        "company": data_dict['company'],
        "transaction_date": data_dict['transaction_date'],
        "schedule_date": data_dict['schedule_date'],
        "currency": frappe.get_cached_value("Company", data_dict['company'], "default_currency"),
        "conversion_rate": 1,
        "is_subcontracted": 1,
        "is_old_subcontracting_flow": 0,  # 明确设置为新流程
        "custom_purchase_type": "委外加工",
        "status": "Draft",
        "items": [service_item]
    }
    
    # 添加可选字段
    optional_fields = ['project', 'cost_center', 'description']
    for field in optional_fields:
        if data_dict.get(field):
            if field == 'description':
                service_item['description'] = data_dict[field]
            else:
                purchase_order_data[field] = data_dict[field]
    
    try:
        # 创建采购订单文档
        purchase_order = frappe.get_doc(purchase_order_data)
        
        # 设置缺失值
        purchase_order.set_missing_values()
        
        # 保存采购订单
        purchase_order.insert()
        
        # 计算税费和总计
        purchase_order.calculate_taxes_and_totals()
        purchase_order.save()
        
        print(f"委外加工服务费采购订单已创建: {purchase_order.name}")
        
        # 根据参数决定是否提交采购订单
        submit_doc = data_dict.get('submit_doc', True)
        if submit_doc:
            try:
                purchase_order.submit()
                print(f"委外加工服务费采购订单已提交: {purchase_order.name}")
                doc_status = "已提交"
            except Exception as submit_error:
                print(f"提交采购订单失败: {str(submit_error)}")
                return {
                    "status": "partial_success",
                    "message": f"委外加工服务费采购订单已创建但提交失败: {purchase_order.name}",
                    "purchase_order": purchase_order.name,
                    "error": str(submit_error),
                    "doc": purchase_order.as_dict(),
                    "total_amount": purchase_order.grand_total,
                    "base_total_amount": purchase_order.base_grand_total
                }
        else:
            doc_status = "草稿"
            print(f"委外加工服务费采购订单保持草稿状态: {purchase_order.name}")
        
        # 创建委外工单（只有已提交的采购订单才能创建委外工单）
        subcontracting_order_name = None
        auto_create_sco = data_dict.get('auto_create_sco', True)
        
        if auto_create_sco and submit_doc:
            # 获取supplier_warehouse参数
            supplier_warehouse = data_dict.get('supplier_warehouse')
            subcontracting_order_name = create_subcontracting_order_from_po(purchase_order.name, supplier_warehouse)
        elif auto_create_sco and not submit_doc:
            print("采购订单为草稿状态，跳过委外工单创建")
        
        result = {
            "status": "success",
            "message": f"委外加工服务费采购订单已创建并{doc_status}: {purchase_order.name}",
            "purchase_order": purchase_order.name,
            "doc": purchase_order.as_dict(),
            "total_amount": purchase_order.grand_total,
            "base_total_amount": purchase_order.base_grand_total,
            "doc_status": doc_status
        }
        
        if subcontracting_order_name:
            result["subcontracting_order"] = subcontracting_order_name
            result["message"] += f"，委外工单已创建: {subcontracting_order_name}"
        elif auto_create_sco and not submit_doc:
            result["message"] += "（草稿状态，委外工单将在提交后创建）"
        
        return result
        
    except Exception as e:
        print(f"创建委外加工服务费采购订单失败: {str(e)}")
        frappe.log_error(f"创建委外加工服务费采购订单失败: {str(e)}", "委外加工采购订单创建错误")
        return {
            "status": "error",
            "message": f"创建委外加工服务费采购订单失败: {str(e)}",
            "error": str(e)
        }

@frappe.whitelist()
def get_subcontracting_service_info(service_item_name="委外加工"):
    """
    获取委外加工服务费的标准信息
    
    参数:
    - service_item_name: 服务项目名称，默认为"委外加工"
    
    返回:
    - 服务项目的详细信息
    """
    try:
        # 获取服务项目代码
        service_item_code = get_service_item_by_name(service_item_name)
        
        if not service_item_code:
            return {
                "status": "error",
                "message": f"找不到名称为 '{service_item_name}' 的服务项目"
            }
        
        # 获取项目详细信息
        item_doc = frappe.get_doc("Item", service_item_code)
        
        return {
            "status": "success",
            "item_code": service_item_code,
            "item_name": service_item_name,
            "item_group": item_doc.item_group,
            "description": item_doc.description or f"{service_item_name}服务费",
            "default_expense_account": "5403 - 机械作业 - D",
            "default_cost_center": "主 - D",
            "default_warehouse": "仓库 - D",
            "stock_uom": item_doc.stock_uom,
            "is_stock_item": item_doc.is_stock_item,
            "disabled": item_doc.disabled
        }
        
    except Exception as e:
        frappe.log_error(f"获取委外加工服务信息失败: {str(e)}", "委外加工服务信息查询错误")
        return {
            "status": "error",
            "message": f"获取委外加工服务信息失败: {str(e)}"
        }

@frappe.whitelist()
def validate_subcontracting_supplier(supplier):
    """
    验证供应商是否适合委外加工
    
    参数:
    - supplier: 供应商代码
    
    返回:
    - 验证结果和供应商信息
    """
    
    if not supplier:
        return {
            "valid": False,
            "message": "供应商代码不能为空"
        }
    
    try:
        supplier_doc = frappe.get_doc("Supplier", supplier)
        
        # 检查供应商是否存在
        if not supplier_doc:
            return {
                "valid": False,
                "message": f"供应商 {supplier} 不存在"
            }
        
        # 检查供应商是否启用
        if supplier_doc.disabled:
            return {
                "valid": False,
                "message": f"供应商 {supplier} 已被禁用"
            }
        
        return {
            "valid": True,
            "supplier_name": supplier_doc.supplier_name,
            "supplier_type": supplier_doc.supplier_type,
            "country": supplier_doc.country,
            "supplier_group": supplier_doc.supplier_group
        }
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"验证供应商时发生错误: {str(e)}"
        }

@frappe.whitelist()
def create_subcontracting_order_from_purchase_order(purchase_order_name, submit=False, supplier_warehouse=None):
    """
    从采购订单创建委外工单
    
    参数:
    - purchase_order_name: 采购订单名称
    - submit: 是否自动提交委外工单（可选，默认为False）
    - supplier_warehouse: 委外仓库（可选，默认为"委外仓库 - D"）
    
    返回:
    - 创建结果
    """
    try:
        # 检查采购订单是否存在
        if not frappe.db.exists("Purchase Order", purchase_order_name):
            return {
                "status": "error",
                "message": f"采购订单 {purchase_order_name} 不存在"
            }
        
        # 检查采购订单是否已提交
        po_docstatus = frappe.get_value("Purchase Order", purchase_order_name, "docstatus")
        if po_docstatus != 1:
            return {
                "status": "error",
                "message": f"采购订单 {purchase_order_name} 尚未提交，无法创建委外工单"
            }
        
        # 检查是否已经存在委外工单
        existing_sco = frappe.get_value("Subcontracting Order", {"purchase_order": purchase_order_name})
        if existing_sco:
            return {
                "status": "warning",
                "message": f"采购订单 {purchase_order_name} 已经存在委外工单: {existing_sco}",
                "subcontracting_order": existing_sco
            }
        
        # 导入创建委外工单的函数
        from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order
        
        # 创建委外工单
        subcontracting_order = make_subcontracting_order(
            source_name=purchase_order_name,
            save=False,  # 先不保存
            submit=False,
            notify=False
        )
        
        if subcontracting_order:
            # 设置supplier_warehouse
            if not subcontracting_order.supplier_warehouse:
                # 优先使用传入的supplier_warehouse参数
                if supplier_warehouse:
                    subcontracting_order.supplier_warehouse = supplier_warehouse
                else:
                    # 尝试从采购订单获取supplier_warehouse
                    po_supplier_warehouse = frappe.get_value("Purchase Order", purchase_order_name, "supplier_warehouse")
                    if po_supplier_warehouse:
                        subcontracting_order.supplier_warehouse = po_supplier_warehouse
                    else:
                        # 如果没有，使用默认的委外仓库
                        subcontracting_order.supplier_warehouse = "委外仓库 - D"
            
            # 现在保存
            subcontracting_order.save()
            
            # 如果需要提交
            if submit:
                subcontracting_order.submit()
        
        if subcontracting_order:
            result = {
                "status": "success",
                "message": f"委外工单已创建: {subcontracting_order.name}",
                "subcontracting_order": subcontracting_order.name,
                "doc": subcontracting_order.as_dict()
            }
            
            if submit:
                result["message"] += "（已提交）"
            
            return result
        else:
            return {
                "status": "error",
                "message": "创建委外工单失败"
            }
        
    except Exception as e:
        frappe.log_error(f"从采购订单创建委外工单失败: {str(e)}", "委外工单创建错误")
        return {
            "status": "error",
            "message": f"从采购订单创建委外工单失败: {str(e)}",
            "error": str(e)
        }

@frappe.whitelist()
def get_subcontracting_orders_by_po(purchase_order_name):
    """
    获取采购订单关联的委外工单列表
    
    参数:
    - purchase_order_name: 采购订单名称
    
    返回:
    - 委外工单列表
    """
    try:
        subcontracting_orders = frappe.get_all(
            "Subcontracting Order",
            filters={"purchase_order": purchase_order_name},
            fields=["name", "status", "docstatus", "creation", "modified"],
            order_by="creation desc"
        )
        
        return {
            "status": "success",
            "purchase_order": purchase_order_name,
            "subcontracting_orders": subcontracting_orders,
            "count": len(subcontracting_orders)
        }
        
    except Exception as e:
        frappe.log_error(f"获取采购订单委外工单列表失败: {str(e)}", "委外工单查询错误")
        return {
            "status": "error",
            "message": f"获取采购订单委外工单列表失败: {str(e)}",
            "error": str(e)
        }

def _create_single_subcontracting_service_po_internal(kwargs):
    """
    内部函数：创建单个委外加工服务费采购订单（核心逻辑剥离）
    不处理JSON数据和HTTP请求，纯内部逻辑
    
    返回: 创建的采购订单文档对象
    抛出: 任何创建过程中的异常
    """
    # 验证必需参数
    if not kwargs.get('supplier'):
        raise ValueError("供应商（supplier）是必需参数")
    
    if not kwargs.get('qty'):
        raise ValueError("数量（qty）是必需参数")
    
    if not kwargs.get('rate'):
        raise ValueError("单价（rate）是必需参数")
    
    # 新委外加工流程需要fg_item
    if not kwargs.get('fg_item'):
        raise ValueError("成品项目（fg_item）是必需参数，用于新委外加工流程")
    
    # 设置默认值
    if not kwargs.get('company'):
        kwargs['company'] = frappe.defaults.get_global_default("company")
    
    if not kwargs.get('transaction_date'):
        kwargs['transaction_date'] = nowdate()
    
    if not kwargs.get('schedule_date'):
        kwargs['schedule_date'] = add_days(nowdate(), 7)
    
    if not kwargs.get('warehouse'):
        kwargs['warehouse'] = "仓库 - D"
    
    # 获取供应商名称
    if not kwargs.get('supplier_name'):
        supplier_name = frappe.get_value("Supplier", kwargs['supplier'], "supplier_name")
        if supplier_name:
            kwargs['supplier_name'] = supplier_name
    
    # 获取服务项目代码
    service_item_name = kwargs.get('service_item_name', '委外加工')
    service_item_code = get_service_item_by_name(service_item_name)
    
    if not service_item_code:
        raise ValueError(f"找不到名称为 '{service_item_name}' 的服务项目，请检查项目名称或手动指定item_code")
    
    # 委外加工服务费的标准物料信息
    service_item = {
        "item_code": service_item_code,
        "item_group": "服务",
        "item_name": service_item_name,
        "qty": kwargs['qty'],
        "rate": kwargs['rate'],
        "warehouse": kwargs['warehouse'],
        "schedule_date": kwargs['schedule_date'],
        "description": kwargs.get('description', f'{service_item_name}服务费'),
        "expense_account": kwargs.get('expense_account', '5403 - 机械作业 - D'),
        "cost_center": kwargs.get('cost_center', '主 - D'),
        "fg_item": kwargs['fg_item'],
        "fg_item_qty": kwargs.get('fg_item_qty', 1)
    }
    
    # 创建采购订单数据
    purchase_order_data = {
        "doctype": "Purchase Order",
        "supplier": kwargs['supplier'],
        "supplier_name": kwargs.get('supplier_name', ''),
        "company": kwargs['company'],
        "transaction_date": kwargs['transaction_date'],
        "schedule_date": kwargs['schedule_date'],
        "currency": frappe.get_cached_value("Company", kwargs['company'], "default_currency"),
        "conversion_rate": 1,
        "is_subcontracted": 1,
        "is_old_subcontracting_flow": 0,
        "custom_purchase_type": "委外加工",
        "status": "Draft",
        "items": [service_item]
    }
    
    # 添加可选字段
    if kwargs.get('project'):
        purchase_order_data['project'] = kwargs['project']
    
    if kwargs.get('cost_center'):
        purchase_order_data['cost_center'] = kwargs['cost_center']
    
    # 创建采购订单文档
    purchase_order = frappe.get_doc(purchase_order_data)
    
    # 设置缺失值
    purchase_order.set_missing_values()
    
    # 保存采购订单
    purchase_order.insert()
    
    # 计算税费和总计
    purchase_order.calculate_taxes_and_totals()
    purchase_order.save()
    
    # 根据参数决定是否提交采购订单
    submit_doc = kwargs.get('submit_doc', True)
    if submit_doc:
        purchase_order.submit()
    
    return purchase_order


@frappe.whitelist()
def batch_create_subcontracting_service_purchase_orders(requests=None):
    """
    批量创建委外加工服务费采购订单（事务性处理）
    要么全部成功，要么全部失败（回滚）

    参数:
    - requests: 列表，每个元素为单个采购订单参数字典

    返回:
    - 批量创建结果（全成功或全失败）
    """
    
    # 兼容从HTTP请求体读取
    if requests is None and frappe.request and frappe.request.json:
        data = frappe.request.json
        if isinstance(data, dict):
            if 'requests' in data:
                requests = data['requests']
            elif 'data_list' in data:
                requests = data['data_list']
            elif 'json_data' in data:
                requests = data['json_data']
            else:
                if isinstance(data, list):
                    requests = data
        elif isinstance(data, list):
            requests = data
    
    # 字符串转JSON
    if isinstance(requests, str):
        try:
            requests = json.loads(requests)
        except Exception:
            frappe.throw("requests 参数不是有效的JSON字符串")
    
    if not isinstance(requests, (list, tuple)) or not requests:
        frappe.throw("requests 必须为非空数组")
    
    created_purchase_orders = []
    created_subcontracting_orders = []
    
    try:
        # 开始数据库事务
        frappe.db.begin()
        
        # 第一阶段：创建所有采购订单（在事务中）
        for index, req in enumerate(requests, start=1):
            if not isinstance(req, dict):
                raise ValueError(f"第 {index} 条请求必须为字典")
            
            try:
                purchase_order = _create_single_subcontracting_service_po_internal(req)
                created_purchase_orders.append({
                    "index": index,
                    "purchase_order": purchase_order,
                    "request": req
                })
            except Exception as e:
                raise ValueError(f"第 {index} 条采购订单创建失败: {str(e)}")
        
        # 第二阶段：创建委外工单（如果需要）
        for item in created_purchase_orders:
            purchase_order = item["purchase_order"]
            req = item["request"]
            
            # 只有已提交的采购订单且要求自动创建委外工单才创建
            auto_create_sco = req.get('auto_create_sco', True)
            submit_doc = req.get('submit_doc', True)
            
            if auto_create_sco and submit_doc:
                supplier_warehouse = req.get('supplier_warehouse')
                subcontracting_order_name = create_subcontracting_order_from_po(
                    purchase_order.name, 
                    supplier_warehouse
                )
                if subcontracting_order_name:
                    created_subcontracting_orders.append({
                        "purchase_order": purchase_order.name,
                        "subcontracting_order": subcontracting_order_name
                    })
        
        # 提交事务
        frappe.db.commit()
        
        # 构建成功返回结果
        results = []
        for item in created_purchase_orders:
            po = item["purchase_order"]
            req = item["request"]
            
            result_item = {
                "index": item["index"],
                "status": "success",
                "purchase_order": po.name,
                "total_amount": po.grand_total,
                "base_total_amount": po.base_grand_total,
                "doc_status": "已提交" if req.get('submit_doc', True) else "草稿"
            }
            
            # 查找对应的委外工单
            for sco_item in created_subcontracting_orders:
                if sco_item["purchase_order"] == po.name:
                    result_item["subcontracting_order"] = sco_item["subcontracting_order"]
                    break
            
            results.append(result_item)
        
        return {
            "status": "success",
            "message": f"批量创建成功，共创建 {len(created_purchase_orders)} 个采购订单，{len(created_subcontracting_orders)} 个委外工单",
            "summary": {
                "total": len(created_purchase_orders),
                "success": len(created_purchase_orders),
                "error": 0,
                "purchase_orders_created": len(created_purchase_orders),
                "subcontracting_orders_created": len(created_subcontracting_orders)
            },
            "results": results
        }
        
    except Exception as e:
        # 回滚事务
        frappe.db.rollback()
        
        error_msg = str(e)
        frappe.log_error(f"批量创建委外加工服务费采购订单失败: {error_msg}", "批量委外加工采购订单创建错误")
        
        return {
            "status": "error",
            "message": f"批量创建失败，所有操作已回滚: {error_msg}",
            "summary": {
                "total": len(requests),
                "success": 0,
                "error": len(requests)
            },
            "error": error_msg
        }
