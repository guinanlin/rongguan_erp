# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


def resolve_customer_name_display(customer_value: str | None) -> str:
	"""当 customer 存的是 Customer.name 时，同步 Customer.customer_name 供列表模糊搜索。"""
	if not customer_value:
		return ""
	stripped = (customer_value or "").strip()
	if not stripped:
		return ""
	if frappe.db.exists("Customer", stripped):
		return frappe.db.get_value("Customer", stripped, "customer_name") or ""
	return ""


class RGProductionProgress(Document):
	def validate(self):
		self.customer_name_display = resolve_customer_name_display(self.customer)
