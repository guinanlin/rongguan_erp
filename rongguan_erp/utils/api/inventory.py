import frappe
import json
from frappe import _
from frappe.utils import now_datetime, getdate
from typing import Dict, List, Optional, Any


@frappe.whitelist()
def get_stock_entries_with_items(
    page: int = 1,
    page_length: int = 10,
    filters: Optional[List] = None,
    fields: Optional[List] = None,
    order_by: str = "creation desc"
) -> Dict[str, Any]:
    """
    分页查询Stock Entry及其子表items
    
    Args:
        page: 页码，从1开始
        page_length: 每页记录数
        filters: 过滤条件
        fields: 查询字段
        order_by: 排序方式
    
    Returns:
        包含分页信息和数据的字典
    """
    try:
        # 默认字段
        if not fields:
            fields = [
                'name', 'naming_series', 'stock_entry_type', 'purpose', 
                'add_to_transit', 'company', 'posting_date', 'posting_time', 
                'set_posting_time', 'inspection_required', 'apply_putaway_rule', 
                'from_bom', 'use_multi_level_bom', 'fg_completed_qty', 
                'process_loss_percentage', 'process_loss_qty', 'to_warehouse', 
                'total_outgoing_value', 'total_incoming_value', 'value_difference', 
                'total_additional_costs', 'is_opening', 'per_transferred', 
                'total_amount', 'is_return', 'creation', 'modified', 'owner', 
                'modified_by', 'docstatus', 'idx', 'address_display', 
                'purchase_receipt_no', 'supplier_address', 'supplier_name', 
                'supplier', 'sales_invoice_no', 'delivery_note_no'
            ]
        
        # 默认过滤条件
        if not filters:
            filters = [
                ['stock_entry_type', 'in', [
                    'Material Receipt', 'Manufacture', 'Repack', 
                    'Disassemble', 'Send to Subcontractor'
                ]]
            ]
        
        # 计算偏移量
        start = (page - 1) * page_length
        
        # 查询主表数据
        stock_entries = frappe.get_list(
            'Stock Entry',
            fields=fields,
            filters=filters,
            order_by=order_by,
            limit_start=start,
            limit_page_length=page_length,
            ignore_permissions=True
        )
        
        # 获取总数
        total_count = frappe.db.count('Stock Entry', filters=filters)
        
        # 查询每个Stock Entry的items
        for entry in stock_entries:
            items = frappe.get_list(
                'Stock Entry Detail',
                fields=[
                    'name', 'parent', 'item_code', 'item_name', 'description',
                    'qty', 'basic_rate', 'basic_amount', 'additional_cost',
                    'valuation_rate', 'amount', 'serial_no', 'batch_no',
                    'actual_qty', 'transferred_qty', 'bom_no', 
                    'allow_zero_valuation_rate', 't_warehouse', 's_warehouse', 
                    'cost_center', 'expense_account', 'is_finished_item',
                    'sample_quantity', 'uom', 'conversion_factor', 'stock_uom',
                    'creation', 'modified', 'owner', 'modified_by', 'idx'
                ],
                filters={'parent': entry.name},
                order_by='idx',
                ignore_permissions=True
            )
            entry['items'] = items
        
        # 计算分页信息
        total_pages = (total_count + page_length - 1) // page_length
        has_prev = page > 1
        has_next = page < total_pages
        
        return {
            'message': stock_entries,
            'pagination': {
                'current_page': page,
                'page_length': page_length,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next,
                'prev_page': page - 1 if has_prev else None,
                'next_page': page + 1 if has_next else None
            }
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'message': _('查询Stock Entry失败')
        }


@frappe.whitelist()
def get_stock_entry_detail(stock_entry_name: str) -> Dict[str, Any]:
    """
    获取单个Stock Entry的详细信息
    
    Args:
        stock_entry_name: Stock Entry的名称
    
    Returns:
        包含Stock Entry详细信息的字典
    """
    try:
        # 获取主表信息
        stock_entry = frappe.get_doc('Stock Entry', stock_entry_name)
        
        # 获取items
        items = frappe.get_list(
            'Stock Entry Detail',
            fields=[
                'name', 'parent', 'item_code', 'item_name', 'description',
                'qty', 'basic_rate', 'basic_amount', 'additional_cost',
                'valuation_rate', 'amount', 'serial_no', 'batch_no',
                'warehouse', 'target_warehouse', 'actual_qty', 'transferred_qty',
                'bom_no', 'allow_zero_valuation_rate', 't_warehouse',
                's_warehouse', 'cost_center', 'expense_account',
                'is_finished_item', 'sample_quantity', 'uom', 'conversion_factor',
                'stock_uom', 'creation', 'modified', 'owner', 'modified_by', 'idx'
            ],
            filters={'parent': stock_entry_name},
            order_by='idx',
            ignore_permissions=True
        )
        
        return {
            'message': {
                'stock_entry': stock_entry.as_dict(),
                'items': items
            }
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'message': _('获取Stock Entry详情失败')
        }


