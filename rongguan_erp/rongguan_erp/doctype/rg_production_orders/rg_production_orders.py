# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_rendered_template


class RGProductionOrders(Document):
	pass

@frappe.whitelist()
def make_from_sales_order(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.qty = obj.qty - obj.delivered_qty
		target.sales_order = obj.parent
		target.sales_order_item = obj.name

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "RG Production Orders",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map": {
				"customer": "customer",
				"delivery_date": "delivery_date",
				"company": "company",
				"name": "order_number",
			}
		},
		# "Sales Order Item": {
		# 	"doctype": "RG Production Orders Item",
		# 	"field_map": {
		# 		"item_code": "item_code",
		# 		"item_name": "item_name",
		# 		"description": "description",
		# 		"uom": "uom"
		# 	},
		# 	"postprocess": update_item
		# }
	}, target_doc)

	return doc

@frappe.whitelist()
def saveRGProductionOrder(doc):
	"""
	保存一个新的 RG Production Order 文档

	参数:
		doc (dict): 包含 RG Production Order 数据的字典

	返回:
		dict: 保存后的文档数据
	"""
	print(f"doc: {doc}")
	try:
		# 提取 materialData 并调用 bulk_add_items_from_data 方法导入成品物料
		material_data = doc.get("materialData", {})
		if material_data:
			try:
				bulk_add_items_from_data(material_data)
			except Exception as e:
				frappe.log_error(f"导入成品物料时出错: {str(e)}")
				# 不影响后续执行，继续处理

		# 映射基本字段
		new_doc = frappe.get_doc({
			"doctype": "RG Production Orders",
			"production_order_number": doc.get("notificationNumber"), # 映射通知单号
			"customer": doc.get("customerId"), # 映射客户ID
			"business_type": doc.get("businessType"), # 映射业务类型
			"order_type": doc.get("orderType"), # 映射订单类型
			"order_number": doc.get("orderNumber"), # 映射订单号
			"departure_date": doc.get("factoryDeadline"), # 映射离厂期
			"product_name": doc.get("productName"), # 映射产品名称
			"status": doc.get("orderStatus"), # 映射订单状态
			"order_date": doc.get("orderDate"), # 映射订单日期
			"delivery_date": doc.get("deliveryDate"), # 映射交货日期
			"contract_number": doc.get("contractNumber"), # 映射合同号
			"merchandiser": doc.get("followerId"), # 映射跟单员ID
			"paper_pattern_maker_id": doc.get("paperPatternMakerId"), # 映射纸样员ID
			"mark": doc.get("mark"), # 映射备注
			"salesperson": doc.get("salesId"), # 映射销售员ID
			"pattern_number": doc.get("patternNumber"), # 映射纸样号
			"national_order": doc.get("countryCode"), # 映射国家单 (根据字段名猜测)
			"factory": doc.get("factoryId"), # 映射工厂ID
			"style_number": doc.get("productName"), # 映射物料ID
			"item": doc.get("productName"), # 映射物料ID
			# "image": doc.get("image"), # JSON中未找到对应字段，忽略或需确认
			"quantity": doc.get("quantity"), # 映射数量
			# 暂时注释 rg_size 字段，避免链接验证错误
			"rg_size": doc.get("materialData", {}).get("selectedSizeChart", {}).get("name"), # 映射尺码类型名称 (根据结构猜测)
			"rg_color": doc.get("materialData", {}).get("selectedColorChart", {}).get("name"), # 映射尺码类型名称 (根据结构猜测)
			"工艺路线": doc.get("processLine"), # 映射工艺路线
			"front_picture": doc.get("displayImageData", {}).get("front", {}).get("file_url"), # 映射款式图示 (取前视图URL)
			"backend_picture": doc.get("displayImageData", {}).get("back", {}).get("file_url"), # 映射款式图示 (取后视图URL)
			"trademark_position_diagram_picture": doc.get("displayImageData", {}).get("brandLabel", {}).get("file_url"), # 映射款式图示 (取后视图URL)
			"origin_label_size_label": doc.get("displayImageData", {}).get("washLabel", {}).get("file_url"), # 映射款式图示 (取后视图URL)

			# 以下字段在提供的doc结构中未直接找到或需要进一步确认如何映射嵌套数据
			# "style_number": doc.get("style_number"), # JSON中定义为Link到Item
			# "order_id": doc.get("order_id"), # JSON中定义
			# "item": doc.get("item"), # JSON中定义为Link到Item
			# "company": doc.get("company"), # JSON中定义
			# "project": doc.get("project"), # JSON中定义
			# "uom": doc.get("uom"), # JSON中定义
			# "is_active": doc.get("is_active"), # JSON中定义
			# "is_default": doc.get("is_default"), # JSON中定义
			# "allow_alternative_item": doc.get("allow_alternative_item"), # JSON中定义
			# "set_rate_of_sub_assembly_item_based_on_bom": doc.get("set_rate_of_sub_assembly_item_based_on_bom"), # JSON中定义
			# "currency_detail": doc.get("currency_detail"), # JSON中定义
		})

		# 映射 Table 字段 (物料清单, 面辅料配件 -> items; 工序步骤 -> operations; 尺码详情 -> rg_size_details)
		items_list = []
		# 映射 materialData.materialList 到 items (RG BOM Item)        
		for item_data in doc.get("materialData", {}).get("materialList", []):
			code = item_data.get("code")
			color = item_data.get("color")
			unit = item_data.get("unit")
			sizes = item_data.get("sizes", {})
			
			# 处理 sizes 字段，只添加数量不为 0 的尺码
			for size, qty in sizes.items():
				if qty and int(qty) != 0:
					item_code_def = f"FG-{code}-{color}-{size}"
					items_list.append({
						"item_code": item_code_def, # 映射物料代码
						"color": color, # 映射颜色
						"uom": unit, # 映射单位
						"qty": int(qty) # 映射数量
					})
		# # 映射 fabricAccessories 到 items (RG BOM Item)
		# for item_data in doc.get("fabricAccessories", []):
		# 	items_list.append({
		# 		"item_code": item_data.get("code"), # 映射物料代码
		# 		"description": item_data.get("description"), # 映射描述
		# 		"qty": item_data.get("quantity"), # 映射数量
		# 		"uom": item_data.get("unit"), # 映射单位
		# 		"rate": item_data.get("price"), # 映射价格
		# 		"amount": item_data.get("amount"), # 映射金额
		# 	})
		new_doc.set("items", items_list)


		operations_list = []
		# 映射 processSteps 到 operations (RG BOM Operation)
		for step_data in doc.get("processSteps", []):
			operations_list.append({
				"operation": step_data.get("operation"), # 映射工序
				"description": step_data.get("description"), # 映射描述
				# factory 和 workstationType 需要根据实际情况映射，这里仅作示例
				# "workstation": step_data.get("factory"), # 映射工厂/工作站
				# "workstation_type": step_data.get("workstationType"), # 映射工作站类型
				# operationCost 需要处理格式，这里仅作示例
				# "operation_cost": step_data.get("operationCost"), # 映射工序成本
				"process_party": step_data.get("processParty"), # 映射加工方
			})
		new_doc.set("operations", operations_list)

		# 映射 rg_size_details (RG Size Details)
		# 这部分映射比较复杂，因为 materialList 中的 sizes 是嵌套字典。
		# 需要根据 RG Size Details 的DocType结构来确定如何映射。
		# 暂时留空，如果需要，请提供 RG Size Details 的DocType结构
		# new_doc.set("rg_size_details", [])

		# table_mbev 字段在 JSON 中定义，使用 RG BOM Item，但输入 doc 中没有明确对应的数据
		# new_doc.set("table_mbev", [])

		# 插入文档到数据库
		new_doc.insert()

		# 处理附件并关联到 Item 或 RG Production Order
		attachments = doc.get("attachments", [])
		for attachment in attachments:
			file_url = attachment.get("file_url")
			file_name = attachment.get("file_name")
			content_type = attachment.get("content_type")
			
			if file_url and file_name:
				try:
					# 下载文件并创建 File 记录
					file_doc = frappe.get_doc({
						"doctype": "File",
						"file_name": file_name,
						"file_url": file_url,
						"attached_to_doctype": "RG Production Orders",
						"attached_to_name": new_doc.name,
						"content_type": content_type if content_type else "application/octet-stream",
						"is_private": 0
					})
					file_doc.insert()
				except Exception as e:
					frappe.log_error(f"处理附件 {file_name} 时出错: {str(e)}")

		# 提交事务
		frappe.db.commit()

		return new_doc.as_dict()
	except Exception as e:
		# 如果出现错误，回滚事务
		frappe.db.rollback()
		frappe.log_error(f"保存 RG Production Order 时出错: {str(e)}")
		# 修改错误抛出方式，避免 TypeError
		frappe.throw(f"保存失败: {str(e)}")

