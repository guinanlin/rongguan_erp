# Copyright (c) 2025, guinan.lin@foxmail.com and Contributors
# See license.txt

import frappe
import json
import unittest
import time
from frappe.tests.utils import FrappeTestCase
from pathlib import Path
from rongguan_erp.rongguan_erp.doctype.rg_production_orders.rg_production_orders import saveRGProductionOrder

# bench run-tests --module rongguan_erp.rongguan_erp.doctype.rg_production_orders.test_rg_production_orders

# 读取 JSON 文件
test_data_path = Path(__file__).parent / "test_rg_production_orders.json"
with open(test_data_path, "r", encoding="utf-8") as f:
    production_order_data = json.load(f)

class TestRGProductionOrders(FrappeTestCase):
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
		self.production_order_data = production_order_data.copy()
		self.production_order_data["orderNumber"] = self.generate_unique_order_number()  # 动态生成唯一订单号

	def generate_unique_order_number(self):
		"""生成唯一的订单号（基于时间戳）"""
		return f"SO-TEST-{int(time.time())}"

	def test_save_生产制造工单(self):
		"""测试生产制造工单创建"""
		result = saveRGProductionOrder(self.production_order_data)
		print("✅ 返回值 result:", result)
		self.assertTrue(frappe.db.exists("RG Production Orders", result["name"]))
		print("✅ 生产制造工单创建成功:", result["name"])

	# 可以添加更多测试方法来测试不同的场景，例如：
	# - 测试不包含子表数据的文档
	# - 测试包含附件的文档
	# - 测试导入成品物料的逻辑 (可能需要mock bulk_add_items_from_data)
	# def test_save_without_items(self):
	#     pass

# if __name__ == "__main__":
# 	unittest.main()
