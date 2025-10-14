import frappe
from frappe import _
from frappe.utils import nowdate, get_datetime, flt
import json
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry


def convert_employee_to_user_id(employee_input):
    """
    将员工ID或员工ID列表转换为用户ID
    
    Args:
        employee_input: 员工ID（字符串）、员工ID列表，或已经是用户ID
        
    Returns:
        list: 用户ID列表
    """
    if not employee_input:
        return []
    
    # 处理输入格式
    if isinstance(employee_input, str):
        try:
            # 尝试解析JSON字符串
            employee_list = json.loads(employee_input)
            if not isinstance(employee_list, list):
                employee_list = [employee_input]
        except (json.JSONDecodeError, TypeError):
            # 如果不是JSON，则作为单个员工ID处理
            employee_list = [employee_input]
    elif isinstance(employee_input, list):
        employee_list = employee_input
    else:
        employee_list = [str(employee_input)]
    
    user_ids = []
    
    for emp_id in employee_list:
        emp_id = str(emp_id).strip()
        if not emp_id:
            continue
            
        # 首先检查是否已经是用户ID（邮箱格式）
        if '@' in emp_id and frappe.db.exists('User', emp_id):
            user_ids.append(emp_id)
            continue
        
        # 检查是否是员工ID，获取对应的用户ID
        user_id = frappe.db.get_value('Employee', emp_id, 'user_id')
        if user_id:
            user_ids.append(user_id)
        else:
            # 如果找不到对应的用户ID，记录错误但继续处理其他员工
            frappe.log_error(f"员工 {emp_id} 没有关联的用户ID", "Employee to User ID Conversion")
    
    return user_ids


def _create_work_orders_without_transaction(work_orders_data):
    """
    批量创建工单但不管理事务的内部函数
    
    Args:
        work_orders_data: 工单数据列表
        
    Returns:
        dict: 包含操作结果的字典
    """
    if isinstance(work_orders_data, str):
        work_orders_data = json.loads(work_orders_data)
    
    if not isinstance(work_orders_data, list):
        return {
            'status': 'error',
            'message': '输入数据必须是工单数据列表'
        }
    
    if not work_orders_data:
        return {
            'status': 'error',
            'message': '工单数据列表不能为空'
        }
    
    # 验证所有工单数据的必需字段
    required_fields = ['production_item', 'qty', 'company', 'bom_no']
    validation_errors = []
    
    for i, work_order_data in enumerate(work_orders_data):
        for field in required_fields:
            if not work_order_data.get(field):
                validation_errors.append(f'第{i+1}个工单缺少必需字段: {field}')
        
        # 验证分配员工/用户是否存在（如果有分配）
        assign_to = work_order_data.get('assign_to')
        if assign_to:
            try:
                # 转换员工ID为用户ID
                user_ids = convert_employee_to_user_id(assign_to)
                if not user_ids:
                    validation_errors.append(f'第{i+1}个工单的分配对象无效或找不到对应用户: {assign_to}')
                else:
                    # 验证用户是否存在
                    for user_id in user_ids:
                        if not frappe.db.exists('User', user_id):
                            validation_errors.append(f'第{i+1}个工单的用户 {user_id} 不存在')
            except Exception as e:
                validation_errors.append(f'第{i+1}个工单分配对象转换失败: {str(e)}')
    
    if validation_errors:
        return {
            'status': 'error',
            'message': '数据验证失败',
            'errors': validation_errors
        }
    
    # 批量创建工单（不管理事务）
    created_work_orders = []
    assignment_results = []
    
    for i, work_order_data in enumerate(work_orders_data):
        # 创建工单文档
        work_order = frappe.new_doc('Work Order')
        
        # 设置基本字段
        work_order.production_item = work_order_data.get('production_item')
        work_order.qty = work_order_data.get('qty')
        work_order.company = work_order_data.get('company')
        work_order.bom_no = work_order_data.get('bom_no')
        work_order.stock_uom = work_order_data.get('stock_uom', 'Nos')
        
        # 设置可选字段
        optional_fields = [
            'naming_series', 'description', 'item_name', 'expected_delivery_date',
            'planned_start_date', 'fg_warehouse', 'wip_warehouse', 'transfer_material_against',
            'use_multi_level_bom', 'update_consumed_material_cost_in_project', 'sales_order'
        ]
        
        for field in optional_fields:
            if work_order_data.get(field):
                setattr(work_order, field, work_order_data.get(field))
        
        # 设置自定义字段
        custom_fields = [
            'custom_work_oder_type', 'custom_style_name', 'custom_style_code'
        ]
        
        for field in custom_fields:
            if work_order_data.get(field):
                setattr(work_order, field, work_order_data.get(field))
        
        # 设置所需物料
        if work_order_data.get('required_items'):
            for item in work_order_data.get('required_items'):
                work_order.append('required_items', {
                    'item_code': item.get('item_code'),
                    'item_name': item.get('item_name'),
                    'description': item.get('description'),
                    'required_qty': item.get('required_qty'),
                    'stock_uom': item.get('stock_uom'),
                    'rate': item.get('rate'),
                    'amount': item.get('amount'),
                    'source_warehouse': item.get('source_warehouse'),
                    'allow_alternative_item': item.get('allow_alternative_item', 0),
                    'include_item_in_manufacturing': item.get('include_item_in_manufacturing', 1)
                })
        
        # 设置操作工序
        if work_order_data.get('operations'):
            try:
                operations_list = work_order_data.get('operations')
                if isinstance(operations_list, list) and operations_list:
                    for operation in operations_list:
                        if isinstance(operation, dict) and operation.get('operation'):
                            work_order.append('operations', {
                                'operation': operation.get('operation'),
                                'status': operation.get('status', 'Pending'),
                                'time_in_mins': operation.get('time_in_mins', 0),
                                'planned_operating_cost': operation.get('planned_operating_cost', 0),
                                'sequence_id': operation.get('sequence_id', 1),
                                'hour_rate': operation.get('hour_rate', 0),
                                'batch_size': operation.get('batch_size', 0),
                                'completed_qty': operation.get('completed_qty', 0),
                                'process_loss_qty': operation.get('process_loss_qty', 0),
                                'actual_operation_time': operation.get('actual_operation_time', 0),
                                'actual_operating_cost': operation.get('actual_operating_cost', 0)
                            })
                        else:
                            # 记录无效的operation数据，但不影响工单创建
                            frappe.log_error(f"工单 {work_order.name} 的operation数据无效: {operation}", "Work Order Operations Error")
            except Exception as operations_error:
                # 如果operations处理出错，记录错误但不影响工单创建
                frappe.log_error(f"工单 {work_order.name} 处理operations时出错: {str(operations_error)}", "Work Order Operations Error")
        
        # 保存工单
        work_order.insert()
        
        created_work_order = {
            'index': i + 1,
            'work_order_name': work_order.name,
            'production_item': work_order.production_item,
            'qty': work_order.qty
        }
        
        # 处理工单分配（如果有）
        assign_to = work_order_data.get('assign_to')
        if assign_to:
            try:
                # 转换员工ID为用户ID
                user_ids = convert_employee_to_user_id(assign_to)
                
                if user_ids:
                    # 设置分配描述
                    assignment_description = work_order_data.get('assignment_description', 
                                                               f'工单 {work_order.name} 已分配给您')
                    
                    # 使用Frappe的标准分配功能
                    from frappe.desk.form import assign_to as frappe_assign_to
                    
                    assignment_args = {
                        'assign_to': user_ids,
                        'doctype': 'Work Order',
                        'name': work_order.name,
                        'description': assignment_description,
                        'priority': work_order_data.get('assignment_priority', 'Medium')
                    }
                    
                    if work_order_data.get('assignment_date'):
                        assignment_args['date'] = work_order_data.get('assignment_date')
                    
                    # 执行分配
                    assignment_result = frappe_assign_to.add(assignment_args)
                    
                    assignment_results.append({
                        'work_order_name': work_order.name,
                        'original_assign_to': assign_to,
                        'converted_user_ids': user_ids,
                        'assignment_status': 'success'
                    })
                    
                    created_work_order['original_assign_to'] = assign_to
                    created_work_order['assigned_user_ids'] = user_ids
                    created_work_order['assignment_status'] = 'success'
                else:
                    # 转换失败
                    assignment_results.append({
                        'work_order_name': work_order.name,
                        'original_assign_to': assign_to,
                        'assignment_status': 'failed',
                        'assignment_error': '无法转换员工ID为用户ID'
                    })
                    
                    created_work_order['original_assign_to'] = assign_to
                    created_work_order['assignment_status'] = 'failed'
                    created_work_order['assignment_error'] = '无法转换员工ID为用户ID'
                
            except Exception as assignment_error:
                # 分配失败但不影响工单创建
                assignment_results.append({
                    'work_order_name': work_order.name,
                    'original_assign_to': assign_to,
                    'assignment_status': 'failed',
                    'assignment_error': str(assignment_error)
                })
                
                created_work_order['original_assign_to'] = assign_to
                created_work_order['assignment_status'] = 'failed'
                created_work_order['assignment_error'] = str(assignment_error)
        
        created_work_orders.append(created_work_order)
    
    # 统计分配结果
    successful_assignments = [r for r in assignment_results if r.get('assignment_status') == 'success']
    failed_assignments = [r for r in assignment_results if r.get('assignment_status') == 'failed']
    
    result = {
        'status': 'success',
        'message': f'成功批量创建{len(created_work_orders)}个工单',
        'total_count': len(created_work_orders),
        'created_work_orders': created_work_orders
    }
    
    if assignment_results:
        result['assignment_summary'] = {
            'total_assignments': len(assignment_results),
            'successful_assignments': len(successful_assignments),
            'failed_assignments': len(failed_assignments)
        }
        
        if successful_assignments:
            result['successful_assignments'] = successful_assignments
        
        if failed_assignments:
            result['failed_assignments'] = failed_assignments
    
    return result