def bulk_add_items_from_data(item_data):
	"""
	批量添加 Item，处理初始 Item 数据中的 sizes 字段，只添加数量不为 0 的 Item。
	
	参数:
		item_data (str or dict or list): 包含 Item 数据的 JSON 字符串、字典或列表，每个 Item 包含 code, color, unit 和 sizes 字段
		
	返回:
		dict: 包含创建成功的 Item 列表和错误信息的字典
	"""
	import json
	import frappe
	from erpnextcn.utils.doctype.item import bulk_create_items
	
	# 如果输入是字符串，则解析为 JSON
	if isinstance(item_data, str):
		item_data = json.loads(item_data)
	
	# 如果输入是字典且包含 materialList 字段，则提取该字段
	print(f"item_data:============== {item_data}")
	if isinstance(item_data, dict) and "materialList" in item_data:
		items = item_data.get("materialList", [])
		item_group = item_data.get("itemGroup", "成品")
		color_attribute = item_data.get("selectedColorChart", {}).get("name", "")
		size_attribute = item_data.get("selectedSizeChart", {}).get("name", "")
	else:
		items = item_data
		item_group = "成品"
		color_attribute = "XSD专属定义颜色"
		size_attribute = "荣冠尺码"
	
	items_to_create = []
	
	for item in items:
		code = item.get("code")
		color = item.get("color")
		unit = item.get("unit")
		sizes = item.get("sizes", {})
		
		# 处理 sizes 字段，只添加数量不为 0 的尺码
		for size, qty in sizes.items():
			if qty and int(qty) != 0:
				# 构建 Item 代码
				item_code = f"{code}-{color}-{size}"
				
				# 检查 Item 是否已经存在
				if frappe.db.exists("Item", item_code):
					frappe.log_error(f"Item {item_code} 已存在，跳过导入。")
					continue
				
				# 创建新的 Item 变体，包含尺码信息
				item_variant = {
					"doctype": "Item",
					"item_code": item_code,
					"item_name": f"{code} ({color}, {size})",
					"description": f"{code} with color {color} and size {size}",
					"uom": unit,
					"variant_of": code,  # 关联到已存在的变体 Item
					"has_variants": 0,
					"attributes": [
						{"attribute": color_attribute, "attribute_value": color},
						{"attribute": size_attribute, "attribute_value": size}
					],
					"stock_uom": unit,
					"default_qty": int(qty),
					"item_group": item_group  # 使用从数据中获取的 item_group 或默认值
				}
				print(f"item_variant: {item_variant}")
				items_to_create.append(item_variant)
	
	# 调用 bulk_create_items 接口进行批量创建
	result = bulk_create_items(items_to_create)
	return result

