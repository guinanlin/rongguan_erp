"""
检查物料数据的辅助脚本
用于调试和查看物料的实际数据
"""
import frappe
from frappe import _


@frappe.whitelist(allow_guest=False)
def check_item_by_sku(sku_code):
    """
    根据 SKU code 查找物料并显示其详细信息（用于调试）
    
    Args:
        sku_code: SKU code 字符串
    """
    if not sku_code:
        return {"error": "sku_code is required"}
    
    # 查找匹配的 items
    items = frappe.db.sql("""
        SELECT name, item_code, item_name, description, variant_of, has_variants, disabled
        FROM `tabItem`
        WHERE item_name = %s OR item_code = %s
        LIMIT 10
    """, (sku_code, sku_code), as_dict=True)
    
    result = {
        "sku_code": sku_code,
        "found_count": len(items),
        "items": []
    }
    
    for item in items:
        item_info = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "variant_of": item.variant_of,
            "has_variants": item.has_variants,
            "disabled": item.disabled
        }
        
        # 获取所有属性
        attributes = frappe.db.sql("""
            SELECT iva.attribute, iva.attribute_value, ia._user_tags
            FROM `tabItem Variant Attribute` iva
            INNER JOIN `tabItem Attribute` ia ON ia.name = iva.attribute
            WHERE iva.parent = %s
        """, (item.name,), as_dict=True)
        
        item_info["attributes"] = attributes
        
        # 单独提取颜色属性
        color_attrs = [a for a in attributes if a._user_tags and "颜色" in a._user_tags]
        item_info["color_attributes"] = color_attrs
        
        result["items"].append(item_info)
    
    return result