@frappe.whitelist()
def batch_save_work_orders(work_orders_data):
    """
    批量保存生产工单的白名单API方法（事务处理）
    支持在保存工单的同时分配给员工，并支持操作工序
    
    Args:
        work_orders_data: 工单数据列表，每个元素都是一个工单数据字典
        可以包含以下字段：
        - 基本字段: production_item, qty, company, bom_no, stock_uom
        - 可选字段: naming_series, description, item_name, expected_delivery_date, 
                   planned_start_date, fg_warehouse, wip_warehouse, transfer_material_against,
                   use_multi_level_bom, update_consumed_material_cost_in_project, sales_order
        - 自定义字段: custom_work_oder_type, custom_style_name, custom_style_code
        - 分配相关字段:
          - assign_to: 分配给的员工ID或用户ID（字符串或列表）
          - assignment_description: 分配描述
          - assignment_priority: 分配优先级 (Low, Medium, High)
          - assignment_date: 分配完成日期
        - 子表字段:
          - required_items: 所需物料列表
          - operations: 操作工序列表，每个工序包含以下字段：
            - operation: 工序名称
            - status: 状态 (Pending, Work In Progress, Completed)
            - time_in_mins: 计划时间（分钟）
            - planned_operating_cost: 计划操作成本
            - sequence_id: 序列ID
            - hour_rate: 小时费率
            - batch_size: 批次大小
            - completed_qty: 完成数量
            - process_loss_qty: 工艺损耗数量
            - actual_operation_time: 实际操作时间
            - actual_operating_cost: 实际操作成本
        
    Returns:
        dict: 包含操作结果的字典
    """
    try:
        # 开始数据库事务
        frappe.db.begin()
        
        # 调用不管理事务的内部函数
        result = _create_work_orders_without_transaction(work_orders_data)
        
        if result.get('status') == 'success':
            # 提交事务
            frappe.db.commit()
            return result
        else:
            # 回滚事务
            frappe.db.rollback()
            return result
            
    except Exception as e:
        # 回滚事务
        frappe.db.rollback()
        frappe.log_error(f"批量保存工单时出错: {str(e)}", "Batch Work Order Save Error")
        return {
            'status': 'error',
            'message': f'批量保存工单时出错: {str(e)}',
            'created_count': 0
        }


@frappe.whitelist()
def test_batch_save_work_orders():
    """
    测试批量保存工单的函数（包含分配功能和operations）
    """
    # 获取一个测试用的员工ID
    test_employee = frappe.db.get_value('Employee', {'status': 'Active'}, ['name', 'user_id'], as_dict=True)
    
    if not test_employee or not test_employee.user_id:
        # 如果没有找到有用户ID的员工，使用当前用户
        assign_to_value = frappe.session.user
    else:
        # 使用员工ID进行测试
        assign_to_value = test_employee.name
    
    test_data = [
        {
            'bom_no': 'BOM-FG000354-012',
            'company': 'DTY',
            'custom_work_oder_type': '纸样工单',
            'description': 'SM-0023 - 纸样制作 (批量测试1)',
            'expected_delivery_date': '2025-06-17',
            'fg_warehouse': '在制品 - D',
            'item_name': 'SM-0023 - 纸样',
            'naming_series': 'MFG-WO-.YYYY.-',
            'planned_start_date': '2025-06-10 10:00:00',
            'production_item': 'FG000354',
            'qty': 3,
            'stock_uom': 'Nos',
            'transfer_material_against': 'Work Order',
            'use_multi_level_bom': 1,
            'wip_warehouse': '在制品 - D',
            'custom_style_name': 'SM-0023',
            'custom_style_code': 'STYLE-0023',
            # 分配相关字段 - 使用员工ID
            'assign_to': assign_to_value,
            'assignment_description': '批量测试工单1 - 请及时处理（使用员工ID）',
            'assignment_priority': 'High',
            # 操作工序
            'operations': [
                {
                    'operation': '裁剪',
                    'status': 'Pending',
                    'time_in_mins': 100,
                    'planned_operating_cost': 0,
                    'sequence_id': 1,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                },
                {
                    'operation': '缝制',
                    'status': 'Pending',
                    'time_in_mins': 150,
                    'planned_operating_cost': 0,
                    'sequence_id': 2,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                }
            ]
        },
        {
            'bom_no': 'BOM-FG000354-012',
            'company': 'DTY',
            'custom_work_oder_type': '纸样工单',
            'description': 'SM-0024 - 纸样制作 (批量测试2)',
            'expected_delivery_date': '2025-06-18',
            'fg_warehouse': '在制品 - D',
            'item_name': 'SM-0024 - 纸样',
            'naming_series': 'MFG-WO-.YYYY.-',
            'planned_start_date': '2025-06-11 10:00:00',
            'production_item': 'FG000354',
            'qty': 5,
            'stock_uom': 'Nos',
            'transfer_material_against': 'Work Order',
            'use_multi_level_bom': 1,
            'wip_warehouse': '在制品 - D',
            'custom_style_name': 'SM-0024',
            'custom_style_code': 'STYLE-0024',
            # 分配相关字段 - 使用员工ID
            'assign_to': assign_to_value,
            'assignment_description': '批量测试工单2 - 中等优先级（使用员工ID）',
            'assignment_priority': 'Medium',
            # 操作工序
            'operations': [
                {
                    'operation': '裁剪',
                    'status': 'Pending',
                    'time_in_mins': 120,
                    'planned_operating_cost': 0,
                    'sequence_id': 1,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                },
                {
                    'operation': '缝制',
                    'status': 'Pending',
                    'time_in_mins': 180,
                    'planned_operating_cost': 0,
                    'sequence_id': 2,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                },
                {
                    'operation': '后道',
                    'status': 'Pending',
                    'time_in_mins': 60,
                    'planned_operating_cost': 0,
                    'sequence_id': 3,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                }
            ]
        },
        {
            'bom_no': 'BOM-FG000354-012',
            'company': 'DTY',
            'custom_work_oder_type': '纸样工单',
            'description': 'SM-0025 - 纸样制作 (批量测试3)',
            'expected_delivery_date': '2025-06-19',
            'fg_warehouse': '在制品 - D',
            'item_name': 'SM-0025 - 纸样',
            'naming_series': 'MFG-WO-.YYYY.-',
            'planned_start_date': '2025-06-12 10:00:00',
            'production_item': 'FG000354',
            'qty': 2,
            'stock_uom': 'Nos',
            'transfer_material_against': 'Work Order',
            'use_multi_level_bom': 1,
            'wip_warehouse': '在制品 - D',
            'custom_style_name': 'SM-0025',
            'custom_style_code': 'STYLE-0025'
            # 这个工单没有分配信息和操作工序，测试混合场景
        }
    ]
    
    result = batch_save_work_orders(test_data)
    
    # 添加测试信息
    result['test_info'] = {
        'test_employee': test_employee,
        'assign_to_value': assign_to_value,
        'message': '测试使用员工ID进行分配，包含operations字段'
    }
    
    return result


@frappe.whitelist()
def test_employee_to_user_conversion():
    """
    测试员工ID到用户ID转换功能的函数
    """
    try:
        # 获取一些测试数据
        employees = frappe.db.get_all('Employee', 
                                    filters={'status': 'Active'}, 
                                    fields=['name', 'employee_name', 'user_id'], 
                                    limit=3)
        
        test_results = []
        
        for emp in employees:
            # 测试员工ID转换
            converted_users = convert_employee_to_user_id(emp.name)
            
            test_results.append({
                'employee_id': emp.name,
                'employee_name': emp.employee_name,
                'expected_user_id': emp.user_id,
                'converted_user_ids': converted_users,
                'conversion_success': emp.user_id in converted_users if emp.user_id else len(converted_users) == 0
            })
        
        # 测试用户ID直接输入（不需要转换）
        test_user = frappe.session.user
        converted_direct = convert_employee_to_user_id(test_user)
        
        test_results.append({
            'input': test_user,
            'type': 'direct_user_id',
            'converted_user_ids': converted_direct,
            'conversion_success': test_user in converted_direct
        })
        
        # 测试列表输入
        if employees:
            emp_list = [emp.name for emp in employees[:2]]
            converted_list = convert_employee_to_user_id(emp_list)
            
            test_results.append({
                'input': emp_list,
                'type': 'employee_list',
                'converted_user_ids': converted_list,
                'conversion_success': len(converted_list) > 0
            })
        
        return {
            'status': 'success',
            'message': '员工ID到用户ID转换测试完成',
            'test_results': test_results,
            'total_employees_tested': len(employees)
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'测试转换功能时出错: {str(e)}'
        }


