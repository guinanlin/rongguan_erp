# -*- coding: utf-8 -*-
"""
销售订单跟踪 API
用于快速获取销售订单的关键状态信息，便于前端跟进订单进度
"""
import frappe
from frappe import _


# 测试方式：
# 1. bench console: frappe.call('rongguan_erp.utils.api.sales_order_tracking.get_sales_order_tracking', sales_order_number='SAL-ORD-2025-00001')
# 2. bench execute: bench execute rongguan_erp.utils.api.sales_order_tracking.get_sales_order_tracking --args '["SAL-ORD-2025-00001"]'
@frappe.whitelist(allow_guest=False)
def get_sales_order_tracking(*args, **kwargs):
    """
    根据销售订单号获取订单的跟踪信息
    """
    try:
        # 获取参数
        sales_order_number = kwargs.get('sales_order_number') or kwargs.get('name')
        if not sales_order_number and args:
            if isinstance(args[0], (str, list)):
                sales_order_number = args[0] if isinstance(args[0], str) else args[0][0]
            elif isinstance(args[0], dict):
                sales_order_number = args[0].get('sales_order_number') or args[0].get('name')
        
        if not sales_order_number:
            return {"success": False, "error": _("销售订单号不能为空")}
        
        if not frappe.db.exists("Sales Order", sales_order_number):
            return {"success": False, "error": _("销售订单 '{0}' 不存在").format(sales_order_number)}
        
        # 获取订单信息
        sales_order = frappe.get_doc("Sales Order", sales_order_number)
        
        # 订单状态映射
        status_map = {0: "草稿", 1: "已提交", 2: "已取消"}
        
        # 查询生产制造通知单（通过 order_number 关联）
        production_order = None
        production_order_docs = frappe.get_all(
            "RG Production Orders",
            filters={"order_number": sales_order_number},
            fields=["name", "status"],
            limit=1
        )
        
        if production_order_docs:
            production_order = {
                "document_number": production_order_docs[0].name,
                "order_status": production_order_docs[0].status or "未知",
                "approval_no": None,
                "approval_status": None
            }
        
        result = {
            "success": True,
            "data": {
                "sales_order": {
                    "document_number": sales_order.name,
                    "order_status": status_map.get(sales_order.docstatus, "未知"),
                    "approval_no": getattr(sales_order, "custom_approval_no", None),
                    "approval_status": None
                }
            }
        }
        
        # 添加生产制造通知单信息
        if production_order:
            result["data"]["production_order"] = production_order
        
        return result
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"获取销售订单跟踪信息失败")
        return {"success": False, "error": _("获取销售订单跟踪信息失败: {0}").format(str(e))}
