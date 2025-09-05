#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
委外加工服务费采购订单测试文件
"""

import frappe
import json
from rongguan_erp.utils.api.purchase_order_core import (
    create_subcontracting_service_purchase_order,
    create_subcontracting_service_po_simple,
    create_subcontracting_service_po_from_dict,
    get_subcontracting_service_info,
    validate_subcontracting_supplier
)

def test_subcontracting_service_info():
    """测试获取委外加工服务费信息"""
    print("=== 测试获取委外加工服务费信息 ===")
    
    try:
        info = get_subcontracting_service_info()
        print(f"委外加工服务费信息: {json.dumps(info, ensure_ascii=False, indent=2)}")
        return info
    except Exception as e:
        print(f"获取委外加工服务费信息失败: {str(e)}")
        return None

def test_validate_supplier():
    """测试供应商验证"""
    print("=== 测试供应商验证 ===")
    
    # 测试一个存在的供应商（请根据实际情况修改）
    test_supplier = "DLZ"  # 根据实际供应商代码修改
    
    try:
        result = validate_subcontracting_supplier(test_supplier)
        print(f"供应商验证结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
    except Exception as e:
        print(f"供应商验证失败: {str(e)}")
        return None

def test_create_simple_subcontracting_po():
    """测试简单的委外加工服务费采购订单创建"""
    print("=== 测试简单的委外加工服务费采购订单创建 ===")
    
    # 测试数据
    test_data = {
        'supplier': 'DLZ',  # 根据实际供应商代码修改
        'qty': 10,
        'rate': 100.00,
        'description': '测试委外加工服务费'
    }
    
    try:
        result = create_subcontracting_service_po_simple(**test_data)
        print(f"简单采购订单创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
    except Exception as e:
        print(f"简单采购订单创建失败: {str(e)}")
        return None

def test_create_subcontracting_po_from_dict():
    """测试从字典创建委外加工服务费采购订单"""
    print("=== 测试从字典创建委外加工服务费采购订单 ===")
    
    # 测试数据
    test_data = {
        'supplier': 'DLZ',  # 根据实际供应商代码修改
        'qty': 5,
        'rate': 150.00,
        'description': '从字典创建的委外加工服务费',
        'project': 'TEST-PROJECT',  # 可选
        'cost_center': '主 - D'  # 可选
    }
    
    try:
        result = create_subcontracting_service_po_from_dict(test_data)
        print(f"字典采购订单创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
    except Exception as e:
        print(f"字典采购订单创建失败: {str(e)}")
        return None

def test_create_subcontracting_po_full():
    """测试完整的委外加工服务费采购订单创建"""
    print("=== 测试完整的委外加工服务费采购订单创建 ===")
    
    # 测试数据
    test_data = {
        'supplier': 'DLZ',  # 根据实际供应商代码修改
        'supplier_name': '测试供应商',
        'company': 'DTY',
        'transaction_date': '2025-01-15',
        'schedule_date': '2025-01-22',
        'qty': 8,
        'rate': 200.00,
        'description': '完整测试委外加工服务费',
        'warehouse': '仓库 - D',
        'cost_center': '主 - D',
        'project': 'TEST-PROJECT',
        'expense_account': '5403 - 机械作业 - D'
    }
    
    try:
        result = create_subcontracting_service_purchase_order(**test_data)
        print(f"完整采购订单创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
    except Exception as e:
        print(f"完整采购订单创建失败: {str(e)}")
        return None

def run_all_tests():
    """运行所有测试"""
    print("开始运行委外加工服务费采购订单测试...")
    print("=" * 50)
    
    # 测试1: 获取服务信息
    test_subcontracting_service_info()
    print()
    
    # 测试2: 验证供应商
    test_validate_supplier()
    print()
    
    # 测试3: 简单创建
    test_create_simple_subcontracting_po()
    print()
    
    # 测试4: 从字典创建
    test_create_subcontracting_po_from_dict()
    print()
    
    # 测试5: 完整创建
    test_create_subcontracting_po_full()
    print()
    
    print("=" * 50)
    print("所有测试完成")

if __name__ == "__main__":
    run_all_tests() 