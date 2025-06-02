# Server Script: save_sales_order
# Whitelisted for API access
import frappe
from frappe import _
import json

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

        # 1. 批量创建商品（items）
        items = order_data.get("items", [])
        if items:
            for item in items:
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
                    return {
                        "error": _("物料创建失败:{}").format(items_result["errors"])                    
                    }
            except Exception as e:
                print("\n=== Debug: Exception in bulk_create_items ===")
                print(f"Error: {str(e)}")
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
            frappe.db.commit()
            print("订单数据:", order_data)
            print("插入数据库结果:", so)
            return {
                "data": {
                    "name": so.name,
                    "status": "Success",
                    "success": True,
                    "message": _("Sales Order created successfully")
                }
            }
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback(), "Sales Order Creation Failed")
            frappe.throw(_("Failed to create Sales Order: {0}").format(str(e)))
    except BrokenPipeError:
        frappe.log_error("客户端断开连接", "BrokenPipeError in save_sales_order")
        return {"error": "请求中断"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sales Order Creation Failed")
        raise