@frappe.whitelist()
def save_work_order(**kwargs):
    """
    保存生产工单的白名单API方法（支持操作工序）
    
    Args:
        **kwargs: 工单数据，支持直接传递参数或work_order_data字典
        支持所有batch_save_work_orders中的字段，包括：
        - 基本字段: production_item, qty, company, bom_no, stock_uom
        - 可选字段: naming_series, description, item_name, expected_delivery_date, 
                   planned_start_date, fg_warehouse, wip_warehouse, transfer_material_against,
                   use_multi_level_bom, update_consumed_material_cost_in_project, sales_order
        - 自定义字段: custom_work_oder_type, custom_style_name, custom_style_code
        - 子表字段: required_items, operations
        
    Returns:
        dict: 包含操作结果的字典
    """
    try:
        # 如果传入的是work_order_data参数，使用它；否则使用kwargs
        if 'work_order_data' in kwargs:
            work_order_data = kwargs['work_order_data']
            if isinstance(work_order_data, str):
                work_order_data = json.loads(work_order_data)
        else:
            work_order_data = kwargs
        
        # 验证必需字段
        required_fields = [
            'production_item', 'qty', 'company', 'bom_no'
        ]
        
        for field in required_fields:
            if not work_order_data.get(field):
                return {
                    'status': 'error',
                    'message': f'缺少必需字段: {field}'
                }
        
        # 创建工单文档
        work_order = frappe.new_doc('Work Order')
        
        # 设置基本字段
        work_order.production_item = work_order_data.get('production_item')
        work_order.qty = work_order_data.get('qty')
        work_order.company = work_order_data.get('company')
        work_order.bom_no = work_order_data.get('bom_no')
        work_order.stock_uom = work_order_data.get('stock_uom', 'Nos')
        
        # 设置可选字段
        if work_order_data.get('naming_series'):
            work_order.naming_series = work_order_data.get('naming_series')
        
        if work_order_data.get('description'):
            work_order.description = work_order_data.get('description')
            
        if work_order_data.get('item_name'):
            work_order.item_name = work_order_data.get('item_name')
            
        if work_order_data.get('expected_delivery_date'):
            work_order.expected_delivery_date = work_order_data.get('expected_delivery_date')
            
        if work_order_data.get('planned_start_date'):
            work_order.planned_start_date = work_order_data.get('planned_start_date')
            
        if work_order_data.get('fg_warehouse'):
            work_order.fg_warehouse = work_order_data.get('fg_warehouse')
            
        if work_order_data.get('wip_warehouse'):
            work_order.wip_warehouse = work_order_data.get('wip_warehouse')
            
        if work_order_data.get('transfer_material_against'):
            work_order.transfer_material_against = work_order_data.get('transfer_material_against')
            
        if work_order_data.get('use_multi_level_bom'):
            work_order.use_multi_level_bom = work_order_data.get('use_multi_level_bom')
            
        if work_order_data.get('update_consumed_material_cost_in_project'):
            work_order.update_consumed_material_cost_in_project = work_order_data.get('update_consumed_material_cost_in_project')
            
        if work_order_data.get('sales_order'):
            work_order.sales_order = work_order_data.get('sales_order')
        
        # 设置自定义字段
        if work_order_data.get('custom_work_oder_type'):
            work_order.custom_work_oder_type = work_order_data.get('custom_work_oder_type')
            
        if work_order_data.get('custom_style_name'):
            work_order.custom_style_name = work_order_data.get('custom_style_name')
            
        if work_order_data.get('custom_style_code'):
            work_order.custom_style_code = work_order_data.get('custom_style_code')
        
        # 设置所需物料
        if work_order_data.get('required_items'):
            for item in work_order_data.get('required_items'):
                work_order.append('required_items', {
                    'item_code': item.get('item_code'),
                    'item_name': item.get('item_name'),
                    'description': item.get('description'),
                    'required_qty': item.get('required_qty'),
                    'stock_uom': item.get('stock_uom'),
                    'rate': item.get('rate'),
                    'amount': item.get('amount'),
                    'source_warehouse': item.get('source_warehouse'),
                    'allow_alternative_item': item.get('allow_alternative_item', 0),
                    'include_item_in_manufacturing': item.get('include_item_in_manufacturing', 1)
                })
        
        # 设置操作工序
        if work_order_data.get('operations'):
            try:
                operations_list = work_order_data.get('operations')
                if isinstance(operations_list, list) and operations_list:
                    for operation in operations_list:
                        if isinstance(operation, dict) and operation.get('operation'):
                            work_order.append('operations', {
                                'operation': operation.get('operation'),
                                'status': operation.get('status', 'Pending'),
                                'time_in_mins': operation.get('time_in_mins', 0),
                                'planned_operating_cost': operation.get('planned_operating_cost', 0),
                                'sequence_id': operation.get('sequence_id', 1),
                                'hour_rate': operation.get('hour_rate', 0),
                                'batch_size': operation.get('batch_size', 0),
                                'completed_qty': operation.get('completed_qty', 0),
                                'process_loss_qty': operation.get('process_loss_qty', 0),
                                'actual_operation_time': operation.get('actual_operation_time', 0),
                                'actual_operating_cost': operation.get('actual_operating_cost', 0)
                            })
                        else:
                            # 记录无效的operation数据，但不影响工单创建
                            frappe.log_error(f"工单 {work_order.name} 的operation数据无效: {operation}", "Work Order Operations Error")
            except Exception as operations_error:
                # 如果operations处理出错，记录错误但不影响工单创建
                frappe.log_error(f"工单 {work_order.name} 处理operations时出错: {str(operations_error)}", "Work Order Operations Error")
        
        # 保存工单
        work_order.insert()
        
        return {
            'status': 'success',
            'message': '工单保存成功',
            'work_order_name': work_order.name,
            'data': work_order.as_dict()
        }
        
    except Exception as e:
        frappe.log_error(f"保存工单时出错: {str(e)}", "Work Order Save Error")
        return {
            'status': 'error',
            'message': f'保存工单时出错: {str(e)}'
        }


# 为bench execute专门创建一个简化的测试函数
@frappe.whitelist()
def test_save_work_order():
    """
    测试保存工单的简化函数
    """
    test_data = {
        'bom_no': 'BOM-FG000354-012',
        'company': 'DTY',
        'custom_work_oder_type': '纸样工单',
        'description': 'SM-0023 - 纸样制作',
        'expected_delivery_date': '2025-06-17',
        'fg_warehouse': '在制品 - D',
        'item_name': 'SM-0023 - 纸样',
        'naming_series': 'MFG-WO-.YYYY.-',
        'planned_start_date': '2025-06-10 10:00:00',
        'production_item': 'FG000354',
        'qty': 3,
        'stock_uom': 'Nos',
        'transfer_material_against': 'Work Order',
        'use_multi_level_bom': 1,
        'wip_warehouse': '在制品 - D',
        'custom_style_name': 'SM-0023',
        'custom_style_code': 'STYLE-0023',
        'operations': [
            {
                'operation': '裁剪',
                'status': 'Pending',
                'time_in_mins': 100,
                'planned_operating_cost': 0,
                'sequence_id': 1,
                'hour_rate': 0,
                'batch_size': 0,
                'completed_qty': 0,
                'process_loss_qty': 0,
                'actual_operation_time': 0,
                'actual_operating_cost': 0
            },
            {
                'operation': '缝制',
                'status': 'Pending',
                'time_in_mins': 150,
                'planned_operating_cost': 0,
                'sequence_id': 2,
                'hour_rate': 0,
                'batch_size': 0,
                'completed_qty': 0,
                'process_loss_qty': 0,
                'actual_operation_time': 0,
                'actual_operating_cost': 0
            }
        ]
    }
    
    return save_work_order(**test_data)


@frappe.whitelist()
def get_work_order(work_order_name):
    """
    获取工单信息的白名单API方法
    
    Args:
        work_order_name: 工单名称
        
    Returns:
        dict: 工单信息
    """
    try:
        if not work_order_name:
            return {
                'status': 'error',
                'message': '工单名称不能为空'
            }
            
        work_order = frappe.get_doc('Work Order', work_order_name)
        
        return {
            'status': 'success',
            'data': work_order.as_dict()
        }
        
    except frappe.DoesNotExistError:
        return {
            'status': 'error',
            'message': f'工单 {work_order_name} 不存在'
        }
    except Exception as e:
        frappe.log_error(f"获取工单时出错: {str(e)}", "Work Order Get Error")
        return {
            'status': 'error',
            'message': f'获取工单时出错: {str(e)}'
        }


