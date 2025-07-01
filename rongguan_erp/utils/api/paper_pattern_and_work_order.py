import frappe
import json
import logging
from rongguan_erp.utils.api.work_order import _create_work_orders_without_transaction

@frappe.whitelist(methods=["POST"])
def create_paper_pattern_and_work_order(paper_pattern_data, work_order_data):
    """
    同时创建纸样（RG Paper Pattern）和生产工单（Work Order），保证原子性
    :param paper_pattern_data: dict或json字符串
    :param work_order_data: dict、list或json字符串（可以是单个工单或工单列表）
    :return: {'paper_pattern': name, 'work_orders': [names]}
    """
    # 直接使用 print() 输出
    print("原始输入参数 paper_pattern_data:", paper_pattern_data)
    print("原始输入参数 work_order_data:", work_order_data)
    print("参数类型 paper_pattern_data type:", type(paper_pattern_data))
    print("参数类型 work_order_data type:", type(work_order_data))

    if isinstance(paper_pattern_data, str):
        paper_pattern_data = json.loads(paper_pattern_data)
    if isinstance(work_order_data, str):
        work_order_data = json.loads(work_order_data)

    save_point = "create_paper_pattern_and_work_order"
    try:
        frappe.db.savepoint(save_point)
        
        # 再次打印处理后的参数
        print("处理后的 paper_pattern_data:", paper_pattern_data)
        print("处理后的 work_order_data:", work_order_data)

        paper_pattern_doc = frappe.get_doc({"doctype": "RG Paper Pattern", **paper_pattern_data})
        paper_pattern_doc.insert()

        # 确保 work_order_data 是列表格式
        if isinstance(work_order_data, dict):
            # 如果是单个工单字典，包装成列表
            work_orders_data = [work_order_data]
        elif isinstance(work_order_data, list):
            # 如果已经是列表，直接使用
            work_orders_data = work_order_data
        else:
            raise Exception(f"不支持的工单数据类型: {type(work_order_data)}")

        # 使用不管理事务的内部函数创建工单
        batch_result = _create_work_orders_without_transaction(work_orders_data)
        if batch_result.get('status') != 'success' or not batch_result.get('created_work_orders'):
            raise Exception(f"工单创建失败: {batch_result.get('message')}")
        
        # 获取所有创建的工单名称
        work_order_names = [wo['work_order_name'] for wo in batch_result['created_work_orders']]

        frappe.db.release_savepoint(save_point)
    except Exception as e:
        frappe.db.rollback(save_point=save_point)
        # 打印异常信息
        print("异常详情:", str(e))
        raise

    return {
        "paper_pattern": paper_pattern_doc.name,
        "work_orders": work_order_names,
        "total_work_orders": len(work_order_names)
    }
