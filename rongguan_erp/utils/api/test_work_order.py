import frappe
from rongguan_erp.utils.api.work_order import batch_assign_work_orders


@frappe.whitelist()
def test_batch_assign_specific_work_order():
    """
    测试对特定工单 MFG-WO-2025-00117 进行批量分配
    分配给用户 4@4.com
    """
    # 测试数据 - 使用员工ID
    test_assignments = [
        {
            "work_order_name": "MFG-WO-2025-00117",
            "assign_to": "HR-EMP-00001",  # 员工ID
            "description": "测试批量分配功能 - 使用员工ID分配",
            "priority": "High"
        }
    ]
    
    # 执行批量分配
    result = batch_assign_work_orders(assignments_data=test_assignments)
    
    return {
        'test_info': {
            'work_order_name': 'MFG-WO-2025-00117',
            'assign_to': 'HR-EMP-00001',  # 员工ID
            'test_description': '测试batch_assign_work_orders方法 - 使用员工ID'
        },
        'result': result
    }
