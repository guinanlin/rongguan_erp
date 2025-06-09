# Server Script: save_sales_order
# Whitelisted for API access
import frappe
from frappe import _
import json
import time
from rongguan_erp.rongguan_erp.doctype.rg_production_orders.rg_production_orders import saveRGProductionOrder
from rongguan_erp.rongguan_erp.doctype.rg_production_orders.rg_production_orders_model import get_default_production_order_data


def map_sales_order_to_production_order(so, items_data):
    """
    将销售订单数据映射到生产订单模型
    
    参数:
        so (frappe.model.document.Document): 销售订单文档对象
        items_data (list): 包含销售订单明细数据的列表（字典形式）

    返回:
        dict: 生产订单所需的数据字典
    """
    print("Items Data:", json.dumps(items_data, indent=2, ensure_ascii=False))
    # 尝试获取颜色和尺码属性
    def get_item_attributes(item_dict):
        """
        从物料字典中提取颜色和尺码属性
        
        参数:
            item_dict (dict): 物料字典
        
        返回:
            tuple: (颜色, 尺码)
        """
        color = next((attr['attribute_value'] for attr in item_dict.get('attributes', [])
                       if attr.get('attribute_type') == 'color'), None)
        size = next((attr['attribute_value'] for attr in item_dict.get('attributes', [])
                      if attr.get('attribute_type') == 'size'), None)
        return color, size

    # 构建物料数据
    material_list = []
    for item_dict in items_data:
        color, size = get_item_attributes(item_dict)
        print("Item Code:", item_dict.get("item_code", ""))
        print("Color:", color, "Size:", size)
        if not color or not size:
            frappe.throw(_("颜色或尺码属性为空，请检查销售订单数据"))
        material_list.append({
            "code": item_dict.get("item_code", ""),  # Use actual item_code
            "color": color,          # 颜色
            "unit": item_dict.get("uom", ""),        # 单位
            "sizes": {size: item_dict.get("qty", 0)}  # 尺码及数量
        })

    # 提取第一个物料的颜色和尺码作为默认的颜色图表和尺码图表
    first_item_color = ""
    first_item_size = ""
    if items_data:
        color_attr = next((attr['attribute_value'] for attr in items_data[0].get('attributes', [])
                           if attr.get('attribute') == 'XSD专属定义颜色'), '')
        size_attr = next((attr['attribute_value'] for attr in items_data[0].get('attributes', [])
                          if attr.get('attribute') == '荣冠尺码'), '')
        first_item_color = color_attr if color_attr else "XSD专属定义颜色"
        first_item_size = size_attr if size_attr else "荣冠尺码"

    # 构建生产订单数据
    order_type_mapping = {
        "Sales": "大货",  # 示例映射，可以根据实际业务需求添加更多映射
        # "Sales Sample": "销售样", # 假设销售订单的销售样类型对应生产订单的销售样
        # "Garment Sample": "样衣", # 假设销售订单的样衣类型对应生产订单的样衣
    }
    production_order_type = order_type_mapping.get(so.order_type, "大货") # 默认映射为"大货"

    production_order_data = {
        "notificationNumber": so.name,  # 通知单号（使用销售订单号）
        "customerId": so.customer,      # 客户ID
        "orderNumber": so.name,         # 订单号（使用销售订单号）
        "orderDate": so.transaction_date,  # 订单日期
        "deliveryDate": so.delivery_date,  # 交货日期
        "quantity": so.total_qty,       # 总数量
        "productName": items_data[0].get("variant_of", "") if items_data else "",  # Use variant_of as product name from items_data
        "businessType": so.business_type,  # 业务类型
        "orderStatus": "待处理",  # 初始状态
        "orderType": production_order_type,  # 订单类型，映射后的值
        "materialData": {
            "materialList": material_list,
            "selectedColorChart": {"name": first_item_color},  # Use actual attribute name
            "selectedSizeChart": {"name": first_item_size}     # Use actual attribute name
        },
        "processSteps": [],  # 可以为空
        "displayImageData": {},  # 可以为空
        "attachments": []  # 可以为空
    }
    return production_order_data

