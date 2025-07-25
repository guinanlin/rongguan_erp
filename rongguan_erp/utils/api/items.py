# Server Script: get_items_with_attributes
# Whitelisted for API access
import frappe
from frappe import _
import json
from erpnext.controllers.item_variant import create_variant



# bench --site site1.local execute rongguan_erp.utils.api.items.get_items_with_attributes --kwargs '{"filters": {"item_group": "成品"}}'
@frappe.whitelist(allow_guest=False)  # 确保只允许认证用户访问
def get_items_with_attributes(filters=None, fields=None, or_filters=None, order_by=None, limit_page_length=None, limit_start=0):
    if not filters:
        filters = {}
    
    items = frappe.get_all(
        'Item',
        filters=filters,
        fields=fields or ["*"],
        or_filters=or_filters,
        order_by=order_by,
        limit_page_length=limit_page_length,
        limit_start=limit_start,
        pluck='name'
    )

    result = []
    for item in items:
        doc = frappe.get_doc('Item', item)
        data = doc.as_dict()
        data["attributes"] = doc.attributes
        result.append(data)

    return result

# 要从 API 调用此脚本，使用以下 URL：
# http://192.168.32.20:8000/api/method/get_items_with_attributes?filters={"item_group": "成品"}&fields=["name","item_code"]

# bench --site site1.local execute rongguan_erp.utils.api.items.get_items_attribute_with_value --kwargs '{"filters": {"item_group": "成品"}}'
@frappe.whitelist(allow_guest=False)  # 确保只允许认证用户访问
def get_items_attribute_with_value(filters=None, fields=None):
    if not filters:
        filters = {}
    
    items = frappe.get_all(
        'Item Attribute Value',
        filters=filters,
        fields=fields or ["*"],
        pluck='name'
    )

    result = []
    for item in items:
        doc = frappe.get_doc('Item Attribute Value', item)
        data = doc.as_dict()
        result.append(data)

    return result

# bench --site site1.local execute rongguan_erp.utils.api.items.get_items_by_item_group --kwargs '{"item_group_name": "成品"}'
@frappe.whitelist()
def get_boms_by_item_group(item_group_name):
    """
    根据指定的 Item Group 获取该分类下的所有物料信息（含 BOM、工序等）
    """
    if not item_group_name:
        frappe.throw(_("Item Group 名称不能为空"))

    # Step 1: 使用 SQL 查询获取指定 Item Group 下且有默认 BOM 的物料
    items = frappe.db.sql("""
        SELECT item.name, item.item_code, item.item_name, item.stock_uom, 
               item.variant_of,bom.name as bom_name,bom.is_active,bom.is_default
        FROM `tabItem` AS item
        INNER JOIN `tabBOM` AS bom ON bom.item = item.name
        WHERE item.item_group = %s AND bom.is_active = 1 AND bom.is_default = 1
    """, (item_group_name,), as_dict=True)

    result = []

    for item in items:
        # 获取规格信息（Item Variant Attributes）并转换为字典
        attrs = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": item.name},
            fields=["attribute", "attribute_value"]
        )
        specification_dict = {}
        if attrs:
            for attr in attrs:
                specification_dict[attr.attribute] = attr.attribute_value  # 转换为字典格式

        # Step 3: 获取工序数量（通过 Routing）
        # boms = frappe.get_all(
        #     "BOM",
        #     filters={"item": item.name, "is_active": 1, "is_default": 1},
        #     fields=["routing"]
        # )        
       
        routings = frappe.get_all(
            "BOM Operation",
            filters={"parent": item.bom_name},
            fields=["operation"]
        )
        operation_count = len(routings)

        # Step 4: 获取 BOM 信息
        bom_data = None
        boms_info = frappe.get_all(
            "BOM",
            filters={"item": item.name, "is_active": 1, "is_default": 1},
            fields=["name", "docstatus"]
        )
        if boms_info:
            bom_no = boms_info[0].name
            status = "Submitted" if boms_info[0].docstatus == 1 else "Draft"
        else:
            bom_no = None  # 或其他默认值
            status = None  # 或其他默认值

        bom_items = frappe.get_all(
            "BOM Item",
            filters={"parent": item.bom_name},
            fields=["qty", "uom", "item_code", "item_name"]
        )

        bom_items_count = len(bom_items)

        # 构建最终的 result 项（将 bom_no 和 status 提升到顶层）
        result_item = {
            "bom_no": bom_no,  # 直接作为顶层字段
            "status": status,  # 直接作为顶层字段
            "is_active": item.is_active,
            "is_default": item.is_default,
            "item": {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "UOM": item.stock_uom
            },
            "bom_items": bom_items,
            "bom_items_count": bom_items_count,
            "bom_operation_count": operation_count,
            "specification": specification_dict
        }

        result.append(result_item)

    return result

