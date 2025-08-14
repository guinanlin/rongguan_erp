import frappe
from frappe import _
from frappe.utils import flt, cint
import functools


@frappe.whitelist()
def get_exploded_bom_items(**args):
    """
    根据BOM编号和数量获取展开的BOM物料明细
    
    Args:
        **args: 关键字参数
            bom_no (str): BOM编号
            qty (float): 成品数量，默认为1
            include_non_stock_items (bool): 是否包含非库存物料，默认为True
    
    Note:
        公司信息会自动从BOM文档中获取，无需手动提供
        
    Returns:
        dict: 包含BOM展开物料明细的字典
        {
            "status": "success",
            "data": {
                "item_code": "成品编码",
                "item_name": "成品名称", 
                "bom_no": "BOM编号",
                "qty": 80,
                "total_items": 15,
                "exploded_items": [
                    {
                        "item_code": "物料编码",
                        "item_name": "物料名称",
                        "qty": 160.0,
                        "stock_uom": "单位",
                        "rate": 10.5,
                        "amount": 1680.0,
                        "source_warehouse": "仓库",
                        "operation": "工序",
                        "description": "描述"
                    }
                ]
            }
        }
    """
    try:
        # 从args中获取参数
        bom_no = args.get('bom_no')
        qty = args.get('qty', 1)
        include_non_stock_items = args.get('include_non_stock_items', True)
        
        # 参数验证
        if not bom_no:
            return {
                "status": "error", 
                "message": "BOM编号(bom_no)不能为空"
            }
            
        qty = flt(qty) or 1
        if qty <= 0:
            return {
                "status": "error", 
                "message": "数量必须大于0"
            }
        
        # 检查BOM是否存在
        if not frappe.db.exists("BOM", bom_no):
            return {
                "status": "error", 
                "message": f"BOM {bom_no} 不存在"
            }
        
        # 获取BOM基本信息
        bom_doc = frappe.get_doc("BOM", bom_no)
        if bom_doc.docstatus != 1:
            return {
                "status": "error", 
                "message": f"BOM {bom_no} 尚未提交，无法使用"
            }
        
        # 从BOM文档中获取公司信息（BOM必须有公司字段）
        company = bom_doc.company
        if not company:
            return {
                "status": "error", 
                "message": f"BOM {bom_no} 没有设置公司信息"
            }
        
        # 获取BOM对应的物料信息
        item_code = bom_doc.item
        item_doc = frappe.get_doc("Item", item_code)
        
        # 调用ERPNext的BOM展开方法获取物料明细
        from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
        
        exploded_items_dict = get_bom_items_as_dict(
            bom=bom_no,
            company=company, 
            qty=qty,
            fetch_exploded=1,  # 获取展开的BOM
            include_non_stock_items=include_non_stock_items
        )
        
        # 将字典转换为列表并排序
        exploded_items = list(exploded_items_dict.values())
        exploded_items.sort(key=functools.cmp_to_key(lambda a, b: (a.item_code > b.item_code) - (a.item_code < b.item_code)))
        
        # 计算总金额
        total_amount = sum(flt(item.get("amount", 0)) for item in exploded_items)
        
        # 格式化返回数据
        result_data = {
            "item_code": item_code,
            "item_name": item_doc.item_name,
            "bom_no": bom_no,
            "bom_quantity": bom_doc.quantity,
            "requested_qty": qty,
            "company": company,
            "currency": bom_doc.currency,
            "total_items": len(exploded_items),
            "total_amount": total_amount,
            "exploded_items": []
        }
        
        # 处理每个展开的物料项
        for item in exploded_items:
            item_info = {
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "qty": flt(item.get("qty", 0)),
                "stock_uom": item.get("stock_uom"),
                "rate": flt(item.get("rate", 0)),
                "amount": flt(item.get("amount", 0)),
                "source_warehouse": item.get("source_warehouse"),
                "operation": item.get("operation"),
                "description": item.get("description"),
                "item_group": item.get("item_group"),
                "allow_alternative_item": item.get("allow_alternative_item"),
                "include_item_in_manufacturing": item.get("include_item_in_manufacturing"),
                "sourced_by_supplier": item.get("sourced_by_supplier")
            }
            result_data["exploded_items"].append(item_info)
        
        return {
            "status": "success",
            "message": f"成功获取BOM {bom_no} 的物料明细，共 {len(exploded_items)} 项物料",
            "data": result_data
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"获取BOM展开物料明细时发生错误: {str(e)}",
            title="BOM Exploded Items Error"
        )
        return {
            "status": "error",
            "message": f"获取BOM物料明细失败: {str(e)}"
        }


