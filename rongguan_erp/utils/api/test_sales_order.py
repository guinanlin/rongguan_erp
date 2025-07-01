import frappe
import json
import unittest
from rongguan_erp.utils.api.sales_order import save_sales_order
from pathlib import Path

# bench run-tests --module rongguan_erp.utils.api.test_sales_order
# 读取 JSON 文件
test_data_path = Path(__file__).parent / "test_sales_order2.json"
with open(test_data_path, "r", encoding="utf-8") as f:
    order_data = json.load(f)

class TestSalesOrder(unittest.TestCase):
    created_sales_orders = [] # 新增类变量用于存储创建的销售订单
    @classmethod
    def setUpClass(cls):
        """初始化 Frappe 环境（仅执行一次）"""
        frappe.init(site="site1.local")
        frappe.connect()

    @classmethod
    def tearDownClass(cls):
        """清理 Frappe 环境（仅执行一次）"""
        if frappe.local.site:
            for so_name in cls.created_sales_orders:
                if frappe.db.exists("Sales Order", so_name):
                    frappe.delete_doc("Sales Order", so_name, ignore_permissions=True)
                    print(f"✅ 清理销售订单成功: {so_name}")
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
        # 输出 result 的内容
        print("✅ 返回值 result:", result)
        # 从返回值的 "data" 字段中获取 name
        created_so_name = result["data"]["name"]
        self.assertTrue(frappe.db.exists("Sales Order", created_so_name))
        print("✅ 销售订单创建成功:", created_so_name)
        TestSalesOrder.created_sales_orders.append(created_so_name) # 记录创建的销售订单

    def test_get_sales_order_detail(self):
        """测试获取销售订单详情"""
        # 在获取详情前先创建一个销售订单
        self.order_data["name"] = self.generate_order_number()
        create_result = save_sales_order(self.order_data)
        self.assertTrue(create_result["data"]["success"])
        created_so_name = create_result["data"]["name"]
        TestSalesOrder.created_sales_orders.append(created_so_name) # 记录创建的销售订单

        # 调用 get_sales_order_detail 方法
        from rongguan_erp.utils.api.sales_order import get_sales_order_detail
        detail_result = get_sales_order_detail(created_so_name)
        
        # 验证返回结果
        self.assertTrue(detail_result["success"])
        self.assertEqual(detail_result["message"], "Success")
        self.assertIsNotNone(detail_result["data"])
        self.assertEqual(detail_result["data"]["name"], created_so_name) # 验证获取的订单号
        print(f"✅ 销售订单详情获取成功: {detail_result['data']['name']}")

    def test_get_style_and_items_by_sales_order(self):
        """测试通过销售订单号获取款式、款号及所有变体item"""
        # 先创建一个销售订单
        self.order_data["name"] = self.generate_order_number()
        create_result = save_sales_order(self.order_data)
        self.assertTrue(create_result["data"]["success"])
        created_so_name = create_result["data"]["name"]
        TestSalesOrder.created_sales_orders.append(created_so_name)

        # 导入白名单方法
        from rongguan_erp.utils.api.sales_order import get_style_and_items_by_sales_order
        result = get_style_and_items_by_sales_order(created_so_name)
        print("✅ get_style_and_items_by_sales_order 返回:", result)
        # 断言返回结构
        self.assertIn("custom_material_code_display", result)
        self.assertIn("custom_style_number", result)
        self.assertIn("items", result)
        self.assertIsInstance(result["items"], list)

    def test_print_specific_sales_order(self):
        from rongguan_erp.utils.api.sales_order import get_style_and_items_by_sales_order
        so_name = "SO-250629-48822-08"
        result = get_style_and_items_by_sales_order(so_name)
        print("指定销售订单号测试结果：", result)

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
    from rongguan_erp.utils.api.sales_order import get_style_and_items_by_sales_order
    so_name = "SO-250629-48822-08"
    result = get_style_and_items_by_sales_order(so_name)
    print("指定销售订单号测试结果：", result)
