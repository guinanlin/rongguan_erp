# Copyright (c) 2025, Rongguan ERP and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import unittest
from erpnext.stock.doctype.stock_entry.stock_entry import get_warehouse_details


class TestWarehouseDetails(unittest.TestCase):
    """测试 Stock Entry 的 get_warehouse_details 方法"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.test_item_code = "RED布料-red"
        self.test_warehouse = "仓库 - DM"
        self.test_company = "DMY"
    
    def test_get_warehouse_details_basic(self):
        """测试基本的 get_warehouse_details 功能"""
        print("\n=== 测试 get_warehouse_details 基本功能 ===")
        
        # 测试参数
        test_args = {
            "item_code": self.test_item_code,
            "warehouse": self.test_warehouse,
            "posting_date": "2025-01-15",
            "posting_time": "10:00:00",
            "company": self.test_company,
            "voucher_type": "Stock Entry",
            "voucher_no": "test-001"
        }
        
        print(f"料号: {test_args['item_code']}")
        print(f"仓库: {test_args['warehouse']}")
        print(f"日期: {test_args['posting_date']}")
        print(f"时间: {test_args['posting_time']}")
        
        try:
            # 调用 get_warehouse_details 方法
            result = get_warehouse_details(test_args)
            
            print("\n=== 返回结果 ===")
            print(f"actual_qty: {result.get('actual_qty', 0)}")
            print(f"basic_rate: {result.get('basic_rate', 0)}")
            
            # 验证结果
            self.assertIsNotNone(result, "返回结果不应为空")
            self.assertIn('actual_qty', result, "返回结果应包含 actual_qty 字段")
            self.assertIn('basic_rate', result, "返回结果应包含 basic_rate 字段")
            
            print(f"\n✓ 成功获取实际数量: {result['actual_qty']}")
            print(f"✓ 成功获取基本价格: {result['basic_rate']}")
            
        except Exception as e:
            print(f"✗ 调用失败: {str(e)}")
            self.fail(f"get_warehouse_details 调用失败: {str(e)}")
    
    def test_get_warehouse_details_different_warehouses(self):
        """测试不同仓库的库存情况"""
        print("\n=== 测试不同仓库的库存情况 ===")
        
        test_warehouses = ["仓库 - DM", "仓库 - D"]
        
        for warehouse in test_warehouses:
            test_args = {
                "item_code": self.test_item_code,
                "warehouse": warehouse,
                "posting_date": "2025-01-15",
                "posting_time": "10:00:00",
                "company": self.test_company,
                "voucher_type": "Stock Entry",
                "voucher_no": "test-001"
            }
            
            try:
                result = get_warehouse_details(test_args)
                actual_qty = result.get('actual_qty', 0)
                print(f"仓库 {warehouse}: actual_qty = {actual_qty}")
                
                # 验证结果
                self.assertIsInstance(actual_qty, (int, float), f"仓库 {warehouse} 的 actual_qty 应该是数字")
                
            except Exception as e:
                print(f"仓库 {warehouse}: 错误 - {str(e)}")
                self.fail(f"仓库 {warehouse} 测试失败: {str(e)}")
    
    def test_get_warehouse_details_different_times(self):
        """测试不同时间点的库存情况"""
        print("\n=== 测试不同时间点的库存情况 ===")
        
        test_times = [
            ("2025-01-15", "10:00:00"),
            ("2025-09-14", "17:30:00"),  # 在库存变动之前
            ("2025-09-14", "17:40:00"),  # 在库存变动之后
        ]
        
        for date, time in test_times:
            test_args = {
                "item_code": self.test_item_code,
                "warehouse": self.test_warehouse,
                "posting_date": date,
                "posting_time": time,
                "company": self.test_company,
                "voucher_type": "Stock Entry",
                "voucher_no": "test-001"
            }
            
            try:
                result = get_warehouse_details(test_args)
                actual_qty = result.get('actual_qty', 0)
                print(f"时间 {date} {time}: actual_qty = {actual_qty}")
                
                # 验证结果
                self.assertIsInstance(actual_qty, (int, float), f"时间 {date} {time} 的 actual_qty 应该是数字")
                
            except Exception as e:
                print(f"时间 {date} {time}: 错误 - {str(e)}")
                self.fail(f"时间 {date} {time} 测试失败: {str(e)}")
    
    def test_get_warehouse_details_edge_cases(self):
        """测试边界情况"""
        print("\n=== 测试边界情况 ===")
        
        # 测试不存在的料号
        test_args = {
            "item_code": "不存在的料号",
            "warehouse": self.test_warehouse,
            "posting_date": "2025-01-15",
            "posting_time": "10:00:00",
            "company": self.test_company,
            "voucher_type": "Stock Entry",
            "voucher_no": "test-001"
        }
        
        try:
            result = get_warehouse_details(test_args)
            actual_qty = result.get('actual_qty', 0)
            print(f"不存在料号: actual_qty = {actual_qty}")
            
            # 不存在的料号应该返回 0 或 None
            self.assertTrue(actual_qty == 0 or actual_qty is None, "不存在料号应返回 0 或 None")
            
        except Exception as e:
            print(f"不存在料号测试: 错误 - {str(e)}")
            # 对于不存在的料号，可能会抛出异常，这是可以接受的
        
        # 测试不存在的仓库
        test_args = {
            "item_code": self.test_item_code,
            "warehouse": "不存在的仓库",
            "posting_date": "2025-01-15",
            "posting_time": "10:00:00",
            "company": self.test_company,
            "voucher_type": "Stock Entry",
            "voucher_no": "test-001"
        }
        
        try:
            result = get_warehouse_details(test_args)
            actual_qty = result.get('actual_qty', 0)
            print(f"不存在仓库: actual_qty = {actual_qty}")
            
            # 不存在的仓库应该返回 0 或 None
            self.assertTrue(actual_qty == 0 or actual_qty is None, "不存在仓库应返回 0 或 None")
            
        except Exception as e:
            print(f"不存在仓库测试: 错误 - {str(e)}")
            # 对于不存在的仓库，可能会抛出异常，这是可以接受的

# bench execute rongguan_erp.tests.test_warehouse_details.test_warehouse_details_manual
def test_warehouse_details_manual():
    """手动测试函数，可以直接调用"""
    print("=== 手动测试 get_warehouse_details 方法 ===")
    
    # 测试参数 - 基于实际数据
    test_args = {
        "item_code": "RED布料-red",
        "warehouse": "仓库 - DM",
        "posting_date": "2025-09-15",  
        "posting_time": "00:47:00",    
        "company": "DMY",          
        "voucher_type": "Stock Entry",
        "voucher_no": "MAT-STE-2025-00003"  
    }
    
    print(f"料号: {test_args['item_code']}")
    print(f"仓库: {test_args['warehouse']}")
    print(f"日期: {test_args['posting_date']}")
    print(f"时间: {test_args['posting_time']}")
    print()
    
    try:
        # 调用 get_warehouse_details 方法
        result = get_warehouse_details(test_args)
        
        print("=== 返回结果 ===")
        print(f"actual_qty: {result.get('actual_qty', 0)}")
        print(f"basic_rate: {result.get('basic_rate', 0)}")
        print()
        
        # 验证结果
        if result.get('actual_qty') is not None:
            print(f"✓ 成功获取实际数量: {result['actual_qty']}")
        else:
            print("✗ 未能获取实际数量")
            
        if result.get('basic_rate') is not None:
            print(f"✓ 成功获取基本价格: {result['basic_rate']}")
        else:
            print("✗ 未能获取基本价格")
            
        return result
        
    except Exception as e:
        print(f"✗ 调用失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 如果直接运行此文件，执行手动测试
    test_warehouse_details_manual()
