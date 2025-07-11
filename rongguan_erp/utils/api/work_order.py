import frappe
from frappe import _
from frappe.utils import nowdate, get_datetime
import json


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
    elif isinstance(employee_list, list):
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
            'custom_work_oder_type', 'custom_assigned_employee', 
            'custom_assigned_employee_name', 'custom_pattern_name'
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
    支持在保存工单的同时分配给员工
    
    Args:
        work_orders_data: 工单数据列表，每个元素都是一个工单数据字典
        可以包含以下分配相关字段：
        - assign_to: 分配给的员工ID或用户ID（字符串或列表）
        - assignment_description: 分配描述
        - assignment_priority: 分配优先级 (Low, Medium, High)
        - assignment_date: 分配完成日期
        
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
    测试批量保存工单的函数（包含分配功能）
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
            'custom_assigned_employee': 'HR-EMP-00001',
            'custom_assigned_employee_name': '林',
            'custom_pattern_name': 'SM-0023-1',
            # 分配相关字段 - 使用员工ID
            'assign_to': assign_to_value,
            'assignment_description': '批量测试工单1 - 请及时处理（使用员工ID）',
            'assignment_priority': 'High'
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
            'custom_assigned_employee': 'HR-EMP-00001',
            'custom_assigned_employee_name': '林',
            'custom_pattern_name': 'SM-0024-2',
            # 分配相关字段 - 使用员工ID
            'assign_to': assign_to_value,
            'assignment_description': '批量测试工单2 - 中等优先级（使用员工ID）',
            'assignment_priority': 'Medium'
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
            'custom_assigned_employee': 'HR-EMP-00001',
            'custom_assigned_employee_name': '林',
            'custom_pattern_name': 'SM-0025-3'
            # 这个工单没有分配信息，测试混合场景
        }
    ]
    
    result = batch_save_work_orders(test_data)
    
    # 添加测试信息
    result['test_info'] = {
        'test_employee': test_employee,
        'assign_to_value': assign_to_value,
        'message': '测试使用员工ID进行分配'
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
    保存生产工单的白名单API方法
    
    Args:
        **kwargs: 工单数据，支持直接传递参数或work_order_data字典
        
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
            
        if work_order_data.get('custom_assigned_employee'):
            work_order.custom_assigned_employee = work_order_data.get('custom_assigned_employee')
            
        if work_order_data.get('custom_assigned_employee_name'):
            work_order.custom_assigned_employee_name = work_order_data.get('custom_assigned_employee_name')
            
        if work_order_data.get('custom_pattern_name'):
            work_order.custom_pattern_name = work_order_data.get('custom_pattern_name')
        
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
        'custom_assigned_employee': 'HR-EMP-00001',
        'custom_assigned_employee_name': '林',
        'custom_pattern_name': 'SM-0023'
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
def update_work_order(work_order_name, work_order_data):
    """
    更新工单信息的白名单API方法
    
    Args:
        work_order_name: 工单名称
        work_order_data: 要更新的工单数据
        
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
            if field != 'required_items' and hasattr(work_order, field):
                setattr(work_order, field, value)
        
        # 更新所需物料
        if 'required_items' in work_order_data:
            work_order.required_items = []
            for item in work_order_data['required_items']:
                work_order.append('required_items', item)
        
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
def batch_assign_work_orders(assignments_data):
    """
    批量分配工单的白名单API方法
    
    Args:
        assignments_data: 分配数据列表，每个元素包含工单名称和分配信息
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
            
            # 调用单个分配方法
            result = assign_work_order(
                work_order_name=work_order_name,
                assign_to=assign_to,
                description=assignment_data.get('description'),
                priority=assignment_data.get('priority', 'Medium'),
                date=assignment_data.get('date')
            )
            
            if result.get('status') == 'success':
                successful_assignments.append({
                    'index': i + 1,
                    'work_order_name': work_order_name,
                    'assigned_to': assign_to if isinstance(assign_to, list) else [assign_to]
                })
            else:
                failed_assignments.append({
                    'index': i + 1,
                    'work_order_name': work_order_name,
                    'error': result.get('message')
                })
        
        return {
            'status': 'success' if successful_assignments else 'error',
            'message': f'批量分配完成: 成功 {len(successful_assignments)} 个，失败 {len(failed_assignments)} 个',
            'total_count': len(assignments_data),
            'successful_count': len(successful_assignments),
            'failed_count': len(failed_assignments),
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

"""
=== CURL 测试示例 ===

1. 批量保存工单（包含分配功能）的curl命令：

curl -X POST "http://your-site-url/api/method/rongguan_erp.utils.api.work_order.batch_save_work_orders" \
-H "Content-Type: application/json" \
-H "Authorization: token your_api_key:your_api_secret" \
-d '{
  "work_orders_data": [
    {
      "bom_no": "BOM-FG000354-012",
      "company": "DTY",
      "custom_work_oder_type": "纸样工单",
      "description": "SM-0023 - 纸样制作 (API测试1)",
      "expected_delivery_date": "2025-06-17",
      "fg_warehouse": "在制品 - D",
      "item_name": "SM-0023 - 纸样",
      "naming_series": "MFG-WO-.YYYY.-",
      "planned_start_date": "2025-06-10 10:00:00",
      "production_item": "FG000354",
      "qty": 3,
      "stock_uom": "Nos",
      "transfer_material_against": "Work Order",
      "use_multi_level_bom": 1,
      "wip_warehouse": "在制品 - D",
      "custom_assigned_employee": "HR-EMP-00001",
      "custom_assigned_employee_name": "林",
      "custom_pattern_name": "SM-0023-1",
      "assign_to": "administrator@example.com",
      "assignment_description": "API测试工单1 - 请及时处理",
      "assignment_priority": "High"
    },
    {
      "bom_no": "BOM-FG000354-012",
      "company": "DTY",
      "custom_work_oder_type": "纸样工单",
      "description": "SM-0024 - 纸样制作 (API测试2)",
      "expected_delivery_date": "2025-06-18",
      "fg_warehouse": "在制品 - D",
      "item_name": "SM-0024 - 纸样",
      "naming_series": "MFG-WO-.YYYY.-",
      "planned_start_date": "2025-06-11 10:00:00",
      "production_item": "FG000354",
      "qty": 5,
      "stock_uom": "Nos",
      "transfer_material_against": "Work Order",
      "use_multi_level_bom": 1,
      "wip_warehouse": "在制品 - D",
      "custom_assigned_employee": "HR-EMP-00001",
      "custom_assigned_employee_name": "林",
      "custom_pattern_name": "SM-0024-2",
      "assign_to": ["administrator@example.com", "user2@example.com"],
      "assignment_description": "API测试工单2 - 分配给多个用户",
      "assignment_priority": "Medium"
    },
    {
      "bom_no": "BOM-FG000354-012",
      "company": "DTY",
      "custom_work_oder_type": "纸样工单",
      "description": "SM-0025 - 纸样制作 (API测试3)",
      "expected_delivery_date": "2025-06-19",
      "fg_warehouse": "在制品 - D",
      "item_name": "SM-0025 - 纸样",
      "naming_series": "MFG-WO-.YYYY.-",
      "planned_start_date": "2025-06-12 10:00:00",
      "production_item": "FG000354",
      "qty": 2,
      "stock_uom": "Nos",
      "transfer_material_against": "Work Order",
      "use_multi_level_bom": 1,
      "wip_warehouse": "在制品 - D",
      "custom_assigned_employee": "HR-EMP-00001",
      "custom_assigned_employee_name": "林",
      "custom_pattern_name": "SM-0025-3"
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
"""
