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
				item_creation_result = bulk_add_items_from_data(material_data) # 捕获返回值
				if item_creation_result and item_creation_result.get("errors"):
					# 如果存在错误，打印并抛出
					error_message = "导入成品物料时出错: " + str(item_creation_result["errors"])
					frappe.log_error(error_message)
					frappe.throw(error_message)
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
			"style_number": doc.get("styleNumber"), # 映射物料ID
			"item": doc.get("productName"), # 映射物料ID
			# "image": doc.get("image"), # JSON中未找到对应字段，忽略或需确认
			"quantity": doc.get("quantity"), # 映射数量
			# 暂时注释 rg_size 字段，避免链接验证错误
			"custom_copy_from": doc.get("custom_copy_from"), # 映射 custom_copy_from 字段
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
					item_code_def = code # 映射物料代码，直接使用 code 字段值
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
	print(f"item_data:==============\n {item_data}\n===============")
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
		variant_of = item.get("variant_of")
		# 处理 sizes 字段，只添加数量不为 0 的尺码
		for size, qty in sizes.items():
			if qty and int(qty) != 0:
				# 构建 Item 代码
				item_code = code # 直接使用 code 字段值
				
				# 检查 Item 是否已经存在
				if frappe.db.exists("Item", item_code):
					frappe.log_error(f"Item {item_code} 已存在，跳过导入。")
					print(f"Item {item_code} 已存在，跳过导入。===========")
					continue
				
				# 创建新的 Item 变体，包含尺码信息
				item_variant = {
					"doctype": "Item",
					"item_code": item_code,
					"item_name": f"{code} ({color}, {size})",
					"description": f"{code} with color {color} and size {size}",
					"uom": unit,
					"variant_of": variant_of,
					"has_variants": 1,
					"attributes": [
						{"attribute": color_attribute, "attribute_value": color},
						{"attribute": size_attribute, "attribute_value": size}
					],
					"stock_uom": unit,
					"default_qty": int(qty),
					"item_group": item_group
				}
				print(f"产生物料的变体 item_variant:\n {item_variant}\n===============")
				items_to_create.append(item_variant)
	
	# 调用 bulk_create_items 接口进行批量创建
	result = bulk_create_items(items_to_create)
	print(f"批量创建物料的变体 result:\n {result}\n===============")
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
                "image", "company", "cb0", "project", "rg_color", 
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
        
        # 为每个生产订单添加纸样单状态
        for order in production_orders:
            if order.get("pattern_number"):
                try:
                    # 根据纸样单号查找对应的纸样单（通过文档名称查找）
                    paper_pattern_docs = frappe.get_all(
                        "RG Paper Pattern",
                        filters={"name": order.get("pattern_number")},
                        fields=["name", "docstatus"],
                        limit=1
                    )
                    
                    if paper_pattern_docs:
                        paper_pattern_doc = paper_pattern_docs[0]
                        # 根据 docstatus 设置状态
                        if paper_pattern_doc.docstatus == 0:
                            order["paper_pattern_status"] = "草稿"
                        elif paper_pattern_doc.docstatus == 1:
                            order["paper_pattern_status"] = "已提交"
                        elif paper_pattern_doc.docstatus == 2:
                            order["paper_pattern_status"] = "已取消"
                        else:
                            order["paper_pattern_status"] = "未知状态"
                    else:
                        order["paper_pattern_status"] = ""
                except Exception as e:
                    frappe.log_error(f"获取纸样单 {order.get('pattern_number')} 状态时出错: {str(e)}")
                    order["paper_pattern_status"] = ""
            else:
                order["paper_pattern_status"] = ""
        
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
        
        # 获取纸样单状态（如果 pattern_number 有值）
        if doc_dict.get("pattern_number"):
            try:
                # 根据纸样单号查找对应的纸样单（通过文档名称查找）
                paper_pattern_docs = frappe.get_all(
                    "RG Paper Pattern",
                    filters={"name": doc_dict.get("pattern_number")},
                    fields=["name", "docstatus"],
                    limit=1
                )
                
                if paper_pattern_docs:
                    paper_pattern_doc = paper_pattern_docs[0]
                    # 根据 docstatus 设置状态
                    if paper_pattern_doc.docstatus == 0:
                        doc_dict["paper_pattern_status"] = "草稿"
                    elif paper_pattern_doc.docstatus == 1:
                        doc_dict["paper_pattern_status"] = "已提交"
                    elif paper_pattern_doc.docstatus == 2:
                        doc_dict["paper_pattern_status"] = "已取消"
                    else:
                        doc_dict["paper_pattern_status"] = "未知状态"
                else:
                    doc_dict["paper_pattern_status"] = ""
            except Exception as e:
                frappe.log_error(f"获取纸样单 {doc_dict.get('pattern_number')} 状态时出错: {str(e)}")
                doc_dict["paper_pattern_status"] = "获取状态失败"
        else:
            doc_dict["paper_pattern_status"] = ""
        
        # 处理 items 子表，添加颜色和尺码信息
        if "items" in doc_dict and doc_dict["items"]:
            for item in doc_dict["items"]:
                item_code = item.get("item_code")
                if item_code:
                    try:
                        item_doc = frappe.get_doc("Item", item_code)
                        color = ""
                        size = ""
                        
                        # 获取 Item 的属性
                        for attr in item_doc.get("attributes", []):
                            attribute_name = attr.attribute
                            attribute_value = attr.attribute_value
                            
                            # 查询 tabItem Attribute 表，根据 _user_tags 判断属性类型
                            try:
                                attr_doc = frappe.get_doc("Item Attribute", attribute_name)
                                user_tags = attr_doc.get("_user_tags", "")
                                
                                # 如果 _user_tags 包含颜色相关关键词，则认为是颜色属性
                                if any(tag in user_tags.lower() for tag in ["颜色"]):
                                    color = attribute_value
                                # 如果 _user_tags 包含尺寸相关关键词，则认为是尺码属性
                                elif any(tag in user_tags.lower() for tag in ["尺寸"]):
                                    size = attribute_value
                                    
                            except Exception as attr_e:
                                frappe.log_error(f"获取属性 {attribute_name} 的 _user_tags 时出错: {str(attr_e)}")
                                # 如果无法获取 _user_tags，不设置任何默认值，保持空值
                        
                        item["color"] = color # 添加颜色到返回的 item 字典
                        item["size"] = size   # 添加尺码到返回的 item 字典
                    except Exception as e:
                        frappe.log_error(f"获取物料 {item_code} 的属性时出错: {str(e)}")
                        # 即使无法获取物料属性，也继续执行
        
        # 根据 items 汇总 rg_size_details
        size_qty_map = {}
        if "items" in doc_dict and doc_dict["items"]:
            for item in doc_dict["items"]:
                size = item.get("size")
                qty = item.get("qty")
                if size and qty is not None:
                    try:
                        qty_int = int(qty)
                        if size in size_qty_map:
                            size_qty_map[size] += qty_int
                        else:
                            size_qty_map[size] = qty_int
                    except ValueError:
                        frappe.log_error(f"物料 {item.get('item_code')} 的数量格式无效: {qty}")
        
        derived_rg_size_details = []
        idx = 1
        for size, aggregated_qty in size_qty_map.items():
            derived_rg_size_details.append({
                "size": size,
                "qty": aggregated_qty
            })
            idx += 1
        
        doc_dict["rg_size_details"] = derived_rg_size_details
        
        # 处理 rg_bom_detail_listing 子表数据（table_mbev）
        if "table_mbev" in doc_dict and doc_dict["table_mbev"]:
            # 将 table_mbev 重命名为更直观的字段名
            doc_dict["rg_bom_detail_listing"] = doc_dict["table_mbev"]
            # 同时保留原字段名以保持兼容性
        else:
            doc_dict["rg_bom_detail_listing"] = []
        
        return doc_dict
    except Exception as e:
        frappe.log_error(f"获取生产订单 {docname} 详细信息时出错: {str(e)}")
        frappe.throw(f"获取生产订单详细信息失败: {str(e)}")

