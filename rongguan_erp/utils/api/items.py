# Server Script: get_items_with_attributes
# Whitelisted for API access
import frappe
from frappe import _
import json
from erpnext.controllers.item_variant import create_variant


# bench --site site1.local execute rongguan_erp.utils.api.items.get_items_with_attributes --kwargs '{"filters": {"item_group": "成品"}}'
@frappe.whitelist(allow_guest=False)  # 确保只允许认证用户访问
def get_items_with_attributes(filters=None, fields=None):
    if not filters:
        filters = {}
    
    items = frappe.get_all(
        'Item',
        filters=filters,
        fields=fields or ["*"],
        pluck='name'
    )

    result = []
    for item in items:
        doc = frappe.get_doc('Item', item)
        data = doc.as_dict()
        data["attributes"] = doc.attributes
        result.append(data)

    return result

# 要从 API 调用此脚本，使用以下 URL：
# http://192.168.32.20:8000/api/method/get_items_with_attributes?filters={"item_group": "成品"}&fields=["name","item_code"]

# bench --site site1.local execute rongguan_erp.utils.api.items.get_items_attribute_with_value --kwargs '{"filters": {"item_group": "成品"}}'
@frappe.whitelist(allow_guest=False)  # 确保只允许认证用户访问
def get_items_attribute_with_value(filters=None, fields=None):
    if not filters:
        filters = {}
    
    items = frappe.get_all(
        'Item Attribute Value',
        filters=filters,
        fields=fields or ["*"],
        pluck='name'
    )

    result = []
    for item in items:
        doc = frappe.get_doc('Item Attribute Value', item)
        data = doc.as_dict()
        result.append(data)

    return result

# bench --site site1.local execute rongguan_erp.utils.api.items.get_items_by_item_group --kwargs '{"item_group_name": "成品"}'
@frappe.whitelist()
def get_boms_by_item_group(item_group_name):
    """
    根据指定的 Item Group 获取该分类下的所有物料信息（含 BOM、工序等）
    """
    if not item_group_name:
        frappe.throw(_("Item Group 名称不能为空"))

    # Step 1: 使用 SQL 查询获取指定 Item Group 下且有默认 BOM 的物料
    items = frappe.db.sql("""
        SELECT item.name, item.item_code, item.item_name, item.stock_uom, 
               item.variant_of,bom.name as bom_name,bom.is_active,bom.is_default
        FROM `tabItem` AS item
        INNER JOIN `tabBOM` AS bom ON bom.item = item.name
        WHERE item.item_group = %s AND bom.is_active = 1 AND bom.is_default = 1
    """, (item_group_name,), as_dict=True)

    result = []

    for item in items:
        # 获取规格信息（Item Variant Attributes）并转换为字典
        attrs = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": item.name},
            fields=["attribute", "attribute_value"]
        )
        specification_dict = {}
        if attrs:
            for attr in attrs:
                specification_dict[attr.attribute] = attr.attribute_value  # 转换为字典格式

        # Step 3: 获取工序数量（通过 Routing）
        # boms = frappe.get_all(
        #     "BOM",
        #     filters={"item": item.name, "is_active": 1, "is_default": 1},
        #     fields=["routing"]
        # )        
       
        routings = frappe.get_all(
            "BOM Operation",
            filters={"parent": item.bom_name},
            fields=["operation"]
        )
        operation_count = len(routings)

        # Step 4: 获取 BOM 信息
        bom_data = None
        boms_info = frappe.get_all(
            "BOM",
            filters={"item": item.name, "is_active": 1, "is_default": 1},
            fields=["name", "docstatus"]
        )
        if boms_info:
            bom_no = boms_info[0].name
            status = "Submitted" if boms_info[0].docstatus == 1 else "Draft"
        else:
            bom_no = None  # 或其他默认值
            status = None  # 或其他默认值

        bom_items = frappe.get_all(
            "BOM Item",
            filters={"parent": item.bom_name},
            fields=["qty", "uom", "item_code", "item_name"]
        )

        bom_items_count = len(bom_items)

        # 构建最终的 result 项（将 bom_no 和 status 提升到顶层）
        result_item = {
            "bom_no": bom_no,  # 直接作为顶层字段
            "status": status,  # 直接作为顶层字段
            "is_active": item.is_active,
            "is_default": item.is_default,
            "item": {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "UOM": item.stock_uom
            },
            "bom_items": bom_items,
            "bom_items_count": bom_items_count,
            "bom_operation_count": operation_count,
            "specification": specification_dict
        }

        result.append(result_item)

    return result

