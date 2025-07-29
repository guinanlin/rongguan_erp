# -*- coding: utf-8 -*-
"""
物料申请单取消和删除
"""

import frappe


@frappe.whitelist()
def cancel_and_delete_material_request(**args):
    """
    取消并删除物料申请单
    """
    try:
        material_request_name = args.get('material_request_name')
        
        # 检查物料申请单是否存在
        if not frappe.db.exists("Material Request", material_request_name):
            return {"success": False, "message": f"物料申请单 {material_request_name} 不存在"}
        
        # 获取物料申请单
        material_request = frappe.get_doc("Material Request", material_request_name)
        
        # 检查状态必须是Pending
        if material_request.status != "Pending":
            return {"success": False, "message": f"物料申请单 {material_request_name} 状态不是Pending，当前状态: {material_request.status}"}
        
        # 保存销售订单号，用于后续更新生产制造通知单
        sales_order_number = material_request.get('custom_sales_order_number')
        
        # 先取消
        if material_request.docstatus == 1:
            material_request.cancel()
            frappe.db.commit()
        
        # 再删除
        frappe.delete_doc("Material Request", material_request_name, force=True)
        frappe.db.commit()
        
        # 根据销售订单号查找并更新生产制造通知单状态
        if sales_order_number:
            production_orders = frappe.get_all("RG Production Orders", 
                filters={"order_number": sales_order_number},
                fields=["name", "status"])
            
            updated_orders = []
            for order in production_orders:
                if order.status != "待处理":
                    # 更新生产制造通知单状态为"待处理"
                    frappe.db.set_value("RG Production Orders", order.name, "status", "待处理")
                    updated_orders.append(order.name)
            
            frappe.db.commit()
            
            if updated_orders:
                return {
                    "success": True, 
                    "message": f"物料申请单 {material_request_name} 已成功取消并删除，同时更新了 {len(updated_orders)} 个生产制造通知单状态为待处理",
                    "updated_production_orders": updated_orders
                }
            else:
                return {
                    "success": True, 
                    "message": f"物料申请单 {material_request_name} 已成功取消并删除，未找到需要更新的生产制造通知单"
                }
        else:
            return {"success": True, "message": f"物料申请单 {material_request_name} 已成功取消并删除"}
        
    except Exception as e:
        return {"success": False, "message": f"操作失败: {str(e)}"} 