#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
委外加工服务费采购订单使用示例
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

def example_1_simple_creation():
    """
    示例1: 最简单的委外加工服务费采购订单创建
    只需要提供供应商、数量和单价
    """
    print("=== 示例1: 简单创建 ===")
    
    result = create_subcontracting_service_po_simple(
        supplier="DLZ",  # 供应商代码
        qty=10,          # 数量
        rate=100.00      # 单价
    )
    
    print(f"创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

def example_2_with_description():
    """
    示例2: 带描述的委外加工服务费采购订单创建
    """
    print("=== 示例2: 带描述创建 ===")
    
    result = create_subcontracting_service_po_simple(
        supplier="DLZ",
        qty=5,
        rate=150.00,
        description="服装裁剪加工服务费"
    )
    
    print(f"创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

def example_3_full_parameters():
    """
    示例3: 使用完整参数的委外加工服务费采购订单创建
    """
    print("=== 示例3: 完整参数创建 ===")
    
    result = create_subcontracting_service_purchase_order(
        supplier="DLZ",
        supplier_name="大连制衣厂",
        company="DTY",
        transaction_date="2025-01-15",
        schedule_date="2025-01-22",
        qty=20,
        rate=80.00,
        description="批量服装加工服务费",
        warehouse="仓库 - D",
        cost_center="主 - D",
        project="2025春季服装项目",
        expense_account="5403 - 机械作业 - D"
    )
    
    print(f"创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

def example_4_from_dict():
    """
    示例4: 从字典数据创建委外加工服务费采购订单
    """
    print("=== 示例4: 从字典创建 ===")
    
    # 准备数据字典
    po_data = {
        "supplier": "DLZ",
        "qty": 15,
        "rate": 120.00,
        "description": "高级定制服装加工费",
        "project": "VIP客户定制项目",
        "cost_center": "主 - D",
        "warehouse": "仓库 - D"
    }
    
    result = create_subcontracting_service_po_from_dict(po_data)
    
    print(f"创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

def example_5_supplier_validation():
    """
    示例5: 供应商验证
    """
    print("=== 示例5: 供应商验证 ===")
    
    # 验证供应商
    validation_result = validate_subcontracting_supplier("DLZ")
    print(f"供应商验证结果: {json.dumps(validation_result, ensure_ascii=False, indent=2)}")
    
    if validation_result.get("valid"):
        print("供应商验证通过，可以创建采购订单")
        # 创建采购订单
        result = create_subcontracting_service_po_simple(
            supplier="DLZ",
            qty=8,
            rate=90.00,
            description="验证后的委外加工服务费"
        )
        print(f"采购订单创建结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
    else:
        print(f"供应商验证失败: {validation_result.get('message')}")
        return None

def example_6_get_service_info():
    """
    示例6: 获取委外加工服务费标准信息
    """
    print("=== 示例6: 获取服务信息 ===")
    
    service_info = get_subcontracting_service_info()
    print(f"委外加工服务费标准信息: {json.dumps(service_info, ensure_ascii=False, indent=2)}")
    
    # 使用标准信息创建采购订单
    result = create_subcontracting_service_po_simple(
        supplier="DLZ",
        qty=12,
        rate=110.00,
        description=service_info.get("description", "委外加工服务费")
    )
    
    print(f"使用标准信息创建的采购订单: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

def example_7_batch_creation():
    """
    示例7: 批量创建委外加工服务费采购订单
    """
    print("=== 示例7: 批量创建 ===")
    
    # 批量数据
    batch_data = [
        {"supplier": "DLZ", "qty": 10, "rate": 100.00, "description": "批次1-基础加工"},
        {"supplier": "DLZ", "qty": 15, "rate": 120.00, "description": "批次2-精细加工"},
        {"supplier": "DLZ", "qty": 8, "rate": 150.00, "description": "批次3-特殊工艺"}
    ]
    
    results = []
    for i, data in enumerate(batch_data, 1):
        print(f"创建第{i}个采购订单...")
        result = create_subcontracting_service_po_simple(**data)
        results.append(result)
        print(f"第{i}个采购订单结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return results

def example_8_error_handling():
    """
    示例8: 错误处理示例
    """
    print("=== 示例8: 错误处理 ===")
    
    # 测试缺少必需参数的情况
    try:
        result = create_subcontracting_service_po_simple(
            supplier="DLZ",
            # 缺少 qty 和 rate
        )
        print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"预期错误: {str(e)}")
    
    # 测试无效供应商的情况
    try:
        result = create_subcontracting_service_po_simple(
            supplier="INVALID_SUPPLIER",
            qty=10,
            rate=100.00
        )
        print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"预期错误: {str(e)}")

def run_all_examples():
    """
    运行所有示例
    """
    print("开始运行委外加工服务费采购订单使用示例...")
    print("=" * 60)
    
    examples = [
        ("示例1: 简单创建", example_1_simple_creation),
        ("示例2: 带描述创建", example_2_with_description),
        ("示例3: 完整参数创建", example_3_full_parameters),
        ("示例4: 从字典创建", example_4_from_dict),
        ("示例5: 供应商验证", example_5_supplier_validation),
        ("示例6: 获取服务信息", example_6_get_service_info),
        ("示例7: 批量创建", example_7_batch_creation),
        ("示例8: 错误处理", example_8_error_handling)
    ]
    
    for name, func in examples:
        print(f"\n{name}")
        print("-" * 40)
        try:
            func()
        except Exception as e:
            print(f"示例执行失败: {str(e)}")
        print()
    
    print("=" * 60)
    print("所有示例执行完成")

if __name__ == "__main__":
    run_all_examples() 