import frappe
import json
import unittest
from rongguan_erp.utils.api.items import get_item_color_values
from pathlib import Path

# bench run-tests --module rongguan_erp.utils.api.test_items

# 读取 JSON 文件
test_data_path = Path(__file__).parent / "test_items.json"
with open(test_data_path, "r", encoding="utf-8") as f:
    item_data = json.load(f)

class TestItems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """初始化 Frappe 环境（仅执行一次）"""
        frappe.init(site="site1.local")
        frappe.connect()

    @classmethod
    def tearDownClass(cls):
        """清理 Frappe 环境（仅执行一次）"""
        if frappe.local.site:
            frappe.destroy()
            frappe.init(site="site1.local")  # 重新初始化以避免缓存错误

    def setUp(self):
        """每个测试方法前的初始化"""
        self.item_data = item_data  # 直接使用 JSON 数据

    def test_get_item_color_values(self):
        """测试获取物料的颜色属性值"""
        item_code = self.item_data.get("item_code")
        result = get_item_color_values(item_code)
        self.assertIsInstance(result, dict)
        self.assertIn("color_attributes", result)
        print("✅ 颜色属性值获取成功:", result)

if __name__ == "__main__":
    unittest.main()
