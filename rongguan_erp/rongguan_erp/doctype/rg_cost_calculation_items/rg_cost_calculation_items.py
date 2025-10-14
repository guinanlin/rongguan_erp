# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RgCostCalculationItems(Document):
	def validate(self):
		"""验证并计算字段"""
		self.calculate_consumption_and_amount()
	
	def calculate_consumption_and_amount(self):
		"""计算总耗和金额"""
		# 对于面料、辅料、工艺：计算总耗和金额
		if self.item_type in ['fabric', 'accessory', 'process']:
			# 计算总耗 = 净耗 × (1 + 损耗率/100)
			if self.net_consumption and self.loss_rate is not None:
				self.total_consumption = self.net_consumption * (1 + self.loss_rate / 100)
			elif self.net_consumption:
				self.total_consumption = self.net_consumption
			
			# 计算金额 = 含税单价 × 总耗
			if self.unit_price and self.total_consumption:
				self.amount = self.unit_price * self.total_consumption
		
		# 对于生产成本：直接计算金额
		elif self.item_type == 'production':
			# 计算金额 = 含税单价 × 数量
			if self.unit_price and self.quantity:
				self.amount = self.unit_price * self.quantity
			# 如果有损耗率，也应用到金额上
			elif self.unit_price:
				base_amount = self.unit_price
				if self.loss_rate:
					self.amount = base_amount * (1 + self.loss_rate / 100)
				else:
					self.amount = base_amount
