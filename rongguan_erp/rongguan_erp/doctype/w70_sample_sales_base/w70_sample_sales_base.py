# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
import re
from frappe.model.document import Document


def parse_currency_value(value):
	"""
	解析货币字符串，去除货币符号并转换为浮点数
	支持格式：$0.00, ￥100.00, ¥100.00, 100.00, 等
	
	Args:
		value: 可以是字符串（带货币符号）或数字
		
	Returns:
		float: 解析后的数值，如果无法解析则返回 None
	"""
	if value is None:
		return None
	
	# 如果已经是数字类型，直接返回
	if isinstance(value, (int, float)):
		return float(value)
	
	# 如果是字符串，尝试解析
	if isinstance(value, str):
		# 去除前后空格
		value = value.strip()
		
		# 如果为空字符串，返回 None
		if not value:
			return None
		
		# 去除常见的货币符号：$, ￥, ¥, €, £, 等
		# 同时去除千位分隔符（逗号）
		value = re.sub(r'[$\￥¥€£,\s]', '', value)
		
		# 尝试转换为浮点数
		try:
			return float(value)
		except (ValueError, TypeError):
			# 如果转换失败，尝试提取数字部分
			# 匹配数字（包括小数点和负号）
			match = re.search(r'-?\d+\.?\d*', value)
			if match:
				try:
					return float(match.group())
				except (ValueError, TypeError):
					pass
			return None
	
	return None


class W70SampleSalesBase(Document):
	def validate(self):
		"""验证和计算字段"""
		# 清理所有货币字段，去除货币符号
		self.clean_currency_fields()
		
		# 计算金额（数量 × 单价）
		if self.quantity and self.unit_price:
			self.amount = self.quantity * self.unit_price
		
		# 计算总成本
		self.calculate_total_cost()
		
		# 计算毛利：金额 - 总成本
		self.calculate_gross_profit()
	
	def clean_currency_fields(self):
		"""清理所有货币字段，将带货币符号的字符串转换为数值"""
		currency_fields = [
			'unit_price',              # 单价
			'amount',                   # 金额
			'receivable_amount_usd',    # 应收美金货款
			'receivable_amount_cny',    # 应收人民币货款
			'received_amount',          # 实收货款
			'freight_cost',            # 货代费用
			'fabric_lining_cost',       # 面里料费用
			'accessory_cost',           # 辅料费用
			'pattern_cost',             # 纸样费
			'special_process_cost',     # 特殊工艺费用
			'production_cost',          # 生产费用
			'logistics_cost',           # 物流费用
			'management_cost',          # 管理费用
			'other_cost',               # 其他费用
			'total_cost',               # 总成本费用
			'gross_profit'              # 毛利
		]
		
		for field in currency_fields:
			value = self.get(field)
			if value is not None:
				parsed_value = parse_currency_value(value)
				if parsed_value is not None:
					self.set(field, parsed_value)
	
	def calculate_total_cost(self):
		"""计算总成本费用：所有费用字段的总和"""
		total_costs = 0
		cost_fields = [
			'freight_cost',          # 货代费用
			'fabric_lining_cost',     # 面里料费用
			'accessory_cost',         # 辅料费用
			'pattern_cost',           # 纸样费
			'special_process_cost',   # 特殊工艺费用
			'production_cost',        # 生产费用
			'logistics_cost',         # 物流费用
			'management_cost',        # 管理费用
			'other_cost'              # 其他费用
		]
		
		for field in cost_fields:
			value = self.get(field)
			if value is not None:
				parsed_value = parse_currency_value(value)
				if parsed_value is not None:
					total_costs += parsed_value
		
		self.total_cost = total_costs
	
	def calculate_gross_profit(self):
		"""计算毛利：金额 - 总成本费用"""
		if not self.amount:
			self.gross_profit = 0
			return
		
		# 使用 total_cost 计算毛利
		total_costs = self.total_cost or 0
		self.gross_profit = self.amount - total_costs