@frappe.whitelist()
def get_work_order_list(page=1, page_size=20, filters=None, order_by=None, fields=None):
    """
    获取工单列表的白名单API方法（支持分页、子表信息和Job Card明细）
    
    Args:
        page: 页码，默认为1
        page_size: 每页数量，默认为20
        filters: 过滤条件，可以是字符串或字典
        order_by: 排序字段，默认为creation desc
        fields: 要获取的字段列表，如果为None则获取所有字段
        
    Returns:
        dict: 包含工单列表和分页信息的字典，每个工单包含以下子表信息：
        - required_items: 所需物料
        - operations: 操作
        - material_consumption: 物料消耗
        - material_transfer: 物料转移
        - assignments: 分配信息
        - job_cards: Job Card明细（包含所有子表信息）
    """
    try:
        # 参数处理
        page = int(page) if page else 1
        page_size = int(page_size) if page_size else 20
        
        # 处理filters参数
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except (json.JSONDecodeError, TypeError):
                filters = {}
        elif filters is None:
            filters = {}
        
        # 处理fields参数
        if isinstance(fields, str):
            try:
                fields = json.loads(fields)
            except (json.JSONDecodeError, TypeError):
                fields = None
        
        # 获取Work Order文档的所有字段
        work_order_meta = frappe.get_meta('Work Order')
        available_fields = [field.fieldname for field in work_order_meta.fields]

        # 添加系统字段（这些字段存在于数据库中但不在元数据中）
        system_fields = ['_assign', '_user_tags', '_comments', '_liked_by', '_seen']
        available_fields.extend(system_fields)
        
        # 默认字段列表（只包含确定存在的基础字段）
        default_fields = [
            'name', 'production_item', 'item_name', 'qty', 'company', 
            'bom_no', 'status', 'docstatus', 'description', 'stock_uom',
            'expected_delivery_date', 'planned_start_date', 'planned_end_date',
            'actual_start_date', 'actual_end_date', 'fg_warehouse', 'wip_warehouse',
            'transfer_material_against', 'use_multi_level_bom', 'sales_order',
            'creation', 'modified', 'owner', 'modified_by','_assign'
        ]
        
        # 检查自定义字段是否存在，如果存在则添加到默认字段中
        custom_fields = [
            'custom_work_oder_type', 'custom_style_name', 'custom_style_code'
        ]
        
        for custom_field in custom_fields:
            if custom_field in available_fields:
                default_fields.append(custom_field)
        
        # 如果用户没有指定字段，使用默认字段
        if fields is None:
            fields = default_fields
        else:
            # 验证用户指定的字段是否存在
            valid_fields = []
            for field in fields:
                if field in available_fields:
                    valid_fields.append(field)
                else:
                    frappe.log_error(f"字段 {field} 在Work Order中不存在", "Work Order List Field Error")
            
            if not valid_fields:
                # 如果所有字段都无效，使用默认字段
                fields = default_fields
            else:
                fields = valid_fields
        
        # 默认排序
        if not order_by:
            order_by = 'creation desc'
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取工单列表
        work_orders = frappe.get_all(
            'Work Order',
            filters=filters,
            fields=fields,
            order_by=order_by,
            limit=page_size,
            limit_start=offset
        )
        
        # 获取总数
        total_count = frappe.db.count('Work Order', filters=filters)
        
        # 获取每个工单的详细信息（包括子表）
        detailed_work_orders = []
        for work_order in work_orders:
            try:
                # 获取完整的工单文档（包含子表）
                work_order_doc = frappe.get_doc('Work Order', work_order.name)
                work_order_dict = work_order_doc.as_dict()

                # 确保 _assign 字段被正确包含
                assign_value = frappe.db.get_value('Work Order', work_order.name, '_assign')
                work_order_dict['_assign'] = assign_value if assign_value else None
                
                # 获取子表信息
                sub_tables = {}
                
                # 获取所需物料子表
                if hasattr(work_order_doc, 'required_items') and work_order_doc.required_items:
                    sub_tables['required_items'] = []
                    for item in work_order_doc.required_items:
                        sub_tables['required_items'].append(item.as_dict())
                
                # 获取操作子表
                if hasattr(work_order_doc, 'operations') and work_order_doc.operations:
                    sub_tables['operations'] = []
                    for operation in work_order_doc.operations:
                        sub_tables['operations'].append(operation.as_dict())
                
                # 获取物料消耗子表
                if hasattr(work_order_doc, 'material_consumption') and work_order_doc.material_consumption:
                    sub_tables['material_consumption'] = []
                    for consumption in work_order_doc.material_consumption:
                        sub_tables['material_consumption'].append(consumption.as_dict())
                
                # 获取物料转移子表
                if hasattr(work_order_doc, 'material_transfer') and work_order_doc.material_transfer:
                    sub_tables['material_transfer'] = []
                    for transfer in work_order_doc.material_transfer:
                        sub_tables['material_transfer'].append(transfer.as_dict())
                
                # 获取分配信息
                try:
                    from frappe.desk.form import assign_to as frappe_assign_to
                    assignments = frappe_assign_to.get({
                        'doctype': 'Work Order',
                        'name': work_order.name
                    })
                    sub_tables['assignments'] = assignments
                except Exception as assignment_error:
                    sub_tables['assignments'] = []
                    frappe.log_error(f"获取工单 {work_order.name} 分配信息失败: {str(assignment_error)}")
                
                # 通过work order 的custom_sales_order字段获取对应的纸样单，然后获取纸样单的的纸样师的信息
                try:
                    paper_pattern_doc = frappe.get_doc("RG Paper Pattern", work_order.custom_sales_order)
                    sub_tables['paper_pattern'] = paper_pattern_doc.as_dict()
                except Exception as paper_pattern_error:
                    sub_tables['paper_pattern'] = []
                    frappe.log_error(f"获取工单 {work_order.name} 纸样单信息失败: {str(paper_pattern_error)}")
                    
                # 获取Job Card明细
                try:
                    job_cards = frappe.get_all(
                        'Job Card',
                        filters={'work_order': work_order.name},
                        fields=['name', 'operation', 'workstation', 'status', 'for_quantity', 
                               'total_completed_qty', 'actual_start_date', 'actual_end_date',
                               'expected_start_date', 'expected_end_date', 'time_required',
                               'total_time_in_mins', 'posting_date', 'remarks', 'docstatus',
                               'creation', 'modified', 'owner', 'modified_by']
                    )
                    
                    # 获取每个Job Card的详细信息（包括子表）
                    detailed_job_cards = []
                    for job_card in job_cards:
                        try:
                            job_card_doc = frappe.get_doc('Job Card', job_card.name)
                            job_card_dict = job_card_doc.as_dict()
                            
                            # 获取Job Card的子表信息
                            job_card_sub_tables = {}
                            
                            # 获取Job Card Items子表
                            if hasattr(job_card_doc, 'items') and job_card_doc.items:
                                job_card_sub_tables['items'] = []
                                for item in job_card_doc.items:
                                    job_card_sub_tables['items'].append(item.as_dict())
                            
                            # 获取Job Card Operations子表
                            if hasattr(job_card_doc, 'sub_operations') and job_card_doc.sub_operations:
                                job_card_sub_tables['sub_operations'] = []
                                for operation in job_card_doc.sub_operations:
                                    job_card_sub_tables['sub_operations'].append(operation.as_dict())
                            
                            # 获取Job Card Time Logs子表
                            if hasattr(job_card_doc, 'time_logs') and job_card_doc.time_logs:
                                job_card_sub_tables['time_logs'] = []
                                for time_log in job_card_doc.time_logs:
                                    job_card_sub_tables['time_logs'].append(time_log.as_dict())
                            
                            # 获取Job Card Scheduled Time Logs子表
                            if hasattr(job_card_doc, 'scheduled_time_logs') and job_card_doc.scheduled_time_logs:
                                job_card_sub_tables['scheduled_time_logs'] = []
                                for scheduled_log in job_card_doc.scheduled_time_logs:
                                    job_card_sub_tables['scheduled_time_logs'].append(scheduled_log.as_dict())
                            
                            # 获取Job Card Scrap Items子表
                            if hasattr(job_card_doc, 'scrap_items') and job_card_doc.scrap_items:
                                job_card_sub_tables['scrap_items'] = []
                                for scrap_item in job_card_doc.scrap_items:
                                    job_card_sub_tables['scrap_items'].append(scrap_item.as_dict())
                            
                            # 合并Job Card主表和子表信息
                            job_card_dict['sub_tables'] = job_card_sub_tables
                            detailed_job_cards.append(job_card_dict)
                            
                        except Exception as job_card_detail_error:
                            # 如果获取Job Card详细信息失败，至少返回基本信息
                            frappe.log_error(f"获取Job Card {job_card.name} 详细信息失败: {str(job_card_detail_error)}")
                            job_card['sub_tables'] = {}
                            detailed_job_cards.append(job_card)
                    
                    sub_tables['job_cards'] = detailed_job_cards
                    
                except Exception as job_card_error:
                    sub_tables['job_cards'] = []
                    frappe.log_error(f"获取工单 {work_order.name} Job Card信息失败: {str(job_card_error)}")
                
                # 合并主表和子表信息
                work_order_dict['sub_tables'] = sub_tables
                detailed_work_orders.append(work_order_dict)
                
            except Exception as detail_error:
                # 如果获取详细信息失败，至少返回基本信息
                frappe.log_error(f"获取工单 {work_order.name} 详细信息失败: {str(detail_error)}")
                work_order['sub_tables'] = {}
                detailed_work_orders.append(work_order)
        
        # 计算分页信息
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            'status': 'success',
            'message': f'成功获取工单列表，共 {total_count} 条记录',
            'data': {
                'work_orders': detailed_work_orders,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                },
                'filters_applied': filters,
                'order_by': order_by,
                'fields_used': fields,
                'available_fields': available_fields
            }
        }
        
    except Exception as e:
        frappe.log_error("获取工单列表时出错", "Work Order List Get Error")
        return {
            'status': 'error',
            'message': f'获取工单列表时出错: {str(e)}'
        }


