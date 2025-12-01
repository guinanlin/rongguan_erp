# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RGPaperPattern(Document):
	def validate(self):
		"""验证销售单号和样衣编号的组合唯一性"""
		if self.sales_order and self.pattern_number:
			# 构建查询条件
			filters = {
				"sales_order": self.sales_order,
				"pattern_number": self.pattern_number,
			}
			
			# 如果是更新操作，排除当前文档
			if self.name and not self.get("__islocal"):
				filters["name"] = ["!=", self.name]
			
			# 查询是否存在相同的组合
			existing = frappe.db.exists("RG Paper Pattern", filters)
			
			if existing:
				frappe.throw(
					f"此销售单号 {frappe.bold(self.sales_order)} 和此样衣编号 {frappe.bold(self.pattern_number)} 已经存在",
					title="重复记录"
				)