@frappe.whitelist()
def search_stock_entries(
    search_term: str,
    page: int = 1,
    page_length: int = 10,
    stock_entry_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    搜索Stock Entry
    
    Args:
        search_term: 搜索关键词
        page: 页码
        page_length: 每页记录数
        stock_entry_types: 限制的stock_entry_type列表
    
    Returns:
        搜索结果
    """
    try:
        # 构建搜索过滤条件
        filters = [
            ['name', 'like', f'%{search_term}%']
        ]
        
        if stock_entry_types:
            filters.append(['stock_entry_type', 'in', stock_entry_types])
        
        return get_stock_entries_with_items(
            page=page,
            page_length=page_length,
            filters=filters
        )
        
    except Exception as e:
        return {
            'error': str(e),
            'message': _('搜索Stock Entry失败')
        }


def test_stock_entry_api():
    """
    Bench execute测试方法
    使用方法: bench execute rongguan_erp.utils.api.inventory.test_stock_entry_api
    """
    print("=== 测试Stock Entry API ===")
    
    # 测试1: 基本分页查询
    print("\n1. 测试基本分页查询:")
    result1 = get_stock_entries_with_items(page=1, page_length=5)
    print(f"返回记录数: {len(result1.get('message', []))}")
    print(f"分页信息: {result1.get('pagination', {})}")
    
    # 测试2: 自定义过滤条件
    print("\n2. 测试自定义过滤条件:")
    filters = [['stock_entry_type', '=', 'Material Receipt']]
    result2 = get_stock_entries_with_items(page=1, page_length=3, filters=filters)
    print(f"Material Receipt类型记录数: {len(result2.get('message', []))}")
    
    # 测试3: 搜索功能
    print("\n3. 测试搜索功能:")
    result3 = search_stock_entries('MAT', page=1, page_length=3)
    print(f"搜索'MAT'结果数: {len(result3.get('message', []))}")
    
    # 测试4: 如果有数据，测试详情查询
    if result1.get('message'):
        first_entry = result1['message'][0]
        print(f"\n4. 测试详情查询 - {first_entry['name']}:")
        detail = get_stock_entry_detail(first_entry['name'])
        if 'message' in detail:
            items_count = len(detail['message'].get('items', []))
            print(f"子表items数量: {items_count}")
        else:
            print(f"详情查询失败: {detail.get('error', '未知错误')}")
    
    # 测试5: 显示第一个记录的完整结构
    if result1.get('message'):
        print(f"\n5. 第一个记录结构示例:")
        first_record = result1['message'][0]
        print(f"主表字段数: {len(first_record)}")
        if 'items' in first_record:
            print(f"子表items数: {len(first_record['items'])}")
            if first_record['items']:
                print(f"第一个item字段: {list(first_record['items'][0].keys())}")
    
    print("\n=== 测试完成 ===")
    return result1


def test_pagination():
    """
    测试分页功能
    使用方法: bench execute rongguan_erp.utils.api.inventory.test_pagination
    """
    print("=== 测试分页功能 ===")
    
    # 测试不同页码
    for page in [1, 2, 3]:
        print(f"\n页码 {page}:")
        result = get_stock_entries_with_items(page=page, page_length=2)
        pagination = result.get('pagination', {})
        print(f"当前页: {pagination.get('current_page')}")
        print(f"总记录数: {pagination.get('total_count')}")
        print(f"总页数: {pagination.get('total_pages')}")
        print(f"有上一页: {pagination.get('has_prev')}")
        print(f"有下一页: {pagination.get('has_next')}")
        print(f"返回记录数: {len(result.get('message', []))}")
    
    print("\n=== 分页测试完成 ===")


def test_search():
    """
    测试搜索功能
    使用方法: bench execute rongguan_erp.utils.api.inventory.test_search
    """
    print("=== 测试搜索功能 ===")
    
    search_terms = ['MAT', 'STE', '2025']
    
    for term in search_terms:
        print(f"\n搜索关键词: '{term}'")
        result = search_stock_entries(term, page=1, page_length=5)
        count = len(result.get('message', []))
        print(f"搜索结果数: {count}")
        
        if result.get('message'):
            print("前3个结果:")
            for i, entry in enumerate(result['message'][:3]):
                print(f"  {i+1}. {entry.get('name')} - {entry.get('stock_entry_type')}")
    
    print("\n=== 搜索测试完成 ===")