# file: rongguan_erp/utils/api/items.py
# 示例用法:
# bench --site site1.local execute rongguan_erp.utils.api.items.get_items_with_attributes_with_pagination --kwargs '{"filters": {"item_group": "成品"}, "page_number": 1, "page_size": 10}'
@frappe.whitelist(allow_guest=False)
def get_items_with_attributes_with_pagination(filters=None, fields=None, page_number=1, page_size=20):
    # 输出所有输入的参数
    print(f"Input parameters: filters={filters}, fields={fields}, page_number={page_number}, page_size={page_size}")

    # 强制将 filters 参数（如果它是字符串的话）通过 json.loads() 转换为正确的 Python 对象
    # 考虑到 Frappe 可能将 URL 参数解析为字符列表，需要先将其拼接回字符串
    if isinstance(filters, list) and all(isinstance(char, str) and len(char) == 1 for char in filters):
        try:
            filters_str = "".join(filters)
            filters = json.loads(filters_str)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON format for filters after reconstruction."))
        except Exception as e:
            frappe.log_error(f"Error reconstructing or parsing filters: {e}", "Filters Reconstruction Error")
            frappe.throw(_("An error occurred while processing filters."))
    elif isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON format for filters."))

    if not filters:
        filters = {}

    page_number = int(page_number)
    page_size = int(page_size)

    if page_number < 1:
        page_number = 1
    if page_size < 1:
        page_size = 20

    # 获取总条目数
    print(f"filters (after json.loads and reconstruction)===========: {filters}")
    total_items = frappe.db.count('Item', filters=filters)
    print(f"total_items===========: {total_items}")
    
    # 计算总页数
    total_pages = (total_items + page_size - 1) // page_size

    # 计算偏移量
    offset = (page_number - 1) * page_size

    items = frappe.get_all(
        'Item',
        filters=filters,
        fields=fields or ["*"],
        limit_page_length=page_size,
        limit_start=offset,
        pluck='name',
        order_by="creation desc"
    )

    result_data = []
    for item in items:
        doc = frappe.get_doc('Item', item)
        data = doc.as_dict()
        
        # 初始化一个空列表来存放处理后的属性
        processed_attributes = []
        for attr_doc in doc.attributes:
            attr_dict = attr_doc.as_dict()  # 将 ItemVariantAttribute 对象转换为字典
            try:
                item_attribute_doc = frappe.get_doc("Item Attribute", attr_dict.get("attribute"))
                attr_dict["_user_tags"] = item_attribute_doc._user_tags
            except frappe.DoesNotExistError:
                attr_dict["_user_tags"] = ""
            except Exception as e:
                frappe.log_error(f"Error fetching _user_tags for Item Attribute {attr_dict.get('attribute')}: {e}", "Item Attribute Fetch Error")
                attr_dict["_user_tags"] = ""

            # 根据 _user_tags 判断 attribute_type
            if attr_dict.get("_user_tags"):
                if "颜色" in attr_dict["_user_tags"]:
                    attr_dict["attribute_type"] = "color"
                elif "尺寸" in attr_dict["_user_tags"]:
                    attr_dict["attribute_type"] = "size"
                else:
                    attr_dict["attribute_type"] = ""
            else:
                attr_dict["attribute_type"] = ""

            processed_attributes.append(attr_dict)
        
        data["attributes"] = processed_attributes # 用处理后的列表替换原始属性

        result_data.append(data)
    print(f"Result data===========: {total_items} {total_pages} {page_number} {page_size}")
    pagination_info = {
        "page_number": page_number,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_items": total_items
    }

    # 打印计算后的分页信息，用于调试
    print(f"Calculated pagination info: page_number={page_number}, page_size={page_size}, total_pages={total_pages}, total_items={total_items}")

    return {
        "data": result_data,
        "pagination": pagination_info
    }

# bench --site site1.local execute rongguan_erp.utils.api.items.create_style_number_number_by_custom_item_code --kwargs '{"item_data": {"doctype": "Item", "item_code": "A013", "item_name": "测xx224", "item_group": "成品", "stock_uom": "件", "has_variants": 1, "attributes": [{"attribute": "颜色", "attribute_value": "颜色"}, {"attribute": "尺寸", "attribute_value": "荣冠尺码"}]}}'
# 返回结果:
# {"item_code": "A013", "item_name": "测xx224", "message": "Item created successfully with custom item_code"}
@frappe.whitelist()
def create_style_number_number_by_custom_item_code(item_data):
    if isinstance(item_data, str):
        try:
            item_data = json.loads(item_data)
        except json.JSONDecodeError:
             frappe.throw(_("Invalid JSON input."))

    if not isinstance(item_data, dict):
        frappe.throw(_("Invalid input. Expected a dictionary."))

    if item_data.get("doctype") != "Item":
         frappe.throw(_("Invalid doctype specified. Must be 'Item'."))

    # 检查是否是变体物料
    has_variants = item_data.get("has_variants")
    variant_of = item_data.get("variant_of")
    provided_item_code = item_data.get("item_code")
    attachment_urls = item_data.get("attachment_urls", [])  # 获取多个附件 URL，默认为空列表

    if has_variants or variant_of:  # 如果是变体相关的物料
        if provided_item_code:
            try:
                # 设置标志以禁用自动命名
                frappe.flags.in_import = True
                
                doc = frappe.get_doc(item_data)
                doc.name = provided_item_code
                doc.item_code = provided_item_code
                doc.insert(ignore_if_duplicate=True)
                
                # 处理多个附件
                for url in attachment_urls:
                    file_doc = frappe.get_doc({
                        "doctype": "File",
                        "file_url": url,
                        "attached_to_doctype": "Item",
                        "attached_to_name": doc.name,
                        "folder": "Home/Attachments"
                    })
                    file_doc.insert()
                
                # 重置标志
                frappe.flags.in_import = False
                
                frappe.db.commit()
                return {
                    "item_code": doc.name,
                    "item_name": doc.item_name,
                    "message": _("Item created successfully with custom item_code")
                }
            except Exception as e:
                frappe.db.rollback()
                frappe.flags.in_import = False
                frappe.throw(_("Failed to create Item: {0}").format(str(e)))
    
    # 对于非变体物料，使用默认的自动命名
    doc = frappe.get_doc(item_data)
    doc.insert()
    
    # 处理多个附件
    for url in attachment_urls:
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_url": url,
            "attached_to_doctype": "Item",
            "attached_to_name": doc.name,
            "folder": "Home/Attachments"
        })
        file_doc.insert()
    
    frappe.db.commit()
    
    return {
        "item_code": doc.name,
        "item_name": doc.item_name,
        "message": _("Item created successfully with auto-generated item_code")
    }


@frappe.whitelist()
def get_item_color_values(item_code):
    if not item_code:
        return {"error": "item_code is required"}

    item = frappe.get_doc("Item", item_code)

    color_attributes = []

    for attr in item.attributes:
        try:
            attr_doc = frappe.get_doc("Item Attribute", attr.attribute)
            if attr_doc._user_tags and "颜色" in attr_doc._user_tags:
                color_values = [v.attribute_value for v in attr_doc.item_attribute_values]
                color_attributes.append({
                    "attribute": attr.attribute,
                    "values": color_values
                })
        except frappe.DoesNotExistError:
            continue

    if not color_attributes:
        return {"error": "No attribute with tag '颜色' found for this item"}

    return {
        "color_attributes": color_attributes
    }    
