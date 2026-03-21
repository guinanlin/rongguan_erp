# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""为历史数据填充 customer_name_display（与 validate 中逻辑一致：按 Customer.name 关联取 customer_name）。"""
	frappe.db.sql(
		"""
		UPDATE `tabRG Production Progress` p
		LEFT JOIN `tabCustomer` c ON c.name = p.customer
		SET p.customer_name_display = IFNULL(c.customer_name, '')
		"""
	)