@frappe.whitelist()
def update_bom_detail_listing(docname, detail_listing_data):
    """
    更新生产制造通知单的物料明细清单子表
    
    参数:
        docname (str): 生产制造通知单的文档名称
        detail_listing_data (list): 物料明细清单数据列表
        
    返回:
        dict: 更新结果
    """
    try:
        if not docname:
            frappe.throw("请提供有效的文档名称")
            
        if not detail_listing_data:
            frappe.throw("请提供物料明细清单数据")
        
        # 读取父单
        doc = frappe.get_doc("RG Production Orders", docname)
        
        # 清空原有物料明细清单
        doc.table_mbev = []
        
        # 添加新的明细行
        for item_data in detail_listing_data:
            # 验证必要字段
            if not item_data.get("item_code"):
                frappe.throw("物料代码是必填字段")
            
            # 构建明细行数据
            detail_row = {
                "item_code": item_data.get("item_code"),
                "item_description": item_data.get("item_description", ""),
                "item_color": item_data.get("item_color", ""),
                "qty_per_unit": item_data.get("qty_per_unit", 0),
                "garment_color": item_data.get("garment_color", ""),
                "shared": item_data.get("shared", 0),
                "garment_qty": item_data.get("garment_qty", 0),
                "uom": item_data.get("uom", ""),
                "item_group": item_data.get("item_group", ""),
                "rate": item_data.get("rate", 0),
                "amount": item_data.get("amount", 0),
                "required_qty": item_data.get("required_qty", 0),
                "actual_qty": item_data.get("actual_qty", 0),
                "projected_qty": item_data.get("projected_qty", 0),
                "reserved_qty": item_data.get("reserved_qty", 0),
                "ordered_qty": item_data.get("ordered_qty", 0),
                "planned_qty": item_data.get("planned_qty", 0),
                "purchase_planned_qty": item_data.get("purchase_planned_qty", 0),
                "warehouse": item_data.get("warehouse", "")
            }
            
            # 添加到子表
            doc.append("table_mbev", detail_row)
        
        # 保存文档
        doc.save()
        
        # 提交事务
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"成功更新生产制造通知单 {docname} 的物料明细清单",
            "updated_count": len(detail_listing_data)
        }
        
    except Exception as e:
        # 回滚事务
        frappe.db.rollback()
        frappe.log_error(f"更新物料明细清单时出错: {str(e)}")
        frappe.throw(f"更新物料明细清单失败: {str(e)}")