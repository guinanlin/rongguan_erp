import frappe
import json
import unittest
from rongguan_erp.utils.api.sales_order import save_sales_order
from pathlib import Path

# bench run-tests --module rongguan_erp.utils.api.test_sales_order
# bench run-tests --module rongguan_erp.utils.api.test_sales_order --site site1.local

# 读取 JSON 文件
test_data_path = Path(__file__).parent / "test_sales_order.json"
with open(test_data_path, "r", encoding="utf-8") as f:
    order_data = json.load(f)

class TestSalesOrder(unittest.TestCase):
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
        self.order_data = order_data  # 直接使用 JSON 数据

    def generate_order_number(self):
        """生成随机订单号"""
        import time
        import random
        now = time.localtime()
        year = str(now.tm_year)[-2:]
        month = str(now.tm_mon).zfill(2)
        day = str(now.tm_mday).zfill(2)
        seconds = (time.time() % 86400)
        padded_seconds = str(int(seconds)).zfill(5)
        random_num = str(random.randint(0, 99)).zfill(2)
        return f"SO-{year}{month}{day}-{padded_seconds}-{random_num}"

    def test_save_sales_order(self):
        """测试销售订单创建"""
        self.order_data["name"] = self.generate_order_number()
        result = save_sales_order(self.order_data)
        self.assertTrue(frappe.db.exists("Sales Order", result.get("name")))
        print("✅ 销售订单创建成功:", result)

    # def test_invalid_input(self):
    #     """测试无效输入"""
    #     with self.assertRaises(frappe.ValidationError):
    #         save_sales_order({"invalid": "data"})

    # def test_template_configuration(self):
    #     """测试模板商品配置"""
    #     template = frappe.get_doc("Item", "25-054")
    #     print(f"模板配置: has_variants={template.has_variants}, stock_uom={template.stock_uom}")
        
    #     # 检查属性值是否合法
    #     for attr in template.attributes:
    #         if attr.attribute == "XSD专属定义颜色":
    #             print(f"有效颜色值: {frappe.get_all('Item Attribute Value', filters={'parent': attr.attribute}, pluck='attribute_value')}")
    #         if attr.attribute == "荣冠尺码":
    #             print(f"有效尺码值: {frappe.get_all('Item Attribute Value', filters={'parent': attr.attribute}, pluck='attribute_value')}")

    #     # 强制更新属性值（如果需要）
    #     valid_colors = ["大金", "粉粉"]
    #     valid_sizes = ["32#", "34#", "36#"]
    #     for attr in template.attributes:
    #         if attr.attribute == "XSD专属定义颜色" and attr.attribute_value not in valid_colors:
    #             attr.attribute_value = "粉粉"
    #         if attr.attribute == "荣冠尺码" and attr.attribute_value not in valid_sizes:
    #             attr.attribute_value = "32#"
    #     template.save()

if __name__ == "__main__":
    unittest.main()