@frappe.whitelist()
def test_get_work_order_list():
    """
    测试获取工单列表功能的函数（包含Job Card信息）
    """
    try:
        # 测试基本分页
        result1 = get_work_order_list(page=1, page_size=5)
        
        # 测试带过滤条件
        filters = {'status': 'Draft', 'docstatus': 0}
        result2 = get_work_order_list(page=1, page_size=3, filters=filters)
        
        # 测试自定义字段
        fields = ['name', 'production_item', 'qty', 'status', 'custom_work_oder_type']
        result3 = get_work_order_list(page=1, page_size=2, fields=fields)
        
        # 测试包含Job Card信息的工单
        # 查找有Job Card的工单
        job_card_work_orders = frappe.get_all(
            'Job Card',
            fields=['work_order'],
            limit=3
        )
        
        if job_card_work_orders:
            work_order_names = [jc.work_order for jc in job_card_work_orders]
            filters_with_job_cards = {'name': ['in', work_order_names]}
            result4 = get_work_order_list(page=1, page_size=len(work_order_names), filters=filters_with_job_cards)
        else:
            result4 = {'message': '没有找到包含Job Card的工单'}
        
        return {
            'status': 'success',
            'message': '工单列表获取测试完成（包含Job Card信息）',
            'test_results': {
                'basic_pagination': result1,
                'with_filters': result2,
                'with_custom_fields': result3,
                'with_job_cards': result4
            },
            'job_card_info': {
                'total_job_cards': frappe.db.count('Job Card'),
                'work_orders_with_job_cards': len(set([jc.work_order for jc in job_card_work_orders])) if job_card_work_orders else 0
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'测试工单列表获取功能时出错: {str(e)}'
        }


@frappe.whitelist()
def update_work_order(work_order_name, work_order_data):
    """
    更新工单信息的白名单API方法（支持操作工序）
    
    Args:
        work_order_name: 工单名称
        work_order_data: 要更新的工单数据，支持以下字段：
        - 主表字段: 所有Work Order主表字段
        - 子表字段: 
          - required_items: 所需物料列表
          - operations: 操作工序列表
        
    Returns:
        dict: 操作结果
    """
    try:
        if not work_order_name:
            return {
                'status': 'error',
                'message': '工单名称不能为空'
            }
            
        work_order = frappe.get_doc('Work Order', work_order_name)
        
        # 更新字段
        for field, value in work_order_data.items():
            if field not in ['required_items', 'operations'] and hasattr(work_order, field):
                setattr(work_order, field, value)
        
        # 更新所需物料
        if 'required_items' in work_order_data:
            work_order.required_items = []
            for item in work_order_data['required_items']:
                work_order.append('required_items', item)
        
        # 更新操作工序
        if 'operations' in work_order_data:
            try:
                operations_list = work_order_data['operations']
                if isinstance(operations_list, list):
                    work_order.operations = []
                    for operation in operations_list:
                        if isinstance(operation, dict) and operation.get('operation'):
                            work_order.append('operations', operation)
                        else:
                            # 记录无效的operation数据，但不影响工单更新
                            frappe.log_error(f"工单 {work_order_name} 的operation数据无效: {operation}", "Work Order Operations Update Error")
                else:
                    frappe.log_error(f"工单 {work_order_name} 的operations字段不是列表: {operations_list}", "Work Order Operations Update Error")
            except Exception as operations_error:
                # 如果operations处理出错，记录错误但不影响工单更新
                frappe.log_error(f"工单 {work_order_name} 处理operations时出错: {str(operations_error)}", "Work Order Operations Update Error")
        
        work_order.save()
        
        return {
            'status': 'success',
            'message': '工单更新成功',
            'data': work_order.as_dict()
        }
        
    except frappe.DoesNotExistError:
        return {
            'status': 'error',
            'message': f'工单 {work_order_name} 不存在'
        }
    except Exception as e:
        frappe.log_error(f"更新工单时出错: {str(e)}", "Work Order Update Error")
        return {
            'status': 'error',
            'message': f'更新工单时出错: {str(e)}'
        }


@frappe.whitelist()
def assign_work_order(work_order_name, assign_to, description=None, priority="Medium", date=None):
    """
    分配工单给指定用户的白名单API方法
    
    Args:
        work_order_name: 工单名称
        assign_to: 要分配给的用户（可以是字符串或用户列表）
        description: 分配描述
        priority: 优先级 (Low, Medium, High)
        date: 完成日期
        
    Returns:
        dict: 操作结果
    """
    try:
        if not work_order_name:
            return {
                'status': 'error',
                'message': '工单名称不能为空'
            }
        
        # 检查工单是否存在
        if not frappe.db.exists('Work Order', work_order_name):
            return {
                'status': 'error',
                'message': f'工单 {work_order_name} 不存在'
            }
        
        # 处理assign_to参数
        if isinstance(assign_to, str):
            try:
                # 尝试解析JSON字符串
                assign_to_list = json.loads(assign_to)
                if not isinstance(assign_to_list, list):
                    assign_to_list = [assign_to]
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，则作为单个用户处理
                assign_to_list = [assign_to]
        elif isinstance(assign_to, list):
            assign_to_list = assign_to
        else:
            assign_to_list = [str(assign_to)]
        
        # 验证用户是否存在
        for user in assign_to_list:
            if not frappe.db.exists('User', user):
                return {
                    'status': 'error',
                    'message': f'用户 {user} 不存在'
                }
        
        # 设置默认描述
        if not description:
            description = f'工单 {work_order_name} 已分配给您'
        
        # 使用Frappe的标准分配功能
        from frappe.desk.form import assign_to as frappe_assign_to
        
        assignment_args = {
            'assign_to': assign_to_list,
            'doctype': 'Work Order',
            'name': work_order_name,
            'description': description,
            'priority': priority or 'Medium'
        }
        
        if date:
            assignment_args['date'] = date
        
        # 执行分配
        result = frappe_assign_to.add(assignment_args)
        
        return {
            'status': 'success',
            'message': f'工单 {work_order_name} 已成功分配给 {", ".join(assign_to_list)}',
            'assignments': result
        }
        
    except Exception as e:
        frappe.log_error(f"分配工单时出错: {str(e)}", "Work Order Assignment Error")
        return {
            'status': 'error',
            'message': f'分配工单时出错: {str(e)}'
        }


@frappe.whitelist()
def remove_work_order_assignment(work_order_name, assign_to=None):
    """
    移除工单分配的白名单API方法
    
    Args:
        work_order_name: 工单名称
        assign_to: 要移除分配的用户（可选，如果不指定则移除所有分配）
        
    Returns:
        dict: 操作结果
    """
    try:
        if not work_order_name:
            return {
                'status': 'error',
                'message': '工单名称不能为空'
            }
        
        # 检查工单是否存在
        if not frappe.db.exists('Work Order', work_order_name):
            return {
                'status': 'error',
                'message': f'工单 {work_order_name} 不存在'
            }
        
        from frappe.desk.form import assign_to as frappe_assign_to
        
        if assign_to:
            # 移除特定用户的分配
            result = frappe_assign_to.remove('Work Order', work_order_name, assign_to)
            message = f'已移除用户 {assign_to} 对工单 {work_order_name} 的分配'
        else:
            # 移除所有分配
            result = frappe_assign_to.clear('Work Order', work_order_name)
            message = f'已移除工单 {work_order_name} 的所有分配'
        
        return {
            'status': 'success',
            'message': message,
            'assignments': result
        }
        
    except Exception as e:
        frappe.log_error(f"移除工单分配时出错: {str(e)}", "Work Order Assignment Remove Error")
        return {
            'status': 'error',
            'message': f'移除工单分配时出错: {str(e)}'
        }


@frappe.whitelist()
def get_work_order_assignments(work_order_name):
    """
    获取工单分配信息的白名单API方法
    
    Args:
        work_order_name: 工单名称
        
    Returns:
        dict: 分配信息
    """
    try:
        if not work_order_name:
            return {
                'status': 'error',
                'message': '工单名称不能为空'
            }
        
        # 检查工单是否存在
        if not frappe.db.exists('Work Order', work_order_name):
            return {
                'status': 'error',
                'message': f'工单 {work_order_name} 不存在'
            }
        
        from frappe.desk.form import assign_to as frappe_assign_to
        
        # 获取分配信息
        assignments = frappe_assign_to.get({
            'doctype': 'Work Order',
            'name': work_order_name
        })
        
        return {
            'status': 'success',
            'work_order_name': work_order_name,
            'assignments': assignments,
            'total_assignments': len(assignments) if assignments else 0
        }
        
    except Exception as e:
        frappe.log_error(f"获取工单分配时出错: {str(e)}", "Work Order Assignment Get Error")
        return {
            'status': 'error',
            'message': f'获取工单分配时出错: {str(e)}'
        }


@frappe.whitelist()
def get_work_order_job_cards(work_order_name):
    """
    获取工单对应的Job Card明细信息的白名单API方法
    
    Args:
        work_order_name: 工单名称
        
    Returns:
        dict: Job Card信息
    """
    try:
        if not work_order_name:
            return {
                'status': 'error',
                'message': '工单名称不能为空'
            }
        
        # 检查工单是否存在
        if not frappe.db.exists('Work Order', work_order_name):
            return {
                'status': 'error',
                'message': f'工单 {work_order_name} 不存在'
            }
        
        # 获取Job Card列表
        job_cards = frappe.get_all(
            'Job Card',
            filters={'work_order': work_order_name},
            fields=['name', 'operation', 'workstation', 'status', 'for_quantity', 
                   'total_completed_qty', 'actual_start_date', 'actual_end_date',
                   'expected_start_date', 'expected_end_date', 'time_required',
                   'total_time_in_mins', 'posting_date', 'remarks', 'docstatus',
                   'creation', 'modified', 'owner', 'modified_by']
        )
        
        # 获取每个Job Card的详细信息（包括子表）
        detailed_job_cards = []
        for job_card in job_cards:
            try:
                job_card_doc = frappe.get_doc('Job Card', job_card.name)
                job_card_dict = job_card_doc.as_dict()
                
                # 获取Job Card的子表信息
                job_card_sub_tables = {}
                
                # 获取Job Card Items子表
                if hasattr(job_card_doc, 'items') and job_card_doc.items:
                    job_card_sub_tables['items'] = []
                    for item in job_card_doc.items:
                        job_card_sub_tables['items'].append(item.as_dict())
                
                # 获取Job Card Operations子表
                if hasattr(job_card_doc, 'sub_operations') and job_card_doc.sub_operations:
                    job_card_sub_tables['sub_operations'] = []
                    for operation in job_card_doc.sub_operations:
                        job_card_sub_tables['sub_operations'].append(operation.as_dict())
                
                # 获取Job Card Time Logs子表
                if hasattr(job_card_doc, 'time_logs') and job_card_doc.time_logs:
                    job_card_sub_tables['time_logs'] = []
                    for time_log in job_card_doc.time_logs:
                        job_card_sub_tables['time_logs'].append(time_log.as_dict())
                
                # 获取Job Card Scheduled Time Logs子表
                if hasattr(job_card_doc, 'scheduled_time_logs') and job_card_doc.scheduled_time_logs:
                    job_card_sub_tables['scheduled_time_logs'] = []
                    for scheduled_log in job_card_doc.scheduled_time_logs:
                        job_card_sub_tables['scheduled_time_logs'].append(scheduled_log.as_dict())
                
                # 获取Job Card Scrap Items子表
                if hasattr(job_card_doc, 'scrap_items') and job_card_doc.scrap_items:
                    job_card_sub_tables['scrap_items'] = []
                    for scrap_item in job_card_doc.scrap_items:
                        job_card_sub_tables['scrap_items'].append(scrap_item.as_dict())
                
                # 合并Job Card主表和子表信息
                job_card_dict['sub_tables'] = job_card_sub_tables
                detailed_job_cards.append(job_card_dict)
                
            except Exception as job_card_detail_error:
                # 如果获取Job Card详细信息失败，至少返回基本信息
                frappe.log_error(f"获取Job Card {job_card.name} 详细信息失败: {str(job_card_detail_error)}")
                job_card['sub_tables'] = {}
                detailed_job_cards.append(job_card)
        
        # 统计各状态的数量
        status_counts = {}
        for job_card in detailed_job_cards:
            status = job_card.get('status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        result = {
            'status': 'success',
            'work_order_name': work_order_name,
            'job_cards': detailed_job_cards,
            'total_job_cards': len(detailed_job_cards),
            'summary': {
                'total_quantity': sum(jc.get('for_quantity', 0) for jc in detailed_job_cards),
                'total_completed_qty': sum(jc.get('total_completed_qty', 0) for jc in detailed_job_cards),
                'total_time_in_mins': sum(jc.get('total_time_in_mins', 0) for jc in detailed_job_cards),
                'status_counts': status_counts
            }
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(f"获取工单Job Card时出错: {str(e)}", "Work Order Job Card Get Error")
        return {
            'status': 'error',
            'message': f'获取工单Job Card时出错: {str(e)}'
        }


@frappe.whitelist()
def batch_assign_work_orders(**args):
    """
    批量分配工单的白名单API方法
    
    Args:
        **args: 关键字参数，支持以下格式：
        - assignments_data: 分配数据列表，每个元素包含工单名称和分配信息
        格式: [
            {
                "work_order_name": "MFG-WO-2025-00001",
                "assign_to": ["user1@example.com", "user2@example.com"],
                "description": "批量分配",
                "priority": "Medium"
            }
        ]
        
    Returns:
        dict: 批量操作结果
    """
    # 从args中获取assignments_data
    assignments_data = args.get('assignments_data')
    
    if isinstance(assignments_data, str):
        assignments_data = json.loads(assignments_data)
    
    if not isinstance(assignments_data, list):
        return {
            'status': 'error',
            'message': '输入数据必须是分配数据列表'
        }
    
    if not assignments_data:
        return {
            'status': 'error',
            'message': '分配数据列表不能为空'
        }
    
    try:
        successful_assignments = []
        failed_assignments = []
        
        for i, assignment_data in enumerate(assignments_data):
            work_order_name = assignment_data.get('work_order_name')
            assign_to = assignment_data.get('assign_to')
            
            if not work_order_name or not assign_to:
                failed_assignments.append({
                    'index': i + 1,
                    'work_order_name': work_order_name,
                    'error': '工单名称和分配用户不能为空'
                })
                continue
            
            # 将员工ID转换为用户邮箱
            try:
                user_emails = convert_employee_to_user_id(assign_to)
                if not user_emails:
                    failed_assignments.append({
                        'index': i + 1,
                        'work_order_name': work_order_name,
                        'error': f'无法找到员工 {assign_to} 对应的用户邮箱'
                    })
                    continue
            except Exception as e:
                failed_assignments.append({
                    'index': i + 1,
                    'work_order_name': work_order_name,
                    'error': f'员工ID转换失败: {str(e)}'
                })
                continue
            
            # 调用单个分配方法，使用转换后的邮箱
            result = assign_work_order(
                work_order_name=work_order_name,
                assign_to=user_emails,
                description=assignment_data.get('description'),
                priority=assignment_data.get('priority', 'Medium'),
                date=assignment_data.get('date')
            )
            
            if result.get('status') == 'success':
                # 分配成功后，尝试提交工单
                submit_result = None
                try:
                    work_order_doc = frappe.get_doc('Work Order', work_order_name)
                    if work_order_doc.docstatus == 0:  # 只有草稿状态才提交
                        work_order_doc.submit()
                        submit_result = 'success'
                    else:
                        submit_result = f'工单状态为 {work_order_doc.docstatus}，无需提交'
                except Exception as submit_error:
                    submit_result = f'submit失败: {str(submit_error)}'
                    frappe.log_error(f"工单 {work_order_name} 提交失败: {str(submit_error)}", "Work Order Submit Error")
                
                successful_assignments.append({
                    'index': i + 1,
                    'work_order_name': work_order_name,
                    'original_employee_id': assign_to,
                    'converted_user_emails': user_emails,
                    'assigned_to': user_emails,
                    'submit_result': submit_result
                })
            else:
                failed_assignments.append({
                    'index': i + 1,
                    'work_order_name': work_order_name,
                    'error': result.get('message')
                })
        
        # 统计提交结果
        submit_success_count = sum(1 for item in successful_assignments if item.get('submit_result') == 'success')
        submit_failed_count = len(successful_assignments) - submit_success_count
        
        return {
            'status': 'success' if successful_assignments else 'error',
            'message': f'批量分配完成: 成功 {len(successful_assignments)} 个，失败 {len(failed_assignments)} 个。提交成功 {submit_success_count} 个，提交失败 {submit_failed_count} 个',
            'total_count': len(assignments_data),
            'successful_count': len(successful_assignments),
            'failed_count': len(failed_assignments),
            'submit_success_count': submit_success_count,
            'submit_failed_count': submit_failed_count,
            'successful_assignments': successful_assignments,
            'failed_assignments': failed_assignments
        }
        
    except Exception as e:
        frappe.log_error(f"批量分配工单时出错: {str(e)}", "Batch Work Order Assignment Error")
        return {
            'status': 'error',
            'message': f'批量分配工单时出错: {str(e)}'
        }


@frappe.whitelist()
def test_assign_work_order():
    """
    测试工单分配功能的函数
    """
    # 首先创建一个测试工单
    test_work_order_result = test_save_work_order()
    
    if test_work_order_result.get('status') != 'success':
        return {
            'status': 'error',
            'message': '创建测试工单失败',
            'details': test_work_order_result
        }
    
    work_order_name = test_work_order_result.get('work_order_name')
    
    # 测试分配给当前用户
    assign_result = assign_work_order(
        work_order_name=work_order_name,
        assign_to=frappe.session.user,
        description='测试工单分配功能',
        priority='High'
    )
    
    # 获取分配信息
    assignments_result = get_work_order_assignments(work_order_name)
    
    return {
        'status': 'success',
        'message': '工单分配测试完成',
        'test_work_order': work_order_name,
        'assign_result': assign_result,
        'assignments_info': assignments_result
    }


@frappe.whitelist()
def test_get_work_order_job_cards():
    """
    测试获取工单Job Card信息的函数
    """
    try:
        # 查找有Job Card的工单
        job_card_work_orders = frappe.get_all(
            'Job Card',
            fields=['work_order'],
            limit=1
        )
        
        if not job_card_work_orders:
            return {
                'status': 'info',
                'message': '没有找到包含Job Card的工单，无法进行测试'
            }
        
        work_order_name = job_card_work_orders[0].work_order
        
        # 测试获取Job Card信息
        job_cards_result = get_work_order_job_cards(work_order_name)
        
        return {
            'status': 'success',
            'message': 'Job Card信息获取测试完成',
            'test_work_order': work_order_name,
            'job_cards_result': job_cards_result,
            'system_info': {
                'total_job_cards': frappe.db.count('Job Card'),
                'total_work_orders': frappe.db.count('Work Order'),
                'work_orders_with_job_cards': frappe.db.count('Job Card', filters={})
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'测试Job Card功能时出错: {str(e)}'
        }


@frappe.whitelist()
def complete_work_order(work_order_id: str, qty: float):
    """
    一键完工 Work Order
    :param work_order_id: 工单 ID，比如 "MFG-WO-2025-00130"
    :param qty: 要完工的数量
    :return: 提交后的 Stock Entry JSON
    """
    try:
        qty = flt(qty)
        
        # 验证工单是否存在
        if not frappe.db.exists('Work Order', work_order_id):
            return {
                'status': 'error',
                'message': f'工单 {work_order_id} 不存在'
            }
        
        # 获取工单文档
        work_order = frappe.get_doc('Work Order', work_order_id)
        
        # 验证工单状态
        if work_order.docstatus != 1:
            return {
                'status': 'error',
                'message': f'工单 {work_order_id} 未提交，无法完工'
            }
        
        if work_order.status == 'Completed':
            return {
                'status': 'error',
                'message': f'工单 {work_order_id} 已完成'
            }

        # 1. 调用 make_stock_entry 生成单据对象
        try:
            se_dict = make_stock_entry(work_order_id, "Manufacture", qty)
            frappe.logger().info(f"make_stock_entry 返回: {type(se_dict)}")
            
            if not se_dict:
                return {
                    'status': 'error',
                    'message': f'无法为工单 {work_order_id} 生成库存单据，make_stock_entry 返回 None'
                }
            
            # 从字典创建文档对象
            se_doc = frappe.get_doc(se_dict)
            
        except Exception as make_se_error:
            frappe.logger().error(f"make_stock_entry 调用失败: {str(make_se_error)}")
            return {
                'status': 'error',
                'message': f'生成库存单据失败: {str(make_se_error)}'
            }

        # 2. 保存单据
        se_doc.insert(ignore_permissions=True)

        # 3. 提交单据
        se_doc.submit()

        frappe.db.commit()

        return {
            'status': 'success',
            'message': f'工单 {work_order_id} 完工成功',
            'stock_entry': se_doc.as_dict()
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"完工工单 {work_order_id} 时出错: {str(e)}", "Work Order Complete Error")
        return {
            'status': 'error',
            'message': f'完工工单时出错: {str(e)}'
        }


@frappe.whitelist()
def test_operations_functionality():
    """
    专门测试operations字段功能的函数
    """
    test_data = [
        {
            'bom_no': 'BOM-FG000589-037',
            'company': 'DTY',
            'custom_work_oder_type': '大货工单',
            'description': '2026-LYQ - te0033 (t5) - 测试operations',
            'expected_delivery_date': '2025-08-24',
            'fg_warehouse': '在制品 - D',
            'item_name': 'FG000589',
            'naming_series': 'MFG-WO-.YYYY.-',
            'planned_start_date': '2025-08-18',
            'production_item': 'FG000589',
            'qty': 2,
            'stock_uom': '件',
            'transfer_material_against': 'Work Order',
            'use_multi_level_bom': 1,
            'wip_warehouse': '在制品 - D',
            'update_consumed_material_cost_in_project': 1,
            'sales_order': 'SO-250818-02913-04',
            'custom_assigned_employee': '',
            'custom_assigned_employee_name': '',
            'custom_pattern_name': 'RGPP-00421',
            'assign_to': [],
            'assignment_description': '生产通知单: SO-250818-02913-04',
            'assignment_priority': 'Medium',
            'operations': [
                {
                    'operation': '裁剪',
                    'status': 'Pending',
                    'time_in_mins': 100,
                    'planned_operating_cost': 0,
                    'sequence_id': 1,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                },
                {
                    'operation': '缝制',
                    'status': 'Pending',
                    'time_in_mins': 100,
                    'planned_operating_cost': 0,
                    'sequence_id': 2,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                },
                {
                    'operation': '后道',
                    'status': 'Pending',
                    'time_in_mins': 100,
                    'planned_operating_cost': 0,
                    'sequence_id': 3,
                    'hour_rate': 0,
                    'batch_size': 0,
                    'completed_qty': 0,
                    'process_loss_qty': 0,
                    'actual_operation_time': 0,
                    'actual_operating_cost': 0
                }
            ]
        }
    ]
    
    # 测试批量保存
    batch_result = batch_save_work_orders(test_data)
    
    # 如果批量保存成功，测试获取工单信息
    if batch_result.get('status') == 'success' and batch_result.get('created_work_orders'):
        work_order_name = batch_result['created_work_orders'][0]['work_order_name']
        
        # 获取工单详细信息
        work_order_info = get_work_order(work_order_name)
        
        # 获取工单列表（包含operations）
        work_order_list = get_work_order_list(
            page=1, 
            page_size=1, 
            filters={'name': work_order_name}
        )
        
        return {
            'status': 'success',
            'message': 'operations功能测试完成',
            'batch_save_result': batch_result,
            'work_order_detail': work_order_info,
            'work_order_list': work_order_list,
            'test_summary': {
                'operations_count': len(test_data[0]['operations']),
                'operations_names': [op['operation'] for op in test_data[0]['operations']],
                'created_work_order': work_order_name
            }
        }
    else:
        return {
            'status': 'error',
            'message': 'operations功能测试失败',
            'batch_save_result': batch_result
        }


@frappe.whitelist()
def test_operations_error_handling():
    """
    测试operations字段错误处理的函数
    """
    test_cases = [
        {
            'name': '正常operations数据',
            'data': {
                'bom_no': 'BOM-FG000589-037',
                'company': 'DTY',
                'production_item': 'FG000589',
                'qty': 1,
                'operations': [
                    {
                        'operation': '裁剪',
                        'status': 'Pending',
                        'time_in_mins': 100
                    }
                ]
            }
        },
        {
            'name': '没有operations字段',
            'data': {
                'bom_no': 'BOM-FG000589-037',
                'company': 'DTY',
                'production_item': 'FG000589',
                'qty': 1
            }
        },
        {
            'name': 'operations为空列表',
            'data': {
                'bom_no': 'BOM-FG000589-037',
                'company': 'DTY',
                'production_item': 'FG000589',
                'qty': 1,
                'operations': []
            }
        },
        {
            'name': 'operations为None',
            'data': {
                'bom_no': 'BOM-FG000589-037',
                'company': 'DTY',
                'production_item': 'FG000589',
                'qty': 1,
                'operations': None
            }
        },
        {
            'name': 'operations包含无效数据',
            'data': {
                'bom_no': 'BOM-FG000589-037',
                'company': 'DTY',
                'production_item': 'FG000589',
                'qty': 1,
                'operations': [
                    {
                        'operation': '裁剪',
                        'status': 'Pending',
                        'time_in_mins': 100
                    },
                    {
                        'status': 'Pending'  # 缺少operation字段
                    },
                    'invalid_operation',  # 不是字典
                    {
                        'operation': '缝制',
                        'status': 'Pending',
                        'time_in_mins': 150
                    }
                ]
            }
        },
        {
            'name': 'operations不是列表',
            'data': {
                'bom_no': 'BOM-FG000589-037',
                'company': 'DTY',
                'production_item': 'FG000589',
                'qty': 1,
                'operations': 'not_a_list'
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        try:
            # 测试批量保存
            batch_result = batch_save_work_orders([test_case['data']])
            
            results.append({
                'test_case': test_case['name'],
                'status': 'success',
                'batch_result': batch_result,
                'message': f"测试用例 {i+1} 执行成功"
            })
            
        except Exception as e:
            results.append({
                'test_case': test_case['name'],
                'status': 'error',
                'error': str(e),
                'message': f"测试用例 {i+1} 执行失败"
            })
    
    # 统计结果
    successful_tests = [r for r in results if r['status'] == 'success']
    failed_tests = [r for r in results if r['status'] == 'error']
    
    return {
        'status': 'success',
        'message': f'operations错误处理测试完成: 成功 {len(successful_tests)} 个，失败 {len(failed_tests)} 个',
        'total_tests': len(test_cases),
        'successful_tests': len(successful_tests),
        'failed_tests': len(failed_tests),
        'test_results': results,
        'summary': {
            'should_work_without_operations': any(r['test_case'] == '没有operations字段' and r['status'] == 'success' for r in results),
            'should_work_with_empty_operations': any(r['test_case'] == 'operations为空列表' and r['status'] == 'success' for r in results),
            'should_work_with_invalid_operations': any(r['test_case'] == 'operations包含无效数据' and r['status'] == 'success' for r in results)
        }
    }


@frappe.whitelist()
def test_work_order_without_operations():
    """
    测试没有operations字段的工单创建
    """
    test_data = [
        {
            'bom_no': 'BOM-FG000589-037',
            'company': 'DTY',
            'custom_work_oder_type': '大货工单',
            'description': '测试工单 - 没有operations字段',
            'expected_delivery_date': '2025-08-24',
            'fg_warehouse': '在制品 - D',
            'item_name': 'FG000589',
            'naming_series': 'MFG-WO-.YYYY.-',
            'planned_start_date': '2025-08-18',
            'production_item': 'FG000589',
            'qty': 1,
            'stock_uom': '件',
            'transfer_material_against': 'Work Order',
            'use_multi_level_bom': 1,
            'wip_warehouse': '在制品 - D',
            'update_consumed_material_cost_in_project': 1,
            'sales_order': 'SO-250818-02913-04',
            'custom_pattern_name': 'RGPP-00421'
            # 注意：这里没有operations字段
        }
    ]
    
    result = batch_save_work_orders(test_data)
    
    return {
        'status': 'success',
        'message': '测试没有operations字段的工单创建',
        'result': result,
        'test_info': {
            'has_operations_field': False,
            'expected_behavior': '工单应该正常创建，不受operations字段缺失影响'
        }
    }

"""
=== CURL 测试示例 ===

1. 批量保存工单（包含分配功能和操作工序）的curl命令：

curl -X POST "http://your-site-url/api/method/rongguan_erp.utils.api.work_order.batch_save_work_orders" \
-H "Content-Type: application/json" \
-H "Authorization: token your_api_key:your_api_secret" \
-d '{
  "work_orders_data": [
    {
      "bom_no": "BOM-FG000589-037",
      "company": "DTY",
      "custom_work_oder_type": "大货工单",
      "description": "2026-LYQ - te0033 (t5) - API测试1",
      "expected_delivery_date": "2025-08-24",
      "fg_warehouse": "在制品 - D",
      "item_name": "FG000589",
      "naming_series": "MFG-WO-.YYYY.-",
      "planned_start_date": "2025-08-18",
      "production_item": "FG000589",
      "qty": 2,
      "stock_uom": "件",
      "transfer_material_against": "Work Order",
      "use_multi_level_bom": 1,
      "wip_warehouse": "在制品 - D",
      "update_consumed_material_cost_in_project": 1,
      "sales_order": "SO-250818-02913-04",
      "custom_pattern_name": "RGPP-00421",
      "assign_to": "administrator@example.com",
      "assignment_description": "API测试工单1 - 请及时处理",
      "assignment_priority": "High",
      "operations": [
        {
          "operation": "裁剪",
          "status": "Pending",
          "time_in_mins": 100,
          "planned_operating_cost": 0,
          "sequence_id": 1,
          "hour_rate": 0,
          "batch_size": 0,
          "completed_qty": 0,
          "process_loss_qty": 0,
          "actual_operation_time": 0,
          "actual_operating_cost": 0
        },
        {
          "operation": "缝制",
          "status": "Pending",
          "time_in_mins": 100,
          "planned_operating_cost": 0,
          "sequence_id": 2,
          "hour_rate": 0,
          "batch_size": 0,
          "completed_qty": 0,
          "process_loss_qty": 0,
          "actual_operation_time": 0,
          "actual_operating_cost": 0
        },
        {
          "operation": "后道",
          "status": "Pending",
          "time_in_mins": 100,
          "planned_operating_cost": 0,
          "sequence_id": 3,
          "hour_rate": 0,
          "batch_size": 0,
          "completed_qty": 0,
          "process_loss_qty": 0,
          "actual_operation_time": 0,
          "actual_operating_cost": 0
        }
      ]
    },
    {
      "bom_no": "BOM-FG000580-052",
      "company": "DTY",
      "custom_work_oder_type": "大货工单",
      "description": "2026-LYQ - te0033 (t5) - API测试2",
      "expected_delivery_date": "2025-08-24",
      "fg_warehouse": "在制品 - D",
      "item_name": "FG000580",
      "naming_series": "MFG-WO-.YYYY.-",
      "planned_start_date": "2025-08-18",
      "production_item": "FG000580",
      "qty": 3,
      "stock_uom": "件",
      "transfer_material_against": "Work Order",
      "use_multi_level_bom": 1,
      "wip_warehouse": "在制品 - D",
      "update_consumed_material_cost_in_project": 1,
      "sales_order": "SO-250818-02913-04",
      "custom_pattern_name": "RGPP-00421",
      "assign_to": ["administrator@example.com", "user2@example.com"],
      "assignment_description": "API测试工单2 - 分配给多个用户",
      "assignment_priority": "Medium",
      "operations": [
        {
          "operation": "裁剪",
          "status": "Pending",
          "time_in_mins": 120,
          "planned_operating_cost": 0,
          "sequence_id": 1,
          "hour_rate": 0,
          "batch_size": 0,
          "completed_qty": 0,
          "process_loss_qty": 0,
          "actual_operation_time": 0,
          "actual_operating_cost": 0
        },
        {
          "operation": "缝制",
          "status": "Pending",
          "time_in_mins": 180,
          "planned_operating_cost": 0,
          "sequence_id": 2,
          "hour_rate": 0,
          "batch_size": 0,
          "completed_qty": 0,
          "process_loss_qty": 0,
          "actual_operation_time": 0,
          "actual_operating_cost": 0
        }
      ]
    }
  ]
}'

2. 如果使用本地开发环境（site1.local），curl命令示例：

curl -X POST "http://site1.local:8000/api/method/rongguan_erp.utils.api.work_order.batch_save_work_orders" \
-H "Content-Type: application/json" \
-H "Cookie: sid=your_session_id" \
-d '{
  "work_orders_data": [
    {
      "bom_no": "BOM-FG000354-012",
      "company": "DTY",
      "production_item": "FG000354",
      "qty": 1,
      "assign_to": "administrator@example.com",
      "assignment_description": "测试分配",
      "assignment_priority": "High"
    }
  ]
}'

3. 获取API Token的方法：
   - 登录ERPNext
   - 转到用户设置 > API Access
   - 生成新的API Key和Secret

4. 获取Session ID的方法（用于开发测试）：
   - 在浏览器中登录ERPNext
   - 打开开发者工具 > Application > Cookies
   - 找到名为'sid'的cookie值

5. 分配相关参数说明：
   - assign_to: 可以是单个用户邮箱字符串，或用户邮箱数组
   - assignment_description: 分配描述（可选）
   - assignment_priority: 优先级，可选值：Low, Medium, High（默认Medium）
   - assignment_date: 完成日期（可选，格式：YYYY-MM-DD）

6. 响应格式示例：
{
  "message": {
    "status": "success",
    "message": "成功批量创建3个工单",
    "total_count": 3,
    "created_work_orders": [
      {
        "index": 1,
        "work_order_name": "MFG-WO-2025-00001",
        "production_item": "FG000354",
        "qty": 3,
        "assigned_to": ["administrator@example.com"],
        "assignment_status": "success"
      }
    ],
    "assignment_summary": {
      "total_assignments": 2,
      "successful_assignments": 2,
      "failed_assignments": 0
    }
  }
}

7. Job Card相关API说明：

7.1 获取工单Job Card明细：
GET /api/method/rongguan_erp.utils.api.work_order.get_work_order_job_cards
参数: work_order_name (工单名称)

响应格式：
{
  "message": {
    "status": "success",
    "work_order_name": "MFG-WO-2025-00001",
    "job_cards": [
      {
        "name": "PO-JOB-2025-00001",
        "operation": "Cutting",
        "workstation": "Cutting Station",
        "status": "Work In Progress",
        "for_quantity": 10,
        "total_completed_qty": 5,
        "sub_tables": {
          "items": [...],           // Job Card Items
          "sub_operations": [...],  // Job Card Operations
          "time_logs": [...],       // Job Card Time Logs
          "scheduled_time_logs": [...], // Scheduled Time Logs
          "scrap_items": [...]      // Scrap Items
        }
      }
    ],
    "total_job_cards": 1,
    "summary": {
      "total_quantity": 10,
      "total_completed_qty": 5,
      "total_time_in_mins": 120,
      "status_counts": {
        "Work In Progress": 1
      }
    }
  }
}

7.2 工单列表中的Job Card信息：
在get_work_order_list的响应中，每个工单的sub_tables字段现在包含job_cards数组，
包含该工单的所有Job Card明细信息。

7.3 Job Card子表字段说明：
- items: Job Card物料明细
- sub_operations: Job Card子操作
- time_logs: 时间记录
- scheduled_time_logs: 计划时间记录
- scrap_items: 废料项目

8. 测试Job Card功能：
bench execute rongguan_erp.utils.api.work_order.test_get_work_order_job_cards

9. 测试Operations功能：
bench execute rongguan_erp.utils.api.work_order.test_operations_functionality

10. Operations字段说明：
operations字段是Work Order的子表，用于定义生产工序。每个工序包含以下字段：
- operation: 工序名称（必填）
- status: 状态，可选值：Pending, Work In Progress, Completed（默认Pending）
- time_in_mins: 计划时间，单位分钟（默认0）
- planned_operating_cost: 计划操作成本（默认0）
- sequence_id: 序列ID，用于排序（默认1）
- hour_rate: 小时费率（默认0）
- batch_size: 批次大小（默认0）
- completed_qty: 完成数量（默认0）
- process_loss_qty: 工艺损耗数量（默认0）
- actual_operation_time: 实际操作时间（默认0）
- actual_operating_cost: 实际操作成本（默认0）

11. 支持的API方法：
- batch_save_work_orders: 批量保存工单（支持operations）
- save_work_order: 保存单个工单（支持operations）
- update_work_order: 更新工单（支持operations）
- get_work_order: 获取工单详情（包含operations）
- get_work_order_list: 获取工单列表（包含operations）

12. Operations字段容错处理：
- 如果operations字段不存在，工单创建不受影响
- 如果operations为空列表或None，工单创建不受影响
- 如果operations包含无效数据（缺少operation字段或格式错误），会记录错误但工单创建不受影响
- 如果operations不是列表格式，会记录错误但工单创建不受影响
- 所有operations相关的错误都会记录到系统日志中，便于排查问题

13. 测试Operations错误处理：
bench execute rongguan_erp.utils.api.work_order.test_operations_error_handling

14. 测试没有Operations字段的工单创建：
bench execute rongguan_erp.utils.api.work_order.test_work_order_without_operations
"""