# file: rongguan_erp/utils/api/items.py
# 示例用法:
# bench --site site1.local execute rongguan_erp.utils.api.items.create_style_number_number_by_custom_item_code --kwargs '{"item_data": {"doctype": "Item", "item_code": "A013", "item_name": "测xx224", "item_group": "成品", "stock_uom": "件", "has_variants": 1, "attributes": [{"attribute": "颜色", "attribute_value": "颜色"}, {"attribute": "尺寸", "attribute_value": "荣冠尺码"}]}}'
# 返回结果:
# {"item_code": "A013", "item_name": "\u6d4bxx224", "message": "Item created successfully with custom item_code"}
@frappe.whitelist()
def create_style_number_number_by_custom_item_code(item_data):
    if isinstance(item_data, str):
        try:
            item_data = json.loads(item_data)
        except json.JSONDecodeError:
             frappe.throw(_("Invalid JSON input."))

    if not isinstance(item_data, dict):
        frappe.throw(_("Invalid input. Expected a dictionary."))

    if item_data.get("doctype") != "Item":
         frappe.throw(_("Invalid doctype specified. Must be 'Item'."))

    # 检查是否是变体物料
    has_variants = item_data.get("has_variants")
    variant_of = item_data.get("variant_of")
    provided_item_code = item_data.get("item_code")
    attachment_urls = item_data.get("attachment_urls", [])  # 获取多个附件 URL，默认为空列表

    if has_variants or variant_of:  # 如果是变体相关的物料
        if provided_item_code:
            try:
                # 设置标志以禁用自动命名
                frappe.flags.in_import = True
                
                doc = frappe.get_doc(item_data)
                doc.name = provided_item_code
                doc.item_code = provided_item_code
                doc.insert(ignore_if_duplicate=True)
                
                # 处理多个附件
                for url in attachment_urls:
                    file_doc = frappe.get_doc({
                        "doctype": "File",
                        "file_url": url,
                        "attached_to_doctype": "Item",
                        "attached_to_name": doc.name,
                        "folder": "Home/Attachments"
                    })
                    file_doc.insert()
                
                # 重置标志
                frappe.flags.in_import = False
                
                frappe.db.commit()
                return {
                    "item_code": doc.name,
                    "item_name": doc.item_name,
                    "message": _("Item created successfully with custom item_code")
                }
            except Exception as e:
                frappe.db.rollback()
                frappe.flags.in_import = False
                frappe.throw(_("Failed to create Item: {0}").format(str(e)))
    
    # 对于非变体物料，使用默认的自动命名
    doc = frappe.get_doc(item_data)
    doc.insert()
    
    # 处理多个附件
    for url in attachment_urls:
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_url": url,
            "attached_to_doctype": "Item",
            "attached_to_name": doc.name,
            "folder": "Home/Attachments"
        })
        file_doc.insert()
    
    frappe.db.commit()
    
    return {
        "item_code": doc.name,
        "item_name": doc.item_name,
        "message": _("Item created successfully with auto-generated item_code")
    }


@frappe.whitelist()
def get_item_color_values(item_code):
    if not item_code:
        return {"error": "item_code is required"}

    item = frappe.get_doc("Item", item_code)

    color_attributes = []

    for attr in item.attributes:
        try:
            attr_doc = frappe.get_doc("Item Attribute", attr.attribute)
            if attr_doc._user_tags and "颜色" in attr_doc._user_tags:
                color_values = [v.attribute_value for v in attr_doc.item_attribute_values]
                color_attributes.append({
                    "attribute": attr.attribute,
                    "values": color_values
                })
        except frappe.DoesNotExistError:
            continue

    if not color_attributes:
        return {"error": "No attribute with tag '颜色' found for this item"}

    return {
        "color_attributes": color_attributes
    }    
@frappe.whitelist()
def get_item_size_values(item_code):
    if not item_code:
        return {"error": "item_code is required"}

    item = frappe.get_doc("Item", item_code)

    size_attributes = []

    for attr in item.attributes:
        try:
            attr_doc = frappe.get_doc("Item Attribute", attr.attribute)
            if attr_doc._user_tags and "尺寸" in attr_doc._user_tags:
                size_values = [v.attribute_value for v in attr_doc.item_attribute_values]
                size_attributes.append({
                    "attribute": attr.attribute,
                    "values": size_values
                })
        except frappe.DoesNotExistError:
            continue

    if not size_attributes:
        return {"error": "No attribute with tag '荣冠尺码' found for this item"}

    return {
        "size_attributes": size_attributes
    }    