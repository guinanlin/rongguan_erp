import frappe
import json
import logging

@frappe.whitelist(methods=["POST"])
def create_paper_pattern_and_work_order(paper_pattern_data, work_order_data):
    """
    同时创建纸样（RG Paper Pattern）和生产工单（Work Order），保证原子性
    :param paper_pattern_data: dict或json字符串
    :param work_order_data: dict或json字符串
    :return: {'paper_pattern': name, 'work_order': name}
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
        work_order_doc = frappe.get_doc({"doctype": "Work Order", **work_order_data})
        work_order_doc.insert()
        frappe.db.release_savepoint(save_point)
    except Exception as e:
        frappe.db.rollback(save_point=save_point)
        # 打印异常信息
        print("异常详情:", str(e))
        raise

    return {
        "paper_pattern": paper_pattern_doc.name,
        "work_order": work_order_doc.name
    }