@frappe.whitelist()
def get_item_size_values(item_code):
    if not item_code:
        return {"error": "item_code is required"}

    item = frappe.get_doc("Item", item_code)

    size_attributes = []

    for attr in item.attributes:
        try:
            attr_doc = frappe.get_doc("Item Attribute", attr.attribute)
            if attr_doc._user_tags and "尺寸" in attr_doc._user_tags:
                size_values = [v.attribute_value for v in attr_doc.item_attribute_values]
                size_attributes.append({
                    "attribute": attr.attribute,
                    "values": size_values
                })
        except frappe.DoesNotExistError:
            continue

    if not size_attributes:
        return {"error": "No attribute with tag '荣冠尺码' found for this item"}

    return {
        "size_attributes": size_attributes
    }    

@frappe.whitelist()
def get_item_available_stock(item_code, warehouse=None, company=None):
    """
    获取物料的可用库存信息
    
    Args:
        item_code (str): 物料编码
        warehouse (str): 仓库（可选，如果不指定则获取所有仓库的总库存）
        company (str): 公司（可选，用于过滤仓库）
        
    Returns:
        dict: 包含库存信息的字典
    """
    if not item_code:
        return {"error": "item_code is required"}
    
    try:
        # 检查物料是否存在
        if not frappe.db.exists("Item", item_code):
            return {"error": f"Item {item_code} does not exist"}
        
        # 检查物料是否为库存物料
        item_doc = frappe.get_doc("Item", item_code)
        if not item_doc.is_stock_item:
            return {
                "item_code": item_code,
                "item_name": item_doc.item_name,
                "is_stock_item": False,
                "stock_uom": item_doc.stock_uom,
                "message": "This is not a stock item"
            }
        
        stock_info = {}
        
        if warehouse:
            # 获取指定仓库的库存信息
            bin_data = frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": warehouse},
                ["actual_qty", "projected_qty", "reserved_qty", "ordered_qty", "planned_qty"],
                as_dict=True
            )
            
            if bin_data:
                stock_info = {
                    "warehouse": warehouse,
                    "actual_qty": bin_data.actual_qty or 0,
                    "projected_qty": bin_data.projected_qty or 0,
                    "reserved_qty": bin_data.reserved_qty or 0,
                    "ordered_qty": bin_data.ordered_qty or 0,
                    "planned_qty": bin_data.planned_qty or 0
                }
            else:
                stock_info = {
                    "warehouse": warehouse,
                    "actual_qty": 0,
                    "projected_qty": 0,
                    "reserved_qty": 0,
                    "ordered_qty": 0,
                    "planned_qty": 0
                }
        else:
            # 获取所有仓库的总库存
            if not company:
                company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
            
            # 使用 SQL 查询获取汇总数据
            bin_data = frappe.db.sql("""
                SELECT 
                    SUM(actual_qty) as actual_qty,
                    SUM(projected_qty) as projected_qty,
                    SUM(reserved_qty) as reserved_qty,
                    SUM(ordered_qty) as ordered_qty,
                    SUM(planned_qty) as planned_qty
                FROM `tabBin` b
                LEFT JOIN `tabWarehouse` w ON b.warehouse = w.name
                WHERE b.item_code = %s
                AND (w.company = %s OR %s IS NULL)
            """, (item_code, company, company), as_dict=True)
            
            if bin_data and bin_data[0]:
                data = bin_data[0]
                stock_info = {
                    "warehouse": "All Warehouses",
                    "actual_qty": data.actual_qty or 0,
                    "projected_qty": data.projected_qty or 0,
                    "reserved_qty": data.reserved_qty or 0,
                    "ordered_qty": data.ordered_qty or 0,
                    "planned_qty": data.planned_qty or 0,
                    "company": company
                }
            else:
                stock_info = {
                    "warehouse": "All Warehouses",
                    "actual_qty": 0,
                    "projected_qty": 0,
                    "reserved_qty": 0,
                    "ordered_qty": 0,
                    "planned_qty": 0,
                    "company": company
                }
        
        result = {
            "item_code": item_code,
            "item_name": item_doc.item_name,
            "is_stock_item": True,
            "stock_uom": item_doc.stock_uom,
            "stock_info": stock_info
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in get_item_available_stock for {item_code}: {str(e)}", "Item Stock API Error")
        return {"error": f"Failed to get item stock: {str(e)}"}

@frappe.whitelist()
def get_item_rate_info(item_code, company=None, rm_cost_as_per="Valuation Rate", buying_price_list=None, qty=1, warehouse=None):
    """
    根据 item_code 获取该物料的 rate 信息（不依赖已存在的 BOM）
    模拟 BOM Creator 中选择物料时自动计算 rate 的逻辑
    
    Args:
        item_code (str): 物料编码
        company (str): 公司（可选，默认取默认公司）
        rm_cost_as_per (str): 原材料成本来源，可选值：'Valuation Rate', 'Last Purchase Rate', 'Price List'
        buying_price_list (str): 采购价格清单（可选）
        qty (float): 数量（默认为1）
        warehouse (str): 仓库（可选，用于获取库存信息）
        
    Returns:
        dict: 包含物料 rate 信息和库存信息的字典
    """
    if not item_code:
        return {"error": "item_code is required"}
    
    try:
        # 检查物料是否存在
        if not frappe.db.exists("Item", item_code):
            return {"error": f"Item {item_code} does not exist"}
        
        # 获取物料基本信息
        item_doc = frappe.get_doc("Item", item_code)
        
        # 如果没有指定公司，使用默认公司
        if not company:
            company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
        
        # 导入 get_bom_item_rate 函数
        from erpnext.manufacturing.doctype.bom.bom import get_bom_item_rate
        
        # 准备参数，模拟 BOM Creator 的逻辑
        args = {
            "company": company,
            "item_code": item_code,
            "bom_no": "",
            "qty": float(qty),
            "uom": item_doc.stock_uom,
            "stock_uom": item_doc.stock_uom,
            "conversion_factor": 1.0,
            "sourced_by_supplier": 0,
        }
        
        # 创建一个模拟的 BOM Creator 对象来传递参数
        mock_bom_creator = frappe._dict({
            "company": company,
            "rm_cost_as_per": rm_cost_as_per,
            "buying_price_list": buying_price_list,
            "currency": frappe.get_cached_value("Company", company, "default_currency"),
            "conversion_rate": 1.0,
            "plc_conversion_rate": 1.0,
            "set_rate_based_on_warehouse": 0,
        })
        
        # 调用 get_bom_item_rate 获取 rate
        rate = get_bom_item_rate(args, mock_bom_creator)
        
        # 计算金额
        amount = float(rate) * float(qty)
        
        # 获取库存信息
        stock_info = get_item_available_stock(item_code, warehouse, company)
        
        result = {
            "item_code": item_code,
            "item_name": item_doc.item_name,
            "stock_uom": item_doc.stock_uom,
            "qty": float(qty),
            "rate": rate,
            "amount": amount,
            "company": company,
            "rm_cost_as_per": rm_cost_as_per,
            "buying_price_list": buying_price_list,
            "currency": mock_bom_creator.currency,
            "rate_source": f"Calculated using {rm_cost_as_per}",
            "stock_info": stock_info.get("stock_info") if stock_info.get("stock_info") else None,
            "is_stock_item": stock_info.get("is_stock_item", False)
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in get_item_rate_info for {item_code}: {str(e)}", "Item Rate API Error")
        return {"error": f"Failed to get item rate: {str(e)}"}


@frappe.whitelist()
def get_item_bom_items(item_code):
    """
    根据 item_code 获取该物料的默认 BOM 中的所有 BOM Items 和 rate 信息
    
    Args:
        item_code (str): 物料编码
        
    Returns:
        dict: 包含 BOM Items 信息的字典
    """
    if not item_code:
        return {"error": "item_code is required"}
    
    try:
        # 检查物料是否存在
        if not frappe.db.exists("Item", item_code):
            return {"error": f"Item {item_code} does not exist"}
        
        # 获取物料的默认 BOM
        default_bom = frappe.get_value("Item", item_code, "default_bom")
        
        if not default_bom:
            return {"error": f"No default BOM found for item {item_code}"}
        
        # 获取 BOM 基本信息
        bom_doc = frappe.get_doc("BOM", default_bom)
        
        # 获取 BOM Items
        bom_items = frappe.get_all(
            "BOM Item",
            filters={"parent": default_bom},
            fields=[
                "item_code",
                "item_name", 
                "qty",
                "uom",
                "rate",
                "amount",
                "stock_qty",
                "stock_uom",
                "conversion_factor",
                "bom_no",
                "sourced_by_supplier",
                "allow_alternative_item",
                "idx"
            ],
            order_by="idx"
        )
        
        # 计算总成本
        total_cost = sum(item.get("amount", 0) for item in bom_items)
        
        result = {
            "item_code": item_code,
            "bom_no": default_bom,
            "bom_quantity": bom_doc.quantity,
            "total_cost": total_cost,
            "currency": bom_doc.currency,
            "company": bom_doc.company,
            "bom_items_count": len(bom_items),
            "bom_items": bom_items
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in get_item_bom_items for {item_code}: {str(e)}", "BOM Items API Error")
        return {"error": f"Failed to get BOM items: {str(e)}"}    

@frappe.whitelist()
def update_item_custom_bom_operation(item_code, custom_bom_operation):
    """
    更新指定物料的 custom_bom_operation 字段
    
    Args:
        item_code (str): 物料编码
        custom_bom_operation (list): BOM Operation 列表数据
        
    Returns:
        dict: 更新结果
    """
    if not item_code:
        return {"error": "item_code is required"}
    
    # 如果 custom_bom_operation 是字符串，尝试解析为 JSON
    if isinstance(custom_bom_operation, str):
        try:
            custom_bom_operation = json.loads(custom_bom_operation)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON format for custom_bom_operation"))
    
    if not isinstance(custom_bom_operation, list):
        frappe.throw(_("custom_bom_operation must be a list"))
    
    try:
        # 检查物料是否存在
        if not frappe.db.exists("Item", item_code):
            return {"error": f"Item {item_code} does not exist"}
        
        # 首先检查并创建不存在的 Operation
        created_operations = []
        for operation_data in custom_bom_operation:
            operation_name = operation_data.get("operation", "").strip()
            if operation_name and not frappe.db.exists("Operation", operation_name):
                try:
                    # 创建新的 Operation
                    operation_doc = frappe.get_doc({
                        "doctype": "Operation",
                        "operation": operation_name,
                        "workstation": operation_data.get("workstation_type") or operation_data.get("workstation")
                    })
                    operation_doc.insert()
                    created_operations.append(operation_name)
                except Exception as e:
                    frappe.log_error(f"Error creating Operation {operation_name}: {str(e)}", "Create Operation Error")
                    # 继续处理，不因为创建 Operation 失败而中断整个流程
        
        # 获取物料文档
        item_doc = frappe.get_doc("Item", item_code)
        
        # 清空现有的 custom_bom_operation
        item_doc.custom_bom_operation = []
        
        # 添加新的 BOM Operation 记录
        for idx, operation_data in enumerate(custom_bom_operation, 1):
            # 创建 BOM Operation 子文档
            bom_operation = frappe.new_doc("BOM Operation")
            
            # 设置基本字段
            bom_operation.parent = item_code
            bom_operation.parentfield = "custom_bom_operation"
            bom_operation.parenttype = "Item"
            bom_operation.idx = idx
            
            # 设置操作相关字段
            bom_operation.operation = operation_data.get("operation", "")
            bom_operation.workstation_type = operation_data.get("workstation_type")
            bom_operation.workstation = operation_data.get("workstation")
            bom_operation.time_in_mins = float(operation_data.get("time_in_mins", 0))
            bom_operation.fixed_time = int(operation_data.get("fixed_time", 0))
            bom_operation.hour_rate = float(operation_data.get("hour_rate", 0))
            bom_operation.batch_size = int(operation_data.get("batch_size", 1))
            bom_operation.set_cost_based_on_bom_qty = int(operation_data.get("set_cost_based_on_bom_qty", 0))
            bom_operation.sequence_id = int(operation_data.get("sequence_id", 0))
            bom_operation.description = operation_data.get("description")
            bom_operation.image = operation_data.get("image")
            
            # 成本相关字段（通常由系统计算）
            bom_operation.base_hour_rate = float(operation_data.get("base_hour_rate", 0))
            bom_operation.operating_cost = float(operation_data.get("operating_cost", 0))
            bom_operation.base_operating_cost = float(operation_data.get("base_operating_cost", 0))
            bom_operation.cost_per_unit = float(operation_data.get("cost_per_unit", 0))
            bom_operation.base_cost_per_unit = float(operation_data.get("base_cost_per_unit", 0))
            
            # 如果有现有的name字段且不是以"new-"开头的临时名称，保留它
            if operation_data.get("name") and not operation_data.get("name", "").startswith("new-"):
                bom_operation.name = operation_data.get("name")
            
            # 添加到 item_doc 的 custom_bom_operation 列表
            item_doc.append("custom_bom_operation", bom_operation)
        
        # 保存文档
        item_doc.save()
        frappe.db.commit()
        
        # 返回更新后的数据
        updated_item = frappe.get_doc("Item", item_code)
        result = {
            "success": True,
            "message": f"Successfully updated custom_bom_operation for item {item_code}",
            "item_code": item_code,
            "custom_bom_operation_count": len(updated_item.custom_bom_operation),
            "custom_bom_operation": [op.as_dict() for op in updated_item.custom_bom_operation]
        }
        
        # 如果创建了新的 Operation，在结果中说明
        if created_operations:
            result["created_operations"] = created_operations
            result["message"] += f". Created new operations: {', '.join(created_operations)}"
        
        return result
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error updating custom_bom_operation for {item_code}: {str(e)}", "Update Custom BOM Operation Error")
        return {"error": f"Failed to update custom_bom_operation: {str(e)}"}

@frappe.whitelist()
def save_item_bom_structure(bom_data):
    """
    保存物料的 BOM 结构
    
    Args:
        bom_data (dict/str): BOM 数据，包含 BOM 基本信息、BOM Items、BOM Operations 等
        
    Returns:
        dict: 保存结果，包含创建的 BOM 名称和相关信息
    """
    print(f"=== 接收到的原始数据 ===")
    print(f"bom_data 类型: {type(bom_data)}")
    print(f"bom_data 内容: {bom_data}")
    
    if not bom_data:
        return {"error": "bom_data is required"}
    
    # 如果 bom_data 是字符串，尝试解析为 JSON
    if isinstance(bom_data, str):
        try:
            print(f"=== 解析JSON之前 ===")
            print(f"原始字符串: {bom_data}")
            bom_data = json.loads(bom_data)
            print(f"=== 解析JSON之后 ===")
            print(f"解析后的数据: {bom_data}")
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON format for bom_data"))
    
    if not isinstance(bom_data, dict):
        frappe.throw(_("bom_data must be a dictionary"))
    
    # 验证必要字段
    if bom_data.get("doctype") != "BOM":
        frappe.throw(_("Invalid doctype. Must be 'BOM'"))
    
    if not bom_data.get("item"):
        frappe.throw(_("Item code is required"))
    
    try:
        # 检查物料是否存在
        item_code = bom_data.get("item")
        if not frappe.db.exists("Item", item_code):
            return {"error": f"Item {item_code} does not exist"}
        
        # 移除临时字段，避免保存时出错
        temp_fields = ["__islocal", "__unsaved", "name"]
        cleaned_bom_data = {k: v for k, v in bom_data.items() if k not in temp_fields}
        
        # 创建 BOM 文档
        bom_doc = frappe.get_doc(cleaned_bom_data)
        
        # 清理 BOM Items 子表数据
        if "items" in cleaned_bom_data and cleaned_bom_data["items"]:
            bom_doc.items = []
            for idx, item_data in enumerate(cleaned_bom_data["items"], 1):
                # 移除临时字段
                cleaned_item_data = {k: v for k, v in item_data.items() 
                                   if k not in ["__islocal", "__unsaved", "name", "parent"]}
                
                # 设置必要字段
                cleaned_item_data["idx"] = idx
                cleaned_item_data["parentfield"] = "items"
                cleaned_item_data["parenttype"] = "BOM"
                
                # 验证必要的物料字段
                if not cleaned_item_data.get("item_code"):
                    frappe.throw(_(f"Item code is required for BOM item at index {idx}"))
                
                # 检查 BOM Item 中的物料是否存在
                if not frappe.db.exists("Item", cleaned_item_data["item_code"]):
                    frappe.throw(_(f"Item {cleaned_item_data['item_code']} does not exist"))
                
                bom_doc.append("items", cleaned_item_data)
        
        # 清理 BOM Operations 子表数据
        if "operations" in cleaned_bom_data and cleaned_bom_data["operations"]:
            bom_doc.operations = []
            for idx, operation_data in enumerate(cleaned_bom_data["operations"], 1):
                # 移除临时字段
                cleaned_operation_data = {k: v for k, v in operation_data.items() 
                                        if k not in ["__islocal", "__unsaved", "name", "parent"]}
                
                # 设置必要字段
                cleaned_operation_data["idx"] = idx
                cleaned_operation_data["parentfield"] = "operations"
                cleaned_operation_data["parenttype"] = "BOM"
                
                # 检查并创建不存在的 Operation
                operation_name = cleaned_operation_data.get("operation", "").strip()
                if operation_name and not frappe.db.exists("Operation", operation_name):
                    try:
                        operation_doc = frappe.get_doc({
                            "doctype": "Operation",
                            "operation": operation_name,
                            "workstation": cleaned_operation_data.get("workstation")
                        })
                        operation_doc.insert()
                    except Exception as e:
                        frappe.log_error(f"Error creating Operation {operation_name}: {str(e)}", "Create Operation Error")
                
                bom_doc.append("operations", cleaned_operation_data)
        
        # 清理 Scrap Items 子表数据（如果有）
        if "scrap_items" in cleaned_bom_data and cleaned_bom_data["scrap_items"]:
            bom_doc.scrap_items = []
            for idx, scrap_data in enumerate(cleaned_bom_data["scrap_items"], 1):
                cleaned_scrap_data = {k: v for k, v in scrap_data.items() 
                                    if k not in ["__islocal", "__unsaved", "name", "parent"]}
                
                cleaned_scrap_data["idx"] = idx
                cleaned_scrap_data["parentfield"] = "scrap_items"
                cleaned_scrap_data["parenttype"] = "BOM"
                
                bom_doc.append("scrap_items", cleaned_scrap_data)
        
        # 保存 BOM 文档
        bom_doc.insert()
        
        # 自动提交 BOM 文档，使其从草稿状态变为已提交状态
        bom_doc.submit()
        
        # 如果设置为默认 BOM，更新物料的 default_bom 字段
        if bom_doc.is_default:
            frappe.db.set_value("Item", item_code, "default_bom", bom_doc.name)
        
        frappe.db.commit()
        
        # 如果bom_data中包含销售订单号，则更新销售订单明细中的BOM编号
        sales_order_no = bom_data.get("sales_order")
        print(f"=== 调试信息 ===")
        print(f"bom_data中的sales_order: {sales_order_no}")
        print(f"物料编码: {item_code}")
        print(f"BOM编号: {bom_doc.name}")
        
        if sales_order_no:
            try:
                print(f"开始调用update_sales_order_item_bom_no方法...")
                
                update_result = update_sales_order_item_bom_no(sales_order_no, item_code, bom_doc.name)
                
                print(f"更新结果: {update_result}")
                
                if not update_result.get("success"):
                    print(f"更新失败: {update_result.get('error')}")
                    frappe.log_error(f"更新销售订单BOM编号失败: {update_result.get('error')}", "Update Sales Order BOM Error")
                else:
                    print(f"更新成功: {update_result.get('message')}")
            except Exception as e:
                print(f"调用更新方法时出错: {str(e)}")
                frappe.log_error(f"调用更新销售订单BOM编号方法时出错: {str(e)}", "Call Update Sales Order BOM Error")
        else:
            print(f"没有销售订单号，跳过更新")
        
        # 返回创建结果
        result = {
            "success": True,
            "message": f"BOM created successfully for item {item_code}",
            "bom_name": bom_doc.name,
            "item_code": item_code,
            "item_name": bom_doc.item_name,
            "quantity": bom_doc.quantity,
            "is_active": bom_doc.is_active,
            "is_default": bom_doc.is_default,
            "total_cost": bom_doc.total_cost,
            "currency": bom_doc.currency,
            "company": bom_doc.company,
            "bom_items_count": len(bom_doc.items),
            "bom_operations_count": len(bom_doc.operations) if bom_doc.operations else 0
        }
        
        # 如果更新了销售订单，在返回结果中添加相关信息
        if sales_order_no:
            result["sales_order_updated"] = True
            result["sales_order_no"] = sales_order_no
            result["message"] += f" and updated Sales Order {sales_order_no}"
        
        return result
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error saving BOM for item {bom_data.get('item', 'Unknown')}: {str(e)}", "Save BOM Error")
        return {"error": f"Failed to save BOM: {str(e)}"}

@frappe.whitelist()
def bulk_save_item_boms(boms_data):
    """
    批量保存物料的 BOM 结构，并支持事务。

    Args:
        boms_data (list/str): 包含多个 BOM 数据的列表或 JSON 字符串。
                               每个 BOM 数据应是 save_item_bom_structure 函数期望的字典格式。

    Returns:
        dict: 批量保存的结果，包含成功和失败的 BOM 列表及总体状态。
    """
    if not boms_data:
        return {"error": "boms_data is required and cannot be empty"}

    # 如果 boms_data 是字符串，尝试解析为 JSON
    if isinstance(boms_data, str):
        try:
            boms_data = json.loads(boms_data)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON format for boms_data"))

    if not isinstance(boms_data, list):
        frappe.throw(_("boms_data must be a list of BOM dictionaries"))

    successful_boms = []
    failed_boms = []
    
    frappe.db.begin() # 开始数据库事务

    try:
        for idx, bom_data in enumerate(boms_data):
            try:
                # 调用现有的 save_item_bom_structure 来处理单个 BOM
                # 注意：这里我们调用的是内部逻辑，而不是 whitelisted 的接口本身，
                # 因为整个事务由 bulk_save_item_boms 统一管理。
                # 为此，我们需要确保 save_item_bom_structure 的核心逻辑可以被复用。
                # 为了简化，这里直接将 save_item_bom_structure 的核心逻辑复制过来，
                # 或者可以重构 save_item_bom_structure 使其返回更详细的结果，并在外部捕获异常。
                
                # --- save_item_bom_structure 的核心逻辑复制开始 ---
                if bom_data.get("doctype") != "BOM":
                    raise frappe.ValidationError(_("Invalid doctype. Must be 'BOM' for BOM at index {0}").format(idx))
                
                item_code = bom_data.get("item")
                if not item_code:
                    raise frappe.ValidationError(_("Item code is required for BOM at index {0}").format(idx))
                
                if not frappe.db.exists("Item", item_code):
                    raise frappe.DoesNotExistError(f"Item {item_code} does not exist for BOM at index {idx}")

                temp_fields = ["__islocal", "__unsaved", "name"]
                cleaned_bom_data = {k: v for k, v in bom_data.items() if k not in temp_fields}
                
                bom_doc = frappe.get_doc(cleaned_bom_data)
                
                if "items" in cleaned_bom_data and cleaned_bom_data["items"]:
                    bom_doc.items = []
                    for item_idx, item_data in enumerate(cleaned_bom_data["items"], 1):
                        cleaned_item_data = {k: v for k, v in item_data.items() 
                                           if k not in ["__islocal", "__unsaved", "name", "parent"]}
                        cleaned_item_data["idx"] = item_idx
                        cleaned_item_data["parentfield"] = "items"
                        cleaned_item_data["parenttype"] = "BOM"
                        if not cleaned_item_data.get("item_code"):
                            raise frappe.ValidationError(_(f"Item code is required for BOM item at index {item_idx} in BOM {idx}"))
                        if not frappe.db.exists("Item", cleaned_item_data["item_code"]):
                            raise frappe.DoesNotExistError(f"Item {cleaned_item_data['item_code']} does not exist for BOM item at index {item_idx} in BOM {idx}")
                        bom_doc.append("items", cleaned_item_data)
                
                if "operations" in cleaned_bom_data and cleaned_bom_data["operations"]:
                    bom_doc.operations = []
                    for op_idx, operation_data in enumerate(cleaned_bom_data["operations"], 1):
                        cleaned_operation_data = {k: v for k, v in operation_data.items() 
                                                if k not in ["__islocal", "__unsaved", "name", "parent"]}
                        cleaned_operation_data["idx"] = op_idx
                        cleaned_operation_data["parentfield"] = "operations"
                        cleaned_operation_data["parenttype"] = "BOM"
                        operation_name = cleaned_operation_data.get("operation", "").strip()
                        if operation_name and not frappe.db.exists("Operation", operation_name):
                            try:
                                operation_doc = frappe.get_doc({
                                    "doctype": "Operation",
                                    "operation": operation_name,
                                    "workstation": cleaned_operation_data.get("workstation")
                                })
                                operation_doc.insert()
                            except Exception as e:
                                frappe.log_error(f"Error creating Operation {operation_name}: {str(e)}", "Create Operation Error")
                        bom_doc.append("operations", cleaned_operation_data)
                
                if "scrap_items" in cleaned_bom_data and cleaned_bom_data["scrap_items"]:
                    bom_doc.scrap_items = []
                    for scrap_idx, scrap_data in enumerate(cleaned_bom_data["scrap_items"], 1):
                        cleaned_scrap_data = {k: v for k, v in scrap_data.items() 
                                            if k not in ["__islocal", "__unsaved", "name", "parent"]}
                        cleaned_scrap_data["idx"] = scrap_idx
                        cleaned_scrap_data["parentfield"] = "scrap_items"
                        cleaned_scrap_data["parenttype"] = "BOM"
                        bom_doc.append("scrap_items", cleaned_scrap_data)
                
                bom_doc.insert()
                bom_doc.submit()
                
                if bom_doc.is_default:
                    frappe.db.set_value("Item", item_code, "default_bom", bom_doc.name)
                
                # --- save_item_bom_structure 的核心逻辑复制结束 ---

                # 如果成功，记录 BOM 名称和物料编码
                successful_boms.append({
                    "item_code": item_code,
                    "bom_name": bom_doc.name,
                    "message": "BOM created successfully"
                })
            except Exception as e:
                # 如果单个 BOM 失败，记录错误信息，但允许其他 BOM 继续处理
                frappe.log_error(f"Error processing BOM at index {idx} for item {bom_data.get('item', 'Unknown')}: {str(e)}")
                failed_boms.append({
                    "item_code": bom_data.get("item", "Unknown"),
                    "error": str(e),
                    "original_data": bom_data # 可以选择包含原始数据以便调试
                })
        
        # 如果有任何BOM处理失败，则整个批量操作的结果应被视为不成功
        operation_successful = not failed_boms

        frappe.db.commit() # 所有 BOM 处理成功，提交事务
        return {
            "success": operation_successful,
            "message": f"Bulk BOM save operation completed. {len(successful_boms)} successful, {len(failed_boms)} failed.",
            "successful_boms": successful_boms,
            "failed_boms": failed_boms
        }

    except Exception as e:
        frappe.db.rollback() # 任何一个 BOM 失败，回滚整个事务
        frappe.log_error(f"Critical error during bulk BOM save: {str(e)}", "Bulk BOM Save Transaction Error")
        return {
            "success": False,
            "message": f"Bulk BOM save operation failed due to a critical error. All changes rolled back. Error: {str(e)}",
            "successful_boms": [], # 事务回滚，所以成功列表为空
            "failed_boms": boms_data # 或者将所有原始数据放入失败列表，因为它整体回滚了
        }

def update_sales_order_item_bom_no(sales_order_no, item_code, bom_no):
    """
    更新销售订单明细中指定物料的BOM编号
    
    Args:
        sales_order_no (str): 销售订单号
        item_code (str): 销售订单项的物料编码
        bom_no (str): 要更新的BOM编号
        
    Returns:
        dict: 更新结果
    """
    print(f"=== update_sales_order_item_bom_no 开始 ===")
    print(f"销售订单号: {sales_order_no}")
    print(f"物料编码: {item_code}")
    print(f"BOM编号: {bom_no}")
    
    if not sales_order_no:
        return {"error": "销售订单号不能为空"}
    
    if not item_code:
        return {"error": "物料编码不能为空"}
    
    if not bom_no:
        return {"error": "BOM编号不能为空"}
    
    try:
        # 检查销售订单是否存在
        print(f"检查销售订单是否存在...")
        if not frappe.db.exists("Sales Order", sales_order_no):
            print(f"销售订单不存在")
            return {"error": f"销售订单 {sales_order_no} 不存在"}
        
        # 检查BOM是否存在
        print(f"检查BOM是否存在...")
        if not frappe.db.exists("BOM", bom_no):
            print(f"BOM不存在")
            return {"error": f"BOM {bom_no} 不存在"}
        
        # 获取销售订单文档
        print(f"获取销售订单文档...")
        sales_order_doc = frappe.get_doc("Sales Order", sales_order_no)
        print(f"销售订单项数量: {len(sales_order_doc.items)}")
        
        # 查找匹配的销售订单项
        updated_item = None
        for i, item in enumerate(sales_order_doc.items):
            print(f"检查第{i+1}项: {item.item_code}")
            if item.item_code == item_code:
                print(f"找到匹配项，当前BOM编号: {item.bom_no}")
                # 更新BOM编号
                item.bom_no = bom_no
                print(f"更新BOM编号为: {bom_no}")
                updated_item = item
                break
        
        if not updated_item:
            print(f"未找到匹配的物料项")
            return {"error": f"在销售订单 {sales_order_no} 中未找到物料 {item_code}"}
        
        # 保存销售订单
        print(f"保存销售订单...")
        sales_order_doc.save()
        frappe.db.commit()
        print(f"保存成功")
        
        return {
            "success": True,
            "message": f"成功更新销售订单 {sales_order_no} 中物料 {item_code} 的BOM编号为 {bom_no}",
            "sales_order_no": sales_order_no,
            "item_code": item_code,
            "bom_no": bom_no,
            "updated_item_name": updated_item.item_name
        }
        
    except Exception as e:
        frappe.db.rollback()
        print(f"更新过程中出错: {str(e)}")
        frappe.log_error(f"更新销售订单 {sales_order_no} 中物料 {item_code} 的BOM编号时出错: {str(e)}", "Update Sales Order Item BOM Error")
        return {"error": f"更新失败: {str(e)}"}


@frappe.whitelist(allow_guest=False)
def update_sales_order_bom(**args):
    """
    更新销售订单的 BOM 编号
    
    使用 ERPNext 标准的 get_default_bom 方法自动填充销售订单明细的 BOM 编号
    系统会根据物料的默认 BOM 设置自动填充空的 bom_no 字段
    
    :param args: 包含 sales_order_name 的参数字典
        - sales_order_name: 销售订单编号
    """
    try:
        sales_order_name = args.get("sales_order_name")
        
        if not sales_order_name:
            return {"status": "error", "message": "sales_order_name 参数不能为空"}
        
        # 检查销售订单是否存在
        if not frappe.db.exists("Sales Order", sales_order_name):
            return {"status": "error", "message": f"销售订单 {sales_order_name} 不存在"}
        
        # 获取销售订单文档
        so = frappe.get_doc("Sales Order", sales_order_name)
        
        print(f"=== 调试信息 ===")
        print(f"销售订单: {sales_order_name}")
        print(f"明细项数量: {len(so.items)}")
        
        # 记录更新前的状态
        before_update = {item.name: item.bom_no for item in so.items}
        print(f"更新前的 BOM 状态: {before_update}")
        
        # 遍历销售订单明细，为每个物料设置默认 BOM
        updated_items = []
        for idx, item in enumerate(so.items):
            print(f"检查第 {idx+1} 项: {item.item_code}")
            print(f"  当前 BOM: {item.bom_no}")
            
            if item.item_code:
                # 使用 ERPNext 标准的 get_default_bom 方法获取默认 BOM
                from erpnext.stock.get_item_details import get_default_bom
                default_bom = get_default_bom(item.item_code)
                print(f"  默认 BOM: {default_bom}")
                
                if default_bom and not item.bom_no:
                    item.bom_no = default_bom
                    updated_items.append({
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "bom_no": default_bom,
                        "row_name": item.name
                    })
                    print(f"  已更新 BOM: {default_bom}")
                elif not default_bom:
                    print(f"  物料 {item.item_code} 没有默认 BOM")
                elif item.bom_no:
                    print(f"  物料 {item.item_code} 已有 BOM: {item.bom_no}")
        
        # 调用 validate 方法确保所有验证逻辑被执行
        print(f"调用 validate 方法...")
        so.validate()
        
        # 保存文档
        so.save()
        frappe.db.commit()
        
        print(f"更新完成，共更新 {len(updated_items)} 项")
        
        return {
            "status": "success", 
            "message": f"Successfully updated BOM for Sales Order {sales_order_name}",
            "sales_order": sales_order_name,
            "updated_items_count": len(updated_items),
            "updated_items": updated_items,
            "total_items_count": len(so.items),
            "debug_info": {
                "before_update": before_update,
                "after_update": {item.name: item.bom_no for item in so.items}
            }
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_sales_order_bom failed")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=False)
def check_sales_order_bom(**args):
    """
    检查销售订单的 BOM 状态
    
    :param args: 包含 sales_order 的参数字典
        - sales_order: 销售订单编号
    """
    try:
        sales_order = args.get("sales_order")
        
        if not sales_order:
            return {"status": "error", "message": "sales_order 参数不能为空"}
        
        # 检查销售订单是否存在
        if not frappe.db.exists("Sales Order", sales_order):
            return {"status": "error", "message": f"销售订单 {sales_order} 不存在"}
        
        # 获取销售订单文档
        so = frappe.get_doc("Sales Order", sales_order)
        
        items_info = []
        for idx, item in enumerate(so.items):
            # 获取物料的默认 BOM
            from erpnext.stock.get_item_details import get_default_bom
            default_bom = get_default_bom(item.item_code)
            
            # 获取物料主数据中的默认 BOM
            item_default_bom = frappe.get_value("Item", item.item_code, "default_bom")
            
            items_info.append({
                "idx": idx + 1,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "current_bom": item.bom_no,
                "default_bom_from_item": item_default_bom,
                "default_bom_from_function": default_bom,
                "has_bom": bool(item.bom_no),
                "has_default_bom": bool(default_bom)
            })
        
        return {
            "status": "success",
            "sales_order": sales_order,
            "total_items": len(so.items),
            "items_info": items_info
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "check_sales_order_bom failed")
        return {"status": "error", "message": str(e)}