# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class W70SampleSalesBase(Document):
	def validate(self):
		"""验证和计算字段"""
		# 计算金额（数量 × 单价）
		if self.quantity and self.unit_price:
			self.amount = self.quantity * self.unit_price
		
		# 计算毛利：金额 - 各项费用总和
		self.calculate_gross_profit()
	
	def calculate_gross_profit(self):
		"""计算毛利：金额 - 各项费用总和"""
		if not self.amount:
			self.gross_profit = 0
			return
		
		total_costs = 0
		cost_fields = [
			'freight_cost',      # 货代费用
			'fabric_cost',       # 面料费用
			'accessory_cost',    # 辅料费用
			'pattern_cost',      # 纸样费
			'production_cost',   # 生产费用
			'logistics_cost',    # 物流费用
			'management_cost',   # 管理费用
			'other_cost'         # 其他费用
		]
		
		for field in cost_fields:
			if self.get(field):
				total_costs += float(self.get(field))
		
		self.gross_profit = self.amount - total_costs
