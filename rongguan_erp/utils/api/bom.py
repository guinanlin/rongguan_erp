import frappe
from frappe import _
from frappe.utils import flt, cint, now_datetime
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
def create_new_bom_version(bom_name, **kwargs):
    """
    创建BOM新版本（后端方法）- 简化版
    
    使用方法：
    # 完全替换物料清单（推荐）
bench --site site1.local execute rongguan_erp.utils.api.bom.create_new_bom_version --kwargs "{'bom_name': 'BOM-QZ0004-pink-02-024', 'remarks': '更新物料清单', 'items': [{'item_code': 'RED布料-pink-04', 'qty': 3.8}, {'item_code': 'RED布料-red-08', 'qty': 4.5}]}"
bench --site site1.local execute rongguan_erp.utils.api.bom.create_new_bom_version --kwargs "{'bom_name': 'BOM-QZ0004-pink-02-024', 'remarks': '更新物料和图片', 'items': [{'item_code': 'RED布料-pink-04', 'qty': 3.8, 'image': 'https://example.com/images/pink-04.jpg'}, {'item_code': 'RED布料-red-08', 'qty': 4.5, 'image': 'https://example.com/images/red-08.jpg'}]}"
    Args:
        bom_name (str): 源BOM编号
        **kwargs: 可选参数
            remarks (str): 版本说明/备注
            amendments (dict): 需要修改的BOM主表字段 {"field_name": "new_value"}
            items (list): BOM物料清单（完整替换原有物料）[{"item_code": "物料编码", "qty": 数量, "rate": 单价, "image": "图片URL", "description": "描述", "source_warehouse": "仓库", ...}]
            is_active (int): 是否激活，默认1（激活）
            is_default (int): 是否设为默认BOM，默认0（不设为默认）
    
    Returns:
        dict: {
            "status": "success|error",
            "message": "操作结果描述",
            "data": {
                "original_bom": "源BOM编号",
                "new_bom": "新BOM编号",
                "new_bom_doc": {...}  # 新BOM文档对象
            }
        }
    
    Example:
        # 示例1: 仅创建新版本（保留原有物料）
        result = frappe.call(
            "rongguan_erp.utils.api.bom.create_new_bom_version",
            bom_name="BOM-ITEM-001",
            remarks="材料价格调整"
        )
        
        # 示例2: 创建新版本并完全替换物料清单
        result = frappe.call(
            "rongguan_erp.utils.api.bom.create_new_bom_version",
            bom_name="BOM-ITEM-001",
            remarks="更新物料清单",
            items=[
                {"item_code": "RED布料-pink-04", "qty": 3.8, "rate": 1.79},
                {"item_code": "RED布料-red-08", "qty": 4.5, "rate": 0.58}
            ]
        )
        
        # 示例3: 创建新版本并设置物料图片
        result = frappe.call(
            "rongguan_erp.utils.api.bom.create_new_bom_version",
            bom_name="BOM-ITEM-001",
            remarks="更新物料和图片",
            items=[
                {
                    "item_code": "RED布料-pink-04",
                    "qty": 3.8,
                    "rate": 1.79,
                    "image": "https://example.com/images/red-fabric-pink-04.jpg",
                    "description": "红色布料 - 高质量"
                },
                {
                    "item_code": "RED布料-red-08",
                    "qty": 4.5,
                    "rate": 0.58,
                    "image": "https://example.com/images/red-fabric-red-08.jpg",
                    "source_warehouse": "主仓库 - DMY"
                }
            ]
        )
    """
    try:
        # 1. 参数验证
        if not bom_name:
            return {
                "status": "error",
                "message": "BOM编号(bom_name)不能为空"
            }
        
        # 2. 检查源BOM是否存在
        if not frappe.db.exists("BOM", bom_name):
            return {
                "status": "error",
                "message": f"BOM {bom_name} 不存在"
            }
        
        # 3. 获取源BOM文档
        source_bom = frappe.get_doc("BOM", bom_name)
        
        # 验证BOM状态（只能从已提交的BOM创建新版本）
        if source_bom.docstatus != 1:
            return {
                "status": "error",
                "message": f"只能从已提交的BOM创建新版本，当前BOM状态为: {source_bom.docstatus}"
            }
        
        # 4. 使用frappe.copy_doc复制文档
        new_bom = frappe.copy_doc(source_bom, ignore_no_copy=True)
        
        # 5. 重置关键字段
        new_bom.docstatus = 0  # 设为草稿
        new_bom.is_active = kwargs.get('is_active', 1)  # 默认激活
        new_bom.is_default = kwargs.get('is_default', 0)  # 默认不设为默认BOM
        new_bom.amended_from = None  # 清除修订来源
        
        # 6. 添加版本信息到描述
        version_info = f"\n\n=== 版本信息 ===\n"
        version_info += f"创建时间: {now_datetime()}\n"
        version_info += f"源BOM: {bom_name}\n"
        
        # 如果提供了备注说明，添加到版本信息中
        remarks = kwargs.get('remarks')
        if remarks:
            version_info += f"版本说明: {remarks}\n"
        
        # 追加到原有描述后面
        if new_bom.description:
            new_bom.description = new_bom.description + version_info
        else:
            new_bom.description = version_info
        
        # 7. 应用可选的字段修改（BOM主表）
        amendments = kwargs.get('amendments')
        if amendments and isinstance(amendments, dict):
            for field_name, field_value in amendments.items():
                if hasattr(new_bom, field_name):
                    new_bom.set(field_name, field_value)
        
        # 7.5 如果提供了items参数，清空原有物料并重新添加
        items = kwargs.get('items')
        if items and isinstance(items, list):
            # 清空原有的所有物料
            new_bom.items = []
            
            # 添加新的物料清单
            for item_data in items:
                item_code = item_data.get('item_code')
                if not item_code:
                    continue
                
                # 检查物料是否存在
                if not frappe.db.exists("Item", item_code):
                    frappe.msgprint(f"物料 {item_code} 不存在，跳过添加")
                    continue
                
                # 获取物料信息
                item_doc = frappe.get_doc("Item", item_code)
                
                # 创建新的 BOM Item 行
                bom_item_row = new_bom.append('items', {})
                bom_item_row.item_code = item_code
                bom_item_row.item_name = item_doc.item_name
                bom_item_row.description = item_data.get('description', item_doc.description or item_doc.item_name)
                bom_item_row.uom = item_data.get('uom', item_doc.stock_uom)
                bom_item_row.stock_uom = item_doc.stock_uom
                bom_item_row.conversion_factor = item_data.get('conversion_factor', 1.0)
                bom_item_row.qty = item_data.get('qty', 1.0)
                bom_item_row.stock_qty = bom_item_row.qty * bom_item_row.conversion_factor
                bom_item_row.rate = item_data.get('rate', 0.0)
                bom_item_row.base_rate = bom_item_row.rate
                bom_item_row.amount = bom_item_row.qty * bom_item_row.rate
                bom_item_row.base_amount = bom_item_row.amount
                bom_item_row.qty_consumed_per_unit = bom_item_row.qty
                bom_item_row.is_stock_item = item_doc.is_stock_item
                bom_item_row.include_item_in_manufacturing = 1
                bom_item_row.sourced_by_supplier = 0
                # 设置图片（优先使用参数提供的，否则从物料主档获取）
                bom_item_row.image = item_data.get('image', item_doc.image or '')
                # 设置源仓库（可选）
                if 'source_warehouse' in item_data:
                    bom_item_row.source_warehouse = item_data['source_warehouse']
        
        # 8. 保存新BOM（触发autoname生成新版本号）
        new_bom.insert(ignore_permissions=False)
        
        # 8.5 重新设置 image 字段（因为 BOM Item 的 image 字段有 fetch_from，会被自动覆盖）
        # 需要在 insert 后、submit 前手动更新数据库
        if items and isinstance(items, list):
            need_reload = False
            for item_data in items:
                if 'image' in item_data and item_data['image']:
                    item_code = item_data.get('item_code')
                    for bom_item in new_bom.items:
                        if bom_item.item_code == item_code:
                            # 直接更新数据库，绕过 fetch_from
                            frappe.db.set_value("BOM Item", bom_item.name, "image", item_data['image'])
                            need_reload = True
                            break
            
            # 如果更新了 image，需要提交并重新加载文档
            if need_reload:
                frappe.db.commit()
                new_bom.reload()
        
        # 9. 提交新BOM（设置为已提交状态）
        new_bom.submit()
        
        # 10. 返回结果
        return {
            "status": "success",
            "message": f"成功创建并提交BOM新版本: {new_bom.name}",
            "data": {
                "original_bom": bom_name,
                "new_bom": new_bom.name,
                "new_bom_doc": new_bom.as_dict()
            }
        }
        
    except frappe.PermissionError as e:
        return {
            "status": "error",
            "message": f"权限不足: {str(e)}"
        }
    except Exception as e:
        frappe.log_error(
            message=f"创建BOM新版本时发生错误: {str(e)}\n源BOM: {bom_name}",
            title="Create BOM Version Error"
        )
        return {
            "status": "error",
            "message": f"创建BOM新版本失败: {str(e)}"
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

3. 创建BOM新版本：
   POST /api/method/rongguan_erp.utils.api.bom.create_new_bom_version
   Body: {
       "bom_name": "BOM-ITEM-001",     # 源BOM编号（必填）
       "remarks": "材料价格调整",       # 版本说明（可选）
       "amendments": {                 # 需要修改的字段（可选）
           "quantity": 2.0,
           "allow_alternative_item": 1
       }
   }
   
   返回数据：
   {
       "status": "success",
       "message": "成功创建BOM新版本: BOM-ITEM-002",
       "data": {
           "original_bom": "BOM-ITEM-001",
           "new_bom": "BOM-ITEM-002",
           "new_bom_doc": {...}  # 完整的新BOM文档对象
       }
   }
   
   核心步骤：
   - get_doc(): 获取源BOM
   - copy_doc(): 深度复制BOM及所有子表
   - 重置状态字段：docstatus=0, is_active=0, is_default=0
   - 添加版本信息到remarks字段
   - insert(): 保存并触发autoname自动生成新版本号

4. 测试BOM展开功能：
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
