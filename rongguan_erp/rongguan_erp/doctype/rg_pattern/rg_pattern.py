# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RGPattern(Document):
	def validate(self):
		"""验证字段逻辑"""
		self.validate_assignment()
	
	def validate_assignment(self):
		"""验证指派相关字段"""
		# 如果状态为 assigned，必须指定纸样师
		if self.assigned_status == "assigned" and not self.assigned_pattern_designer_id:
			frappe.throw("指派状态为'已指派'时，必须指定被指派的纸样师")
		
		# 如果状态为 unassigned，清空指派相关字段
		if self.assigned_status == "unassigned":
			self.assigned_pattern_designer_id = None
			self.assigned_pattern_designer_name = None
			self.assigned_at = None
			self.assigned_by = None
	
	def before_save(self):
		"""保存前处理"""
		# 检查指派状态是否改变
		if self.is_new():
			# 新记录，如果状态为 assigned，设置指派信息
			if self.assigned_status == "assigned" and self.assigned_pattern_designer_id:
				self.assigned_at = frappe.utils.now()
				self.assigned_by = frappe.session.user
		else:
			# 更新记录，检查状态是否从 unassigned 变为 assigned
			old_doc = self.get_doc_before_save()
			if old_doc:
				if old_doc.assigned_status == "unassigned" and self.assigned_status == "assigned":
					# 状态变为已指派，设置指派时间和操作人
					if self.assigned_pattern_designer_id:
						self.assigned_at = frappe.utils.now()
						self.assigned_by = frappe.session.user
				elif old_doc.assigned_status == "assigned" and self.assigned_status == "unassigned":
					# 状态变为未指派，清空指派信息
					self.assigned_pattern_designer_id = None
					self.assigned_pattern_designer_name = None
					self.assigned_at = None
					self.assigned_by = None
				elif old_doc.assigned_status == "assigned" and self.assigned_status == "assigned":
					# 如果纸样师改变，更新指派时间和操作人
					if old_doc.assigned_pattern_designer_id != self.assigned_pattern_designer_id:
						if self.assigned_pattern_designer_id:
							self.assigned_at = frappe.utils.now()
							self.assigned_by = frappe.session.user


@frappe.whitelist()
def update_pattern_assignment(pattern_name, pattern_maker_id=None, pattern_maker_name=None, paper_pattern_name=None):
	"""
	前端在纸样指派成功后调用，用于更新 RG Pattern 的指派状态。

	参数:
		pattern_name (str): RG Pattern 的 name，例如：SM-0001
		pattern_maker_id (str): 被指派的纸样师 Employee ID
		pattern_maker_name (str): 纸样师名称（可选）
		paper_pattern_name (str): 刚创建的 RG Paper Pattern.name（可选）
	"""
	if not pattern_name:
		frappe.throw("参数 pattern_name 不能为空")

	if not pattern_maker_id:
		frappe.throw("参数 pattern_maker_id 不能为空")

	# 获取样衣单
	doc = frappe.get_doc("RG Pattern", pattern_name)

	# 并发 / 重复指派检查：
	# - 如果已经是 assigned 且已有纸样师
	# - 且新的纸样师与旧的不同，则不允许直接覆盖
	if (
		doc.assigned_status == "assigned"
		and doc.assigned_pattern_designer_id
		and doc.assigned_pattern_designer_id != pattern_maker_id
	):
		frappe.throw(
			f"样衣 {pattern_name} 已指派给 "
			f"{doc.assigned_pattern_designer_name or doc.assigned_pattern_designer_id}，"
			"如需更换纸样师，请先在系统中取消指派后再操作。"
		)

	# 更新指派相关字段
	doc.assigned_status = "assigned"
	doc.assigned_pattern_designer_id = pattern_maker_id

	# 名称如果前端传了，就覆盖；不传则保留 ERPNext 通过 fetch_from 带出的名称
	if pattern_maker_name:
		doc.assigned_pattern_designer_name = pattern_maker_name

	doc.assigned_at = frappe.utils.now()
	doc.assigned_by = frappe.session.user

	if paper_pattern_name:
		doc.paper_pattern_name = paper_pattern_name

	# 保存文档，触发 validate / before_save 等钩子
	doc.save(ignore_permissions=True)

	return {
		"status": "success",
		"name": doc.name,
		"assigned_status": doc.assigned_status,
		"assigned_pattern_designer_id": doc.assigned_pattern_designer_id,
		"assigned_pattern_designer_name": doc.assigned_pattern_designer_name,
		"assigned_at": doc.assigned_at,
		"assigned_by": doc.assigned_by,
		"paper_pattern_name": doc.paper_pattern_name,
	}


@frappe.whitelist()
def get_sales_order_items_by_pattern(pattern_name):
	"""
	通过样衣单号获取对应销售订单的明细数据
	
	Args:
		pattern_name (str): 样衣单号
	
	Returns:
		list: 包含销售订单明细的列表，每个明细包含 item_name, bom_no, 颜色, 尺码等信息
	"""
	try:
		# 获取样衣记录
		pattern_doc = frappe.get_doc("RG Pattern", pattern_name)
		
		if not pattern_doc.sales_order:
			frappe.throw(f"样衣 {pattern_name} 没有关联销售订单")
		
		# 查询销售订单明细
		sales_order_items = frappe.db.sql("""
			SELECT 
				soi.item_code,
				soi.item_name,
				soi.bom_no,
				soi.qty,
				soi.rate,
				soi.amount,
				item.item_group,
				item.brand
			FROM `tabSales Order Item` soi
			LEFT JOIN `tabItem` item ON soi.item_code = item.name
			WHERE soi.parent = %s
			ORDER BY soi.idx
		""", (pattern_doc.sales_order,), as_dict=True)
		
		# 为每个item获取颜色和尺码信息
		result = []
		for item in sales_order_items:
			# 获取Item的变体属性信息
			item_variants = frappe.db.sql("""
				SELECT 
					iva.attribute,
					iva.attribute_value,
					ia._user_tags
				FROM `tabItem Variant Attribute` iva
				LEFT JOIN `tabItem Attribute` ia ON iva.attribute = ia.name
				WHERE iva.parent = %s
				AND (ia._user_tags LIKE %s OR ia._user_tags LIKE %s)
			""", (item.item_code, '%颜色%', '%尺寸%'), as_dict=True)
			
			# 处理属性信息
			color = ""
			size = ""
			for variant in item_variants:
				if variant._user_tags and '颜色' in variant._user_tags:
					color = variant.attribute_value
				elif variant._user_tags and '尺寸' in variant._user_tags:
					size = variant.attribute_value
			
			# 获取工单号 - 单独的事务处理
			work_order = ""
			try:
				work_order_result = frappe.db.sql("""
					SELECT wo.name as work_order
					FROM `tabWork Order` wo
					WHERE wo.sales_order = %s 
					AND wo.production_item = %s
					ORDER BY wo.creation DESC
					LIMIT 1
				""", (pattern_doc.sales_order, item.item_code), as_dict=True)
				
				if work_order_result:
					work_order = work_order_result[0].work_order
			except Exception as e:
				# 如果获取工单号失败，记录日志但不影响主流程
				frappe.log_error(f"获取工单号失败 - 销售订单: {pattern_doc.sales_order}, 物料: {item.item_code}, 错误: {str(e)}")
			
			# 构建返回数据
			item_data = {
				'item_code': item.item_code,
				'item_name': item.item_name,
				'bom_no': item.bom_no,
				'qty': item.qty,
				'rate': item.rate,
				'amount': item.amount,
				'item_group': item.item_group,
				'brand': item.brand,
				'color': color,
				'size': size,
				'work_order': work_order
			}
			result.append(item_data)
		
		return result
		
	except Exception as e:
		frappe.log_error(f"获取销售订单明细失败: {str(e)}")
		frappe.throw(f"获取销售订单明细失败: {str(e)}")
