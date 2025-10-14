# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class RgCostCalculations(Document):
	def before_insert(self):
		"""插入前的处理"""
		# 生成业务主键
		if not self.business_key:
			self.business_key = self.generate_business_key()
		
		# 设置版本号
		if not self.version_no:
			self.version_no = 1
		
		# 设置为最新版本
		if not hasattr(self, 'is_latest_version'):
			self.is_latest_version = 1
		
		# 设置制表人
		if not self.creator:
			self.creator = frappe.session.user
	
	def validate(self):
		"""验证数据"""
		# 确保业务主键存在
		if not self.business_key:
			self.business_key = self.generate_business_key()
		
		# 计算汇总成本
		self.calculate_costs()
	
	def before_save(self):
		"""保存前处理"""
		# 重新计算汇总
		self.calculate_costs()
	
	def generate_business_key(self):
		"""生成业务主键: 客户-款号"""
		if self.customer and self.style_number:
			return f"{self.customer}-{self.style_number}"
		elif self.style_number:
			return self.style_number
		return ""
	
	def calculate_costs(self):
		"""计算各项成本汇总"""
		# 面料成本
		fabric_cost = 0
		if hasattr(self, 'fabric_items') and self.fabric_items:
			for item in self.fabric_items:
				if item.amount:
					fabric_cost += item.amount
		self.fabric_cost = fabric_cost
		
		# 辅料成本
		accessory_cost = 0
		if hasattr(self, 'accessory_items') and self.accessory_items:
			for item in self.accessory_items:
				if item.amount:
					accessory_cost += item.amount
		self.accessory_cost = accessory_cost
		
		# 特殊工艺成本
		process_cost = 0
		if hasattr(self, 'process_items') and self.process_items:
			for item in self.process_items:
				if item.amount:
					process_cost += item.amount
		self.process_cost = process_cost
		
		# 生产其他成本
		production_cost = 0
		if hasattr(self, 'production_items') and self.production_items:
			for item in self.production_items:
				if item.amount:
					production_cost += item.amount
		self.production_cost = production_cost
		
		# 生产总成本
		self.total_production_cost = (
			self.fabric_cost + 
			self.accessory_cost + 
			self.process_cost + 
			self.production_cost
		)
		
		# 利润金额
		profit_percentage = self.profit_percentage or 15
		self.profit_amount = self.total_production_cost * profit_percentage / 100
		
		# FOB价格
		self.fob_price = self.total_production_cost + self.profit_amount
	
	@frappe.whitelist()
	def create_new_version(self, version_remark=None):
		"""创建新版本"""
		# 查询当前业务主键的最大版本号
		max_version = frappe.db.sql("""
			SELECT MAX(version_no) as max_version
			FROM `tabRg Cost Calculations`
			WHERE business_key = %s
		""", (self.business_key,), as_dict=True)
		
		new_version_no = (max_version[0].get('max_version') or 0) + 1
		
		# 复制当前文档
		new_doc = frappe.copy_doc(self)
		new_doc.version_no = new_version_no
		new_doc.is_latest_version = 1
		new_doc.parent_version_id = self.name
		new_doc.version_remark = version_remark or f"从版本 {self.version_no} 复制"
		new_doc.status = "draft"
		new_doc.docstatus = 0
		
		# 保存新版本
		new_doc.insert()
		
		# 更新当前版本为非最新
		frappe.db.set_value("Rg Cost Calculations", self.name, "is_latest_version", 0)
		
		frappe.msgprint(_("已创建新版本 {0}").format(new_version_no))
		
		return new_doc.name
	
	@frappe.whitelist()
	def submit_for_approval(self):
		"""提交审核"""
		if self.status == "draft":
			self.status = "pending"
			self.save()
			frappe.msgprint(_("已提交审核"))
		else:
			frappe.throw(_("只有草稿状态才能提交审核"))
	
	@frappe.whitelist()
	def approve(self):
		"""审批通过"""
		if self.status == "pending":
			self.status = "approved"
			self.approver = frappe.session.user
			self.save()
			frappe.msgprint(_("已批准"))
		else:
			frappe.throw(_("只有待审核状态才能批准"))
	
	@frappe.whitelist()
	def reject(self, reason=None):
		"""审批拒绝"""
		if self.status == "pending":
			self.status = "rejected"
			if reason:
				self.version_remark = reason
			self.save()
			frappe.msgprint(_("已拒绝"))
		else:
			frappe.throw(_("只有待审核状态才能拒绝"))
