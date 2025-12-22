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

        # 查询物料请求（采购计划）（通过 custom_sales_order_number 关联）
        material_request = None
        material_request_docs = frappe.get_all(
            "Material Request",
            filters={"custom_sales_order_number": sales_order_number},
            fields=["name", "status", "docstatus", "per_ordered"],
            order_by="creation desc",
            limit=1,
        )

        if material_request_docs:
            mr = material_request_docs[0]
            
            # 根据业务逻辑确定状态：如果已生成采购订单（per_ordered > 0），状态为"已下单"，否则为"待采购"
            if mr.docstatus == 1 and mr.per_ordered > 0:
                order_status = "已下单"
            elif mr.docstatus == 1 and mr.per_ordered == 0:
                order_status = "待采购"
            else:
                order_status = mr.status or "未知"
            
            material_request = {
                "document_number": mr.name,
                "order_status": order_status,
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
        
        # 添加物料请求（采购计划）信息
        if material_request:
            result["data"]["material_request"] = material_request
        
        # 查询采购订单（通过物料请求关联）
        purchase_order = None
        purchase_order_name = None
        if material_request_docs:
            # 查询与物料请求关联的采购订单
            purchase_order_list = frappe.db.sql("""
                SELECT DISTINCT po.name, po.status, po.docstatus
                FROM `tabPurchase Order` po
                INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
                WHERE poi.material_request = %s
                ORDER BY po.creation DESC
                LIMIT 1
            """, (material_request_docs[0].name,), as_dict=True)
            
            if purchase_order_list:
                po = purchase_order_list[0]
                purchase_order_name = po.name
                purchase_order_approval = _get_dty_approval_info(
                    "Purchase Order", po.name
                )
                purchase_order = {
                    "document_number": po.name,
                    "order_status": po.status or "未知",
                    "approval_no": purchase_order_approval.get("approval_no"),
                    "approval_status": purchase_order_approval.get("approval_status"),
                }
        
        # 添加采购订单信息
        if purchase_order:
            result["data"]["purchase_order"] = purchase_order
        
        # 查询采购接收（通过采购订单关联）
        purchase_receipt = None
        if purchase_order_name:
            # 查询与采购订单关联的采购接收
            purchase_receipt_list = frappe.db.sql("""
                SELECT DISTINCT pr.name, pr.status, pr.docstatus
                FROM `tabPurchase Receipt` pr
                INNER JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
                WHERE pri.purchase_order = %s
                ORDER BY pr.creation DESC
                LIMIT 1
            """, (purchase_order_name,), as_dict=True)
            
            if purchase_receipt_list:
                pr = purchase_receipt_list[0]
                purchase_receipt = {
                    "document_number": pr.name,
                    "order_status": pr.status or "未知",
                }
        
        # 添加采购接收信息
        if purchase_receipt:
            result["data"]["purchase_receipt"] = purchase_receipt
        
        # 查询生产工单（通过 sales_order 直接关联）
        work_order = None
        work_order_docs = frappe.get_all(
            "Work Order",
            filters={"sales_order": sales_order_number},
            fields=["name", "status", "docstatus"],
            order_by="creation desc",
            limit=1,
        )
        
        if work_order_docs:
            wo = work_order_docs[0]
            work_order = {
                "document_number": wo.name,
                "order_status": wo.status or "未知",
            }
        
        # 添加生产工单信息
        if work_order:
            result["data"]["work_order"] = work_order
        
        # 查询产前会议确认状态（通过 RG Production Progress 的封样日期判断）
        pre_production_meeting = None
        production_progress_docs = frappe.get_all(
            "RG Production Progress",
            filters={"sales_order_id": sales_order_number},
            fields=["name", "sealing_sample_date"],
        )
        
        if production_progress_docs:
            # 检查是否有任何一条记录的封样日期不为空
            has_sealing_date = any(
                doc.get("sealing_sample_date") for doc in production_progress_docs
            )
            
            pre_production_meeting = {
                "document_number": sales_order_number,
                "order_status": "已确认" if has_sealing_date else "待确认",
            }
        else:
            # 如果没有生产进度记录，默认为待确认
            pre_production_meeting = {
                "document_number": sales_order_number,
                "order_status": "待确认",
            }
        
        # 添加产前会议确认信息
        if pre_production_meeting:
            result["data"]["pre_production_meeting"] = pre_production_meeting
        
        # 查询裁剪报工状态（通过 RG Cutting Work Report 判断）
        cutting_work = None
        cutting_work_docs = frappe.get_all(
            "RG Cutting Work Report",
            filters={"sales_order": sales_order_number},
            fields=["name"],
            limit=1,
        )
        
        if cutting_work_docs:
            # 如果找到至少一条记录，表示裁剪已开始
            cutting_work = {
                "document_number": sales_order_number,
                "order_status": "已开始",
            }
        else:
            # 如果找不到任何记录，表示裁剪未开始
            cutting_work = {
                "document_number": sales_order_number,
                "order_status": "未开始",
            }
        
        # 添加裁剪报工信息
        if cutting_work:
            result["data"]["cutting_work"] = cutting_work
        
        # 查询领料状态（通过 Stock Entry 类型为 "Send to Subcontractor" 判断）
        material_issue = None
        # 查询方式1：通过 custom_sales_order_number 字段
        stock_entry_docs1 = frappe.get_all(
            "Stock Entry",
            filters={
                "stock_entry_type": "Send to Subcontractor",
                "custom_sales_order_number": sales_order_number
            },
            fields=["name"],
            limit=1,
        )
        
        # 查询方式2：通过 work_order -> Work Order.sales_order 关联
        stock_entry_docs2 = frappe.db.sql("""
            SELECT DISTINCT ste.name
            FROM `tabStock Entry` ste
            INNER JOIN `tabWork Order` wo ON wo.name = ste.work_order
            WHERE ste.stock_entry_type = 'Send to Subcontractor'
            AND wo.sales_order = %s
            LIMIT 1
        """, (sales_order_number,), as_dict=True)
        
        # 如果找到至少一条记录，表示已领料
        if stock_entry_docs1 or stock_entry_docs2:
            material_issue = {
                "document_number": sales_order_number,
                "order_status": "已领料",
            }
        else:
            # 如果找不到任何记录，表示未领料
            material_issue = {
                "document_number": sales_order_number,
                "order_status": "未领料",
            }
        
        # 添加领料信息
        if material_issue:
            result["data"]["material_issue"] = material_issue
        
        # 查询生产报工状态（通过 RG Production Report 判断）
        production_report = None
        production_report_docs = frappe.get_all(
            "RG Production Report",
            filters={"sales_order": sales_order_number},
            fields=["name"],
            limit=1,
        )
        
        if production_report_docs:
            # 如果找到至少一条记录，表示生产中
            production_report = {
                "document_number": sales_order_number,
                "order_status": "生产中",
            }
        else:
            # 如果找不到任何记录，表示未生产
            production_report = {
                "document_number": sales_order_number,
                "order_status": "未生产",
            }
        
        # 添加生产报工信息
        if production_report:
            result["data"]["production_report"] = production_report
        
        # 查询QC巡查状态（通过 QC Patrol Record 判断）
        qc_patrol = None
        qc_patrol_docs = frappe.get_all(
            "QC Patrol Record",
            filters={"order_number": sales_order_number},
            fields=["name"],
            limit=1,
        )
        
        if qc_patrol_docs:
            # 如果找到至少一条记录，表示QC巡查已完成
            qc_patrol = {
                "document_number": sales_order_number,
                "order_status": "已完成",
            }
        else:
            # 如果找不到任何记录，表示QC巡查待处理
            qc_patrol = {
                "document_number": sales_order_number,
                "order_status": "待处理",
            }
        
        # 添加QC巡查信息
        if qc_patrol:
            result["data"]["qc_patrol"] = qc_patrol
        
        return result
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"获取销售订单跟踪信息失败")
        return {"success": False, "error": _("获取销售订单跟踪信息失败: {0}").format(str(e))}