@frappe.whitelist()
def get_bom_structure_summary(**args):
    """
    获取BOM结构摘要信息（不包含详细物料清单，用于快速查看）
    
    Args:
        **args: 关键字参数
            item_code (str): 成品物料编码
            qty (float): 数量
    
    Note:
        公司信息会自动从BOM文档中获取，无需手动提供
        
    Returns:
        dict: BOM结构摘要
    """
    try:
        # 从args中获取参数
        item_code = args.get('item_code')
        qty = args.get('qty', 1)
        
        if not item_code:
            return {"status": "error", "message": "物料编码不能为空"}
        
        # 检查物料是否存在
        if not frappe.db.exists("Item", item_code):
            return {"status": "error", "message": f"物料 {item_code} 不存在"}
        
        # 获取物料和BOM信息
        item_doc = frappe.get_doc("Item", item_code)
        default_bom = item_doc.default_bom
        
        if not default_bom:
            return {"status": "error", "message": f"物料 {item_code} 没有设置默认BOM"}
        
        bom_doc = frappe.get_doc("BOM", default_bom)
        
        # 从BOM获取公司信息
        company = bom_doc.company
        
        # 获取BOM项目统计
        bom_items_count = frappe.db.count("BOM Item", {"parent": default_bom})
        exploded_items_count = frappe.db.count("BOM Explosion Item", {"parent": default_bom})
        
        return {
            "status": "success",
            "data": {
                "item_code": item_code,
                "item_name": item_doc.item_name,
                "bom_no": default_bom,
                "bom_quantity": bom_doc.quantity,
                "requested_qty": flt(qty),
                "company": company,
                "currency": bom_doc.currency,
                "bom_items_count": bom_items_count,
                "exploded_items_count": exploded_items_count,
                "total_cost": bom_doc.total_cost,
                "raw_material_cost": bom_doc.raw_material_cost,
                "operating_cost": bom_doc.operating_cost
            }
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"获取BOM结构摘要时发生错误: {str(e)}",
            title="BOM Structure Summary Error"
        )
        return {
            "status": "error",
            "message": f"获取BOM结构摘要失败: {str(e)}"
        }


@frappe.whitelist()
def test_bom_explosion():
    """
    测试BOM展开功能的演示方法
    
    Returns:
        dict: 测试结果
    """
    try:
        # 获取系统中第一个已提交的BOM进行测试
        test_bom = frappe.db.sql("""
            SELECT name, item, company
            FROM `tabBOM` 
            WHERE docstatus = 1
            LIMIT 1
        """, as_dict=True)
        
        if not test_bom:
            return {
                "status": "warning",
                "message": "系统中没有找到已提交的BOM，无法进行测试"
            }
        
        bom = test_bom[0]
        
        # 测试获取BOM物料明细
        result = get_exploded_bom_items(
            bom_no=bom.name,
            qty=10,  # 测试数量为10
            include_non_stock_items=True
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"BOM展开功能测试成功！使用测试BOM: {bom.name} (物料: {bom.item})",
                "test_data": {
                    "test_bom": bom,
                    "explosion_result": result
                }
            }
        else:
            return {
                "status": "error",
                "message": f"BOM展开功能测试失败: {result.get('message', '未知错误')}",
                "test_data": {
                    "test_bom": bom,
                    "error_result": result
                }
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"测试过程中发生错误: {str(e)}"
        }


# API使用示例和说明
"""
API使用方法：

1. 获取展开的BOM物料明细：
   POST /api/method/rongguan_erp.utils.api.bom.get_exploded_bom_items
   Body: {
       "bom_no": "BOM-FG000579-001",  # BOM编号
       "qty": 80,                     # 数量
       "include_non_stock_items": true  # 可选，是否包含非库存物料
   }
   注：公司信息和物料信息会自动从BOM文档中获取

2. 获取BOM结构摘要：
   POST /api/method/rongguan_erp.utils.api.bom.get_bom_structure_summary
   Body: {
       "item_code": "FG000579",
       "qty": 80
   }
   注：公司信息会自动从BOM文档中获取

3. 测试BOM展开功能：
   POST /api/method/rongguan_erp.utils.api.bom.test_bom_explosion
   Body: {} (无需参数)

返回数据格式：
{
    "status": "success|error|warning",
    "message": "操作结果描述",
    "data": {
        "item_code": "成品编码",
        "item_name": "成品名称",
        "bom_no": "BOM编号", 
        "requested_qty": 80,
        "total_items": 15,
        "total_amount": 12800.0,
        "exploded_items": [
            {
                "item_code": "RM001",
                "item_name": "原材料1",
                "qty": 160.0,
                "stock_uom": "Nos",
                "rate": 10.5,
                "amount": 1680.0,
                "source_warehouse": "Stores - C",
                "operation": "Material Transfer",
                "description": "原材料描述"
            }
        ]
    }
}
"""
