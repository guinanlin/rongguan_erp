# Server Script: get_items_by_sku_and_color
# Whitelisted for API access
import frappe
from frappe import _
import json


@frappe.whitelist(allow_guest=False)
def get_items_by_sku_and_color(items_data):
    """
    根据 SKU code 和颜色批量查询 item 详细信息
    
    Args:
        items_data: 对象格式，包含 items 数组，每个元素包含 sku_code 和 color
        示例: {
            "items": [
                {"sku_code": "IW-10200 涤粘弹面料", "color": "黑棕格"},
                {"sku_code": "IW-10201 其他面料", "color": "红色"}
            ]
        }
        或者直接传入数组格式（向后兼容）: [
            {"sku_code": "IW-10200 涤粘弹面料", "color": "黑棕格"}
        ]
    
    Returns:
        数组格式，按输入顺序返回，每个元素包含：
        - found: true/false
        - sku_code: 输入的SKU
        - color: 输入的颜色
        - item_type: "variant" | "template" | "normal"
        - 以及item的主要详细信息（如果找到）
    """
    if not items_data:
        return []
    
    # 如果输入是字符串，解析为JSON
    if isinstance(items_data, str):
        try:
            items_data = json.loads(items_data)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid JSON format for items_data"))
    
    # 支持两种格式：{"items": []} 或直接数组 []
    if isinstance(items_data, dict):
        if "items" in items_data:
            items_list = items_data["items"]
        else:
            frappe.throw(_("items_data must contain 'items' key or be a list"))
    elif isinstance(items_data, list):
        # 向后兼容：直接传入数组
        items_list = items_data
    else:
        frappe.throw(_("items_data must be a dict with 'items' key or a list"))
    
    if not isinstance(items_list, list):
        frappe.throw(_("items must be a list"))
    
    if len(items_list) == 0:
        return []
    
    try:
        # 提取所有唯一的 SKU code 和颜色组合
        sku_codes = [item.get("sku_code", "").strip() for item in items_list if item.get("sku_code")]
        colors = [item.get("color", "").strip() for item in items_list if item.get("color")]
        
        if not sku_codes:
            # 如果没有任何有效的 SKU code，返回所有未找到的结果
            return [
                {
                    "found": False,
                    "sku_code": item.get("sku_code", ""),
                    "color": item.get("color", ""),
                    "message": "SKU code is required"
                }
                for item in items_list
            ]
        
        # 构建 SQL 查询，批量查找所有匹配的 items
        # 使用 IN 子句匹配多个 SKU code
        placeholders = ", ".join(["%s"] * len(sku_codes))
        unique_colors = list(set(colors))
        color_placeholders = ", ".join(["%s"] * len(unique_colors)) if unique_colors else "''"
        
        query = f"""
            SELECT DISTINCT
                item.name as item_code,
                item.item_name,
                item.description,
                item.item_group,
                item.stock_uom,
                item.variant_of,
                item.has_variants,
                item.disabled,
                item.is_stock_item,
                item.standard_rate,
                item.valuation_rate,
                item.image,
                item.brand,
                iva.attribute_value as color_value,
                ia.name as color_attribute_name
            FROM `tabItem` item
            INNER JOIN `tabItem Variant Attribute` iva ON iva.parent = item.name
            INNER JOIN `tabItem Attribute` ia ON ia.name = iva.attribute
            WHERE item.item_name IN ({placeholders})
                AND ia.name LIKE '%%颜色%%'
                AND iva.attribute_value IN ({color_placeholders})
                AND item.disabled = 0
        """
        
        # 准备查询参数
        query_params = list(sku_codes)
        if unique_colors:
            query_params.extend(unique_colors)
        
        # 执行查询
        matched_items = frappe.db.sql(query, query_params, as_dict=True)
        
        # 建立查找映射：sku_code + color -> item
        item_map = {}
        for item in matched_items:
            key = f"{item.item_name}|||{item.color_value}"
            if key not in item_map:
                item_map[key] = item
        
        # 按输入顺序组装结果
        results = []
        for input_item in items_list:
            sku_code = input_item.get("sku_code", "").strip()
            color = input_item.get("color", "").strip()
            
            if not sku_code:
                results.append({
                    "found": False,
                    "sku_code": sku_code,
                    "color": color,
                    "message": "SKU code is required"
                })
                continue
            
            # 查找匹配的 item
            lookup_key = f"{sku_code}|||{color}"
            matched_item = item_map.get(lookup_key)
            
            if not matched_item:
                results.append({
                    "found": False,
                    "sku_code": sku_code,
                    "color": color,
                    "message": "未找到匹配的item"
                })
                continue
            
            # 获取完整的 item 文档以获取所有属性
            try:
                item_doc = frappe.get_doc("Item", matched_item.item_code)
                
                # 判断 item 类型
                if matched_item.variant_of:
                    item_type = "variant"
                elif matched_item.has_variants:
                    item_type = "template"
                else:
                    item_type = "normal"
                
                # 获取所有属性
                attributes = []
                color_value = None
                for attr in item_doc.attributes:
                    attr_dict = attr.as_dict()
                    # 检查是否是颜色属性（通过属性名称判断）
                    if "颜色" in attr.attribute:
                        color_value = attr.attribute_value
                        attr_dict["is_color"] = True
                    else:
                        attr_dict["is_color"] = False
                    attributes.append(attr_dict)
                
                # 构建返回结果
                result = {
                    "found": True,
                    "sku_code": sku_code,
                    "color": color,
                    "item_type": item_type,
                    "item_code": item_doc.item_code,
                    "item_name": item_doc.item_name,
                    "description": item_doc.description or "",
                    "item_group": item_doc.item_group,
                    "stock_uom": item_doc.stock_uom,
                    "variant_of": item_doc.variant_of or "",
                    "has_variants": 1 if item_doc.has_variants else 0,
                    "disabled": 1 if item_doc.disabled else 0,
                    "is_stock_item": 1 if item_doc.is_stock_item else 0,
                    "standard_rate": item_doc.standard_rate or 0,
                    "valuation_rate": item_doc.valuation_rate or 0,
                    "image": item_doc.image or "",
                    "brand": item_doc.brand or "",
                    "color_value": color_value or "",
                    "attributes": attributes
                }
                
                results.append(result)
                
            except Exception as e:
                frappe.log_error(f"Error getting item details for {matched_item.item_code}: {str(e)}", "Get Item by SKU Error")
                results.append({
                    "found": False,
                    "sku_code": sku_code,
                    "color": color,
                    "message": f"获取item详情时出错: {str(e)}"
                })
        
        return results
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_items_by_sku_and_color failed")
        frappe.throw(_("查询失败: {0}").format(str(e)))


# 测试脚本
# 使用方法：
# bench --site site1.local execute rongguan_erp.utils.api.item.item_api_for_agent.get_items_by_sku_and_color --kwargs '{"items_data": {"items": [{"sku_code": "zNF-16-RED", "color": "红"}]}}'
#
# 或者通过 API 调用：
# POST /api/method/rongguan_erp.utils.api.item.item_api_for_agent.get_items_by_sku_and_color
# Body: {"items_data": {"items": [{"sku_code": "zNF-16-RED", "color": "红"}]}}
