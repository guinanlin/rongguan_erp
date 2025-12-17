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
        def _get_dty_approval_info(ref_doctype: str, ref_document: str):
            """根据引用单据查询 DTY Approval（审批单号与状态）。"""
            if not ref_doctype or not ref_document:
                return {"approval_no": None, "approval_status": None}

            approval_docs = frappe.get_all(
                "DTY Approval",
                filters={"ref_doctype": ref_doctype, "ref_document": ref_document},
                fields=["sp_no", "sp_status"],
                order_by="modified desc",
                limit=1,
            )

            if not approval_docs:
                return {"approval_no": None, "approval_status": None}

            return {
                "approval_no": approval_docs[0].sp_no,
                "approval_status": approval_docs[0].sp_status,
            }

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
            production_order_approval = _get_dty_approval_info(
                "RG Production Orders", production_order_docs[0].name
            )
            production_order = {
                "document_number": production_order_docs[0].name,
                "order_status": production_order_docs[0].status or "未知",
                "approval_no": production_order_approval.get("approval_no"),
                "approval_status": production_order_approval.get("approval_status"),
            }
        
        # 查询纸样单（通过 sales_order 关联）
        paper_pattern = None
        paper_pattern_docs = frappe.get_all(
            "RG Paper Pattern",
            filters={"sales_order": sales_order_number},
            fields=["name", "docstatus"],
            limit=1,
        )

        if paper_pattern_docs:
            paper_pattern_approval = _get_dty_approval_info(
                "RG Paper Pattern", paper_pattern_docs[0].name
            )
            paper_pattern = {
                "document_number": paper_pattern_docs[0].name,
                "order_status": status_map.get(paper_pattern_docs[0].docstatus, "未知"),
                "approval_no": paper_pattern_approval.get("approval_no"),
                "approval_status": paper_pattern_approval.get("approval_status"),
            }

        result = {
            "success": True,
            "data": {
                "sales_order": {
                    "document_number": sales_order.name,
                    "order_status": status_map.get(sales_order.docstatus, "未知"),
                    "approval_no": _get_dty_approval_info("Sales Order", sales_order.name).get("approval_no")
                    or getattr(sales_order, "custom_approval_no", None),
                    "approval_status": _get_dty_approval_info("Sales Order", sales_order.name).get("approval_status"),
                }
            }
        }
        
        # 添加生产制造通知单信息
        if production_order:
            result["data"]["production_order"] = production_order

        # 添加纸样单信息
        if paper_pattern:
            result["data"]["paper_pattern"] = paper_pattern
        
        return result
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"获取销售订单跟踪信息失败")
        return {"success": False, "error": _("获取销售订单跟踪信息失败: {0}").format(str(e))}