@frappe.whitelist()
def get_rg_bom_items(page=1, page_size=10):
	"""
	分页获取所有生产订单的 RG BOM Item 数据，并包含生产订单的 style_number
	
	参数:
		page (int): 页码，默认为 1
		page_size (int): 每页显示的记录数，默认为 10
	
	返回:
		dict: 包含 RG BOM Item 列表、生产订单的 style_number 和分页信息的字典
	"""
	try:
		# 计算分页的起始位置
		start = (int(page) - 1) * int(page_size)
		
		# 查询所有 RG BOM Item 数据
		bom_items = frappe.get_all(
			"RG BOM Item",
			filters={"parenttype": "RG Production Orders","parentfield":"items"},
			fields=["name", "item_code", "item_name", "description", "qty", "uom", "rate", "amount", "parent","idx"],
			order_by="parent desc,idx asc",
			start=start,
			page_length=page_size
		)
		
		# 获取总记录数用于分页计算
		total_count = frappe.db.count(
			"RG BOM Item",
			filters={"parenttype": "RG Production Orders"}
		)
		
		# 计算总页数
		total_pages = (total_count + page_size - 1) // page_size
		
		# 获取所有相关生产订单的 style_number 并直接追加到 item 中
		data = []
		for item in bom_items:
			production_order_name = item.get("parent")
			production_order = frappe.get_doc("RG Production Orders", production_order_name) if production_order_name else None
			style_number = production_order.style_number if production_order else ""
			factory_id = production_order.factory if production_order else ""
			customer_id = production_order.customer if production_order else ""
			delivery_date = production_order.delivery_date if production_order else ""
			item["style_number"] = style_number
			item["production_order_name"] = production_order_name
			item["factory_id"] = factory_id
			item["customer_id"] = customer_id
			item["delivery_date"] = delivery_date
			data.append(item)
		
		return {
			"data": data,
			"page": int(page),
			"page_size": int(page_size),
			"total_count": total_count,
			"total_pages": total_pages
		}
	except Exception as e:
		frappe.log_error(f"获取 RG BOM Item 数据时出错: {str(e)}")
		frappe.throw(f"获取物料清单数据失败: {str(e)}")