@frappe.whitelist(allow_guest=False)  # 确保只允许认证用户访问
def save_sales_order(order_data=None, *args, **kwargs):
    try:
        # 处理多种参数传递方式
        if not order_data:
            if args and isinstance(args[0], (str, dict)):
                order_data = args[0]
            elif kwargs:
                order_data = kwargs

        # 如果是字符串则尝试解析为JSON
        if isinstance(order_data, str):
            try:
                order_data = json.loads(order_data)
            except json.JSONDecodeError:
                return {
                    "error": _("Invalid JSON input")
                }

        if not isinstance(order_data, dict):
            return {
                "error": _("Invalid input format. Expected dict or JSON string")
            }

        print("Received order_data:", order_data)
        order_data["doctype"] = "Sales Order"
        print(f"Final order_data: {order_data}")

        if order_data.get("doctype") != "Sales Order":
            return {
                "error": _("Invalid doctype specified. Must be 'Sales Order'.")
            }

        if not frappe.db.exists("Customer", order_data.get("customer")):
            return {
                "error": _("客户 '{0}' 不存在").format(order_data.get("customer"))
            }

        # 检查公司字段
        if not order_data.get("company"):
            # frappe.throw("公司名称不能为空")
            return {
                "error": _("公司名称不能为空")                    
            }
        
        # 验证公司是否存在
        if not frappe.db.exists("Company", order_data["company"]):
            return {
                "error": _("公司 '{0}' 不存在").format(order_data["company"])
            }
            
        # === 增加检查，如果销售订单已存在则抛出错误 ===
        if order_data.get("name") and frappe.db.exists("Sales Order", order_data["name"]):
             return {
                 "error": _("销售订单 '{0}' 已存在").format(order_data["name"])
             }
        # ===========================================


        # 1. 批量创建商品（items）
        items = order_data.get("items", [])
        if items:
            for item in items:
                # 确保 item 也有 doctype 和 item_group
                item["doctype"] = "Item"
                item["item_group"] = item.get("item_group", "Products")  # 默认值
            try:
                print("\n=== Debug: Calling bulk_create_items ===")
                items_result = frappe.call(
                    "erpnextcn.utils.doctype.item.bulk_create_items",
                    items=items
                )
                print("\n=== Debug: bulk_create_items result ===")
                print(json.dumps(items_result, indent=2, default=str))
                if items_result.get("errors"):
                    # 如果批量创建物料失败，返回错误并回滚事务
                    frappe.db.rollback()
                    return {
                        "error": _("物料创建失败: {}").format(json.dumps(items_result["errors"], ensure_ascii=False)) # 确保中文不乱码
                    }
            except Exception as e:
                print("\n=== Debug: Exception in bulk_create_items ===")
                print(f"Error: {str(e)}")
                frappe.db.rollback() # 确保回滚
                return {"error": str(e), "code": 500}


        # 2. 创建销售订单
        try:
            print(f"order_data========================: {order_data}")

            # 在获取文档之前设置忽略命名系列标志
            if order_data.get("name"):
                 order_data["flags"] = {"ignore_naming_series": True}
                 print(f"Setting ignore_naming_series flag in order_data for name: {order_data['name']}")


            so = frappe.get_doc(order_data)

            # 原来的逻辑已经设置 so.name，保留
            if order_data.get("name"):
                 # 如果在字典中设置了flags，这里其实可以省略对so.flags的再次设置
                 # 但为了兼容性和清晰性，保留此行也无妨
                 # so.flags.ignore_naming_series = True
                 print(f"so.name========================: {so.name}")

            so.insert(ignore_permissions=True)
            
            # 提交销售订单的保存
            # frappe.db.commit() # 移除此行，将在生产订单创建后统一提交

            # 尝试构建生产订单数据并保存
            production_order_name = None
            production_order_message = _("生产制造工单创建成功")

            try:
                # Pass the processed items list to the mapping function
                production_order_data = map_sales_order_to_production_order(so, order_data.get("items", [])) # Pass so and items list
                production_order_result = save_to_rg_production_orders(production_order_data)

                if production_order_result.get("error"):
                    production_order_message = _("销售订单创建成功，但生产制造工单创建失败: {0}").format(production_order_result["error"])
                    # 如果生产订单创建失败，回滚整个事务
                    frappe.db.rollback()
                    frappe.throw(_("销售订单和生产制造工单未能全部创建成功: {0}").format(production_order_result["error"]))
                else:
                    production_order_name = production_order_result["data"]["name"]

            except Exception as e:
                production_order_message = _("销售订单创建成功，但在尝试创建生产制造工单时发生未知错误: {0}").format(str(e))
                # 如果尝试创建生产订单时发生异常，回滚整个事务
                frappe.db.rollback()
                frappe.throw(_("销售订单和生产制造工单未能全部创建成功: {0}").format(str(e)))

            # 只有当销售订单和生产制造工单都成功创建后，才提交事务
            frappe.db.commit()

            return {
                "data": {
                    "name": so.name,
                    "production_order_name": production_order_name,
                    "status": "Success",
                    "success": True,
                    "message": production_order_message
                }
            }
        except Exception as e:
            # 捕获创建销售订单阶段的错误（如 DuplicateEntryError），此时尚未提交，需要回滚
            frappe.db.rollback()
            # 重新抛出捕获到的异常
            frappe.throw(_("创建销售订单失败: {0}").format(str(e)))

    except BrokenPipeError:
        # frappe.log_error("客户端断开连接", "BrokenPipeError in save_sales_order")
        return {"error": "请求中断"}
    except Exception as e:
        # 捕获顶层未处理的异常（在任何事务操作之前）
        # frappe.log_error(frappe.get_traceback(), "General Error in save_sales_order")
        raise # 重新抛出异常

@frappe.whitelist(allow_guest=False)
def save_to_rg_production_orders(production_order_data):
    """
    保存数据到 RG Production Orders 文档
    
    参数:
        production_order_data (dict): 包含部分或全部数据的字典
    
    返回:
        dict: 保存结果
    """
    try:
        # 检查颜色和尺码属性是否存在
        material_list = production_order_data.get("materialData", {}).get("materialList", [])
        for material in material_list:
            color = material.get("color", "默认颜色")
            size = next(iter(material.get("sizes", {}).keys()), "默认尺码") if material.get("sizes") else "默认尺码"

            # 如果颜色或尺码为空，抛出异常
            if not color or not size:
                frappe.throw(_("颜色或尺码属性为空，请检查销售订单数据"))

        # 获取默认数据结构并用传入的数据更新
        full_production_order_data = get_default_production_order_data(production_order_data)

        # 调用 saveRGProductionOrder 方法保存文档
        result = saveRGProductionOrder(full_production_order_data)

        # 返回保存结果
        return {
            "data": {
                "name": result.get("name"),
                "status": "Success",
                "success": True,
                "message": _("RG Production Order created successfully")
            }
        }
    except Exception as e:
        return {
            "error": _("Failed to save RG Production Order: {0}").format(str(e))
        }

# Cursor Rule: 600-how-test-so-2-rg
# Description: Steps to test sales order to production order mapping
# 1. Ensure the sales order data includes valid items with attributes (color, size).
# 2. Call `save_sales_order`