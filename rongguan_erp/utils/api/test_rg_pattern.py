import frappe
import json
import unittest
from pathlib import Path

from rongguan_erp.utils.api.sales_order import save_to_rg_pattern

# bench run-tests --module rongguan_erp.utils.api.test_rg_pattern

# 读取 JSON 文件
test_data_path = Path(__file__).parent / "test_rg_pattern.json"
with open(test_data_path, "r", encoding="utf-8") as f:
    pattern_data_from_file = json.load(f)

class TestRGPattern(unittest.TestCase):
    created_rg_patterns = [] # 类变量用于存储创建的 RG Pattern 文档名称

    @classmethod
    def setUpClass(cls):
        """初始化 Frappe 环境（仅执行一次）"""
        frappe.init(site="site1.local")
        frappe.connect()

    @classmethod
    def tearDownClass(cls):
        """清理 Frappe 环境（仅执行一次）"""
        if frappe.local.site:
            for pattern_name in cls.created_rg_patterns:
                if frappe.db.exists("RG Pattern", pattern_name):
                    frappe.delete_doc("RG Pattern", pattern_name, ignore_permissions=True)
                    print(f"✅ 清理 RG Pattern 成功: {pattern_name}")
            frappe.destroy()
            frappe.init(site="site1.local")  # 重新初始化以避免缓存错误

    def setUp(self):
        """每个测试方法前的初始化"""
        # 深度复制一份数据，以防测试方法修改它
        self.pattern_data = pattern_data_from_file.copy()

    def generate_style_no(self):
        """生成随机款号，确保唯一性"""
        import time
        import random
        return f"TEST-STYLE-{int(time.time() * 1000)}-{random.randint(0, 999)}"

    def test_save_to_rg_pattern(self):
        """测试 RG Pattern 文档的创建"""
        # 使用唯一的款号来避免重复键错误
        self.pattern_data["style_no"] = self.generate_style_no()

        result = save_to_rg_pattern(self.pattern_data)

        # 打印返回结果以便调试
        print("✅ save_to_rg_pattern 返回值:", result)

        # 验证返回结果是否成功
        self.assertTrue(result.get("data") and result["data"].get("success"), f"RG Pattern 创建失败: {result.get('error')}")
        
        created_pattern_name = result["data"]["name"]
        self.assertTrue(frappe.db.exists("RG Pattern", created_pattern_name), "RG Pattern 文档未在数据库中创建")
        self.assertEqual(created_pattern_name, result["data"]["name"], "返回的名称与创建的文档名称不匹配")
        print(f"✅ RG Pattern 文档创建成功: {created_pattern_name}")
        TestRGPattern.created_rg_patterns.append(created_pattern_name) # 记录创建的文档

if __name__ == "__main__":
    unittest.main() 