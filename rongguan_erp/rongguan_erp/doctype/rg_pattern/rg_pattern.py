# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RGPattern(Document):
	pass


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