@frappe.whitelist(allow_guest=False)  # 建议用 token auth 控制权限
def generate_production_order_pdf(name, print_format=None):
    """
    从 RG Production Orders 中读取记录，并用指定 Print Format 渲染 PDF
    """
    if not name:
        frappe.throw("Please provide a document name")

    # 默认使用你在 Print Designer 中设置的模板
    if not print_format:
        print_format = "生产制造通知单"

    doc = frappe.get_doc("RG Production Orders", name)

    # 渲染 Print Format HTML（Jinja 会用 doc 变量）
    html = frappe.get_print(
        doctype="RG Production Orders",
        name=doc.name,
        print_format=print_format,
        doc=doc,
        no_letterhead=True
    )

    # 生成 PDF
    pdf = get_pdf(html)

    # 设置响应
    frappe.local.response.filename = f"{doc.name}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"

@frappe.whitelist()
def get_rg_production_orders(page=1, page_size=10):
    """
    分页获取所有 RG Production Orders 记录
    
    参数:
        page (int): 页码，默认为 1
        page_size (int): 每页显示的记录数，默认为 10
    
    返回:
        dict: 包含 RG Production Orders 列表和分页信息的字典
    """
    try:
        # 计算分页的起始位置
        start = (int(page) - 1) * int(page_size)
        
        # 查询所有 RG Production Orders 数据
        production_orders = frappe.get_all(
            "RG Production Orders",
            fields=[
                "name", "creation", "modified", "owner", "modified_by", 
                "docstatus", "production_order_number", "customer", 
                "business_type", "order_type", "order_number", "departure_date", 
                "style_number", "product_name", "status", "order_id", 
                "order_date", "delivery_date", "contract_number", "merchandiser", 
                "salesperson", "pattern_number", "national_order", "factory", 
                "image", "item", "company", "cb0", "project", "rg_color", 
                "uom", "quantity", "rg_size", "is_active", "is_default", 
                "allow_alternative_item", "set_rate_of_sub_assembly_item_based_on_bom", 
                "currency_detail", "工艺路线", "amended_from", "front_picture", 
                "backend_picture", "trademark_position_diagram_picture", 
                "origin_label_size_label"
                ],
            order_by="creation desc", # 按照创建时间倒序排列
            start=start,
            page_length=page_size
        )
        
        # 获取总记录数用于分页计算
        total_count = frappe.db.count("RG Production Orders")
        
        # 计算总页数
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "data": production_orders,
            "page": int(page),
            "page_size": int(page_size),
            "total_count": total_count,
            "total_pages": total_pages
        }
    except Exception as e:
        frappe.log_error(f"获取 RG Production Orders 数据时出错: {str(e)}")
        frappe.throw(f"获取生产订单数据失败: {str(e)}")

@frappe.whitelist()
def get_production_order_details(docname):
    """
    通过文档名称获取 RG Production Orders 文档的详细信息，包括所有子表数据
    
    参数:
        docname (str): RG Production Orders 文档的名称
        
    返回:
        dict: 包含 RG Production Orders 文档及其子表数据的字典
    """
    try:
        if not docname:
            frappe.throw("请提供有效的文档名称")
            
        # 获取文档及其子表数据
        doc = frappe.get_doc("RG Production Orders", docname)
        
        # 将文档转换为字典格式，以便返回
        doc_dict = doc.as_dict()
        
        return doc_dict
    except Exception as e:
        frappe.log_error(f"获取生产订单 {docname} 详细信息时出错: {str(e)}")
        frappe.throw(f"获取生产订单详细信息失败: {str(e)}")