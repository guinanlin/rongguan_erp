import frappe

def test_stock_calculation():
    item_code = "STO-ITEM-2025-00038-红"
    
    # 查询Bin表中的原始数据，增加reserved_qty_for_production字段
    bin_data = frappe.db.sql("""
        SELECT 
            SUM(actual_qty) as actual_qty,
            SUM(projected_qty) as projected_qty,
            SUM(reserved_qty) as reserved_qty,
            SUM(ordered_qty) as ordered_qty,
            SUM(planned_qty) as planned_qty,
            SUM(reserved_qty_for_production) as reserved_qty_for_production
        FROM `tabBin` 
        WHERE item_code = %s
    """, (item_code,), as_dict=True)
    
    print("=== 原始Bin数据（包含reserved_qty_for_production）===")
    print(f"Bin查询结果: {bin_data}")
    
    if bin_data and bin_data[0]:
        data = bin_data[0]
        actual_qty = data.actual_qty or 0
        projected_qty = data.projected_qty or 0
        reserved_qty = data.reserved_qty or 0
        ordered_qty = data.ordered_qty or 0
        planned_qty = data.planned_qty or 0
        reserved_qty_for_production = data.reserved_qty_for_production or 0
        
        print(f"\n=== 详细数据 ===")
        print(f"实际库存 (actual_qty): {actual_qty}")
        print(f"预计库存 (projected_qty): {projected_qty}")
        print(f"预留库存 (reserved_qty): {reserved_qty}")
        print(f"已订购数量 (ordered_qty): {ordered_qty}")
        print(f"计划库存 (planned_qty): {planned_qty}")
        print(f"生产预留库存 (reserved_qty_for_production): {reserved_qty_for_production}")
        
        # 查询Material Request的待处理数量
        material_request_pending = frappe.db.sql("""
            SELECT 
                SUM(mri.qty - mri.ordered_qty) as pending_qty
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mri.parent = mr.name
            WHERE mri.item_code = %s
            AND mr.docstatus = 1
            AND mr.status != 'Cancelled'
        """, (item_code,), as_dict=True)
        
        requested_qty = material_request_pending[0].pending_qty if material_request_pending and material_request_pending[0] and material_request_pending[0].pending_qty is not None else 0
        print(f"Material Request待处理数量 (requested_qty): {requested_qty}")
        
        # 使用完整的ERPNext公式计算（包含Material Request）
        calculated_projected = actual_qty + ordered_qty + planned_qty - reserved_qty - reserved_qty_for_production + requested_qty
        print(f"\n=== 完整ERPNext公式计算（包含Material Request）===")
        print(f"预计库存计算公式: actual_qty + ordered_qty + planned_qty - reserved_qty - reserved_qty_for_production + requested_qty")
        print(f"计算值: {actual_qty} + {ordered_qty} + {planned_qty} - {reserved_qty} - {reserved_qty_for_production} + {requested_qty} = {calculated_projected}")
        print(f"数据库中的projected_qty: {projected_qty}")
        print(f"是否匹配: {calculated_projected == projected_qty}")
        
        # 分析差异
        difference = projected_qty - calculated_projected
        print(f"\n=== 差异分析 ===")
        print(f"差异值: {difference}")
        if difference == 0:
            print(f"✅ 完美匹配！Material Request是差异的来源")
        else:
            print(f"仍有 {difference} 的差异需要进一步调查")
        
        # 显示各组成部分的贡献
        print(f"\n=== 各组成部分分析 ===")
        print(f"实际库存贡献: +{actual_qty}")
        print(f"已订购数量贡献: +{ordered_qty}")
        print(f"计划库存贡献: +{planned_qty}")
        print(f"预留库存扣除: -{reserved_qty}")
        print(f"生产预留扣除: -{reserved_qty_for_production}")
        print(f"Material Request贡献: +{requested_qty}")
        print(f"总计: {calculated_projected}")
        
    else:
        print("未找到该物料的Bin数据")

def check_ordered_qty_detailed():
    """详细检查已订购数量的来源"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== 详细检查已订购数量 ===")
    
    # 检查采购订单明细（包括所有状态）
    print("\n1. 检查采购订单明细（所有状态）:")
    purchase_order_items = frappe.db.sql("""
        SELECT 
            poi.parent as purchase_order,
            poi.qty,
            poi.received_qty,
            poi.qty - poi.received_qty as pending_qty,
            po.status,
            po.docstatus
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE poi.item_code = %s
    """, (item_code,), as_dict=True)
    
    total_ordered = 0
    print(f"采购订单明细数量: {len(purchase_order_items)}")
    for poi in purchase_order_items:
        pending_qty = poi.pending_qty or 0
        total_ordered += pending_qty
        print(f"  - {poi.purchase_order}: 订购{poi.qty}，已收货{poi.received_qty}，待收货{pending_qty}，状态{poi.status}，文档状态{poi.docstatus}")
    
    print(f"\n总待收货数量: {total_ordered}")
    
    # 检查其他可能影响ordered_qty的订单
    print("\n2. 检查其他订单类型:")
    
    # 检查销售订单（作为预留）
    sales_orders = frappe.db.sql("""
        SELECT 
            soi.parent as sales_order,
            soi.qty,
            soi.delivered_qty,
            soi.qty - soi.delivered_qty as pending_delivery,
            so.status,
            so.docstatus
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON soi.parent = so.name
        WHERE soi.item_code = %s
    """, (item_code,), as_dict=True)
    
    print(f"销售订单数量: {len(sales_orders)}")
    for so in sales_orders:
        pending_delivery = so.pending_delivery or 0
        print(f"  - {so.sales_order}: 销售{so.qty}，已发货{so.delivered_qty}，待发货{pending_delivery}，状态{so.status}")
    
    # 检查生产订单
    production_orders = frappe.db.sql("""
        SELECT 
            name,
            qty,
            produced_qty,
            qty - produced_qty as pending_production,
            status,
            docstatus
        FROM `tabProduction Order` 
        WHERE production_item = %s
    """, (item_code,), as_dict=True)
    
    print(f"生产订单数量: {len(production_orders)}")
    for po in production_orders:
        pending_production = po.pending_production or 0
        print(f"  - {po.name}: 计划{po.qty}，已生产{po.produced_qty}，待生产{pending_production}，状态{po.status}")
    
    # 检查Bin表中的ordered_qty
    bin_ordered = frappe.db.sql("""
        SELECT SUM(ordered_qty) as total_ordered_qty
        FROM `tabBin` 
        WHERE item_code = %s
    """, (item_code,), as_dict=True)
    
    bin_ordered_qty = bin_ordered[0].total_ordered_qty if bin_ordered and bin_ordered[0] else 0
    print(f"\nBin表中的ordered_qty: {bin_ordered_qty}")
    
    # 比较差异
    difference = bin_ordered_qty - total_ordered
    print(f"差异: {difference}")
    
    # 检查是否有其他表影响ordered_qty
    print(f"\n3. 检查其他可能影响ordered_qty的表:")
    
    # 检查库存调整
    stock_entries = frappe.db.sql("""
        SELECT 
            sed.parent as stock_entry,
            sed.item_code,
            sed.qty,
            se.stock_entry_type,
            se.purpose,
            se.docstatus
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON sed.parent = se.name
        WHERE sed.item_code = %s
        AND se.docstatus = 1
    """, (item_code,), as_dict=True)
    
    print(f"库存调整数量: {len(stock_entries)}")
    for se in stock_entries:
        print(f"  - {se.stock_entry}: 数量{se.qty}，类型{se.stock_entry_type}，目的{se.purpose}")
    
    return total_ordered, bin_ordered_qty

def check_related_documents():
    """检查该物料相关的所有单据"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== 检查物料 {item_code} 相关的单据 ===")
    
    # 检查生产订单
    print("\n1. 检查生产订单（作为成品）:")
    production_orders = frappe.db.sql("""
        SELECT name, qty, produced_qty, status, planned_start_date
        FROM `tabProduction Order` 
        WHERE production_item = %s
    """, (item_code,), as_dict=True)
    print(f"生产订单数量: {len(production_orders)}")
    for po in production_orders:
        print(f"  - {po.name}: 计划{po.qty}，已生产{po.produced_qty}，状态{po.status}")
    
    # 检查工作订单（作为原料）
    print("\n2. 检查工作订单（作为原料）:")
    work_orders = frappe.db.sql("""
        SELECT wo.name, wo.production_item, woi.item_code, woi.qty, woi.consumed_qty
        FROM `tabWork Order` wo
        JOIN `tabWork Order Item` woi ON wo.name = woi.parent
        WHERE woi.item_code = %s
    """, (item_code,), as_dict=True)
    print(f"工作订单数量: {len(work_orders)}")
    for wo in work_orders:
        print(f"  - {wo.name}: 生产{wo.production_item}，需要{wo.qty}，已消耗{wo.consumed_qty}")
    
    # 检查采购订单
    print("\n3. 检查采购订单:")
    purchase_orders = frappe.db.sql("""
        SELECT poi.parent, poi.qty, poi.received_qty, po.status
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE poi.item_code = %s
    """, (item_code,), as_dict=True)
    print(f"采购订单数量: {len(purchase_orders)}")
    for po in purchase_orders:
        print(f"  - {po.parent}: 订购{po.qty}，已收货{po.received_qty}，状态{po.status}")
    
    # 检查销售订单
    print("\n4. 检查销售订单:")
    sales_orders = frappe.db.sql("""
        SELECT soi.parent, soi.qty, soi.delivered_qty, so.status
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON soi.parent = so.name
        WHERE soi.item_code = %s
    """, (item_code,), as_dict=True)
    print(f"销售订单数量: {len(sales_orders)}")
    for so in sales_orders:
        print(f"  - {so.parent}: 销售{so.qty}，已发货{so.delivered_qty}，状态{so.status}")

def check_waiting_qty():
    """检查ERPNext中waiting_qty的计算逻辑"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== 检查waiting_qty的计算逻辑 ===")
    
    # 检查采购订单（待收货）
    print("\n1. 采购订单待收货数量:")
    purchase_pending = frappe.db.sql("""
        SELECT 
            SUM(poi.qty - poi.received_qty) as pending_qty
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE poi.item_code = %s
        AND po.docstatus = 1
        AND po.status != 'Cancelled'
    """, (item_code,), as_dict=True)
    
    purchase_pending_qty = purchase_pending[0].pending_qty if purchase_pending and purchase_pending[0] and purchase_pending[0].pending_qty is not None else 0
    print(f"采购订单待收货: {purchase_pending_qty}")
    
    # 检查生产计划（计划产出）
    print("\n2. 生产计划数量:")
    production_plan_pending = frappe.db.sql("""
        SELECT 
            SUM(total_planned_qty - total_produced_qty) as pending_qty
        FROM `tabProduction Plan` 
        WHERE item_code = %s
        AND docstatus = 1
        AND status != 'Cancelled'
    """, (item_code,), as_dict=True)
    
    production_plan_pending_qty = production_plan_pending[0].pending_qty if production_plan_pending and production_plan_pending[0] and production_plan_pending[0].pending_qty is not None else 0
    print(f"生产计划数量: {production_plan_pending_qty}")
    
    # 检查库存调整（待处理）
    print("\n3. 库存调整待处理数量:")
    stock_entry_pending = frappe.db.sql("""
        SELECT 
            SUM(sed.qty) as pending_qty
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON sed.parent = se.name
        WHERE sed.item_code = %s
        AND se.docstatus = 0
        AND se.stock_entry_type IN ('Material Receipt', 'Material Issue', 'Material Transfer')
    """, (item_code,), as_dict=True)
    
    stock_entry_pending_qty = stock_entry_pending[0].pending_qty if stock_entry_pending and stock_entry_pending[0] and stock_entry_pending[0].pending_qty is not None else 0
    print(f"库存调整待处理: {stock_entry_pending_qty}")
    
    # 检查销售订单（作为预留）
    print("\n4. 销售订单预留数量:")
    sales_reserved = frappe.db.sql("""
        SELECT 
            SUM(soi.qty - soi.delivered_qty) as reserved_qty
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON soi.parent = so.name
        WHERE soi.item_code = %s
        AND so.docstatus = 1
        AND so.status != 'Cancelled'
    """, (item_code,), as_dict=True)
    
    sales_reserved_qty = sales_reserved[0].reserved_qty if sales_reserved and sales_reserved[0] and sales_reserved[0].reserved_qty is not None else 0
    print(f"销售订单预留: {sales_reserved_qty}")
    
    # 检查生产订单（作为成品产出）
    print("\n5. 生产订单计划产出:")
    production_order_pending = frappe.db.sql("""
        SELECT 
            SUM(qty - produced_qty) as pending_qty
        FROM `tabProduction Order` 
        WHERE production_item = %s
        AND docstatus = 1
        AND status != 'Cancelled'
    """, (item_code,), as_dict=True)
    
    production_order_pending_qty = production_order_pending[0].pending_qty if production_order_pending and production_order_pending[0] and production_order_pending[0].pending_qty is not None else 0
    print(f"生产订单计划产出: {production_order_pending_qty}")
    
    # 计算总的waiting_qty（包含所有可能的来源）
    total_waiting = purchase_pending_qty + production_plan_pending_qty + stock_entry_pending_qty + production_order_pending_qty
    print(f"\n=== 总计 ===")
    print(f"采购待收货: {purchase_pending_qty}")
    print(f"生产计划: {production_plan_pending_qty}")
    print(f"库存调整待处理: {stock_entry_pending_qty}")
    print(f"生产订单计划产出: {production_order_pending_qty}")
    print(f"总waiting_qty: {total_waiting}")
    print(f"ERPNext界面显示: 496")
    print(f"差异: {496 - total_waiting}")
    
    # 如果还有差异，检查是否有其他单据类型
    if 496 - total_waiting != 0:
        print(f"\n=== 继续查找差异来源 ===")
        print(f"还有 {496 - total_waiting} 的差异需要查找")
        
        # 检查所有相关的单据
        print("\n6. 检查所有相关单据:")
        all_docs = frappe.db.sql("""
            SELECT 'Purchase Order' as doctype, poi.parent as doc_name, poi.qty, poi.received_qty, poi.qty - poi.received_qty as pending
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.item_code = %s AND po.docstatus = 1
            UNION ALL
            SELECT 'Production Order' as doctype, name as doc_name, qty, produced_qty, qty - produced_qty as pending
            FROM `tabProduction Order`
            WHERE production_item = %s AND docstatus = 1
            UNION ALL
            SELECT 'Sales Order' as doctype, soi.parent as doc_name, soi.qty, soi.delivered_qty, soi.qty - soi.delivered_qty as pending
            FROM `tabSales Order Item` soi
            JOIN `tabSales Order` so ON soi.parent = so.name
            WHERE soi.item_code = %s AND so.docstatus = 1
        """, (item_code, item_code, item_code), as_dict=True)
        
        print(f"所有相关单据数量: {len(all_docs)}")
        for doc in all_docs:
            if doc.pending and doc.pending > 0:
                print(f"  - {doc.doctype}: {doc.doc_name}, 待处理: {doc.pending}")
    
    return total_waiting

def check_all_stock_quantities():
    """检查所有库存相关数量"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== 完整库存数量分析 ===")
    
    # 获取Bin表数据
    bin_data = frappe.db.sql("""
        SELECT 
            SUM(actual_qty) as actual_qty,
            SUM(projected_qty) as projected_qty,
            SUM(reserved_qty) as reserved_qty,
            SUM(ordered_qty) as ordered_qty,
            SUM(planned_qty) as planned_qty,
            SUM(reserved_qty_for_production) as reserved_qty_for_production
        FROM `tabBin` 
        WHERE item_code = %s
    """, (item_code,), as_dict=True)
    
    if bin_data and bin_data[0]:
        data = bin_data[0]
        print(f"Bin表数据:")
        print(f"  actual_qty: {data.actual_qty or 0}")
        print(f"  projected_qty: {data.projected_qty or 0}")
        print(f"  reserved_qty: {data.reserved_qty or 0}")
        print(f"  ordered_qty: {data.ordered_qty or 0}")
        print(f"  planned_qty: {data.planned_qty or 0}")
        print(f"  reserved_qty_for_production: {data.reserved_qty_for_production or 0}")
    
    # 计算waiting_qty
    waiting_qty = check_waiting_qty()
    
    # 验证projected_qty计算
    actual_qty = data.actual_qty or 0
    ordered_qty = data.ordered_qty or 0
    planned_qty = data.planned_qty or 0
    reserved_qty = data.reserved_qty or 0
    reserved_qty_for_production = data.reserved_qty_for_production or 0
    
    calculated_projected = actual_qty + ordered_qty + planned_qty - reserved_qty - reserved_qty_for_production
    print(f"\n=== 预计库存验证 ===")
    print(f"计算值: {actual_qty} + {ordered_qty} + {planned_qty} - {reserved_qty} - {reserved_qty_for_production} = {calculated_projected}")
    print(f"数据库值: {data.projected_qty or 0}")
    print(f"差异: {(data.projected_qty or 0) - calculated_projected}")

def check_production_plan_structure():
    """检查Production Plan表的结构"""
    print(f"\n=== 检查Production Plan表结构 ===")
    
    try:
        # 检查表是否存在
        table_exists = frappe.db.sql("SHOW TABLES LIKE 'tabProduction Plan'")
        print(f"Production Plan表是否存在: {len(table_exists) > 0}")
        
        if len(table_exists) > 0:
            # 获取表结构
            structure = frappe.db.sql("DESCRIBE `tabProduction Plan`", as_dict=True)
            print(f"表结构:")
            for row in structure:
                print(f"  {row['Field']}: {row['Type']}")
            
            # 检查是否有相关数据
            count = frappe.db.sql("SELECT COUNT(*) as count FROM `tabProduction Plan`")
            print(f"记录数量: {count[0][0] if count else 0}")
            
            # 查看前几条记录
            records = frappe.db.sql("SELECT * FROM `tabProduction Plan` LIMIT 3", as_dict=True)
            if records:
                print(f"前3条记录的字段:")
                for key in records[0].keys():
                    print(f"  {key}")
        else:
            print("Production Plan表不存在")
            
    except Exception as e:
        print(f"查询出错: {str(e)}")

def check_stock_entry_details():
    """通过Stock Entry明细查询库存事务历史"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== 通过Stock Entry查询库存事务历史 ===")
    
    # 查询该物料的所有库存事务
    stock_entries = frappe.db.sql("""
        SELECT 
            sed.parent as stock_entry,
            sed.item_code,
            sed.qty,
            sed.s_warehouse,
            sed.t_warehouse,
            se.stock_entry_type,
            se.purpose,
            se.posting_date,
            se.posting_time,
            se.docstatus
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON sed.parent = se.name
        WHERE sed.item_code = %s
        ORDER BY se.posting_date DESC, se.posting_time DESC
    """, (item_code,), as_dict=True)
    
    print(f"库存事务总数: {len(stock_entries)}")
    
    # 按类型统计
    entry_types = {}
    total_in = 0
    total_out = 0
    
    for entry in stock_entries:
        entry_type = entry.stock_entry_type
        qty = entry.qty or 0
        
        if entry_type not in entry_types:
            entry_types[entry_type] = {
                'count': 0,
                'total_qty': 0,
                'entries': []
            }
        
        entry_types[entry_type]['count'] += 1
        entry_types[entry_type]['total_qty'] += qty
        entry_types[entry_type]['entries'].append(entry)
        
        # 判断是入库还是出库
        if entry.s_warehouse and not entry.t_warehouse:
            # 出库
            total_out += qty
        elif entry.t_warehouse and not entry.s_warehouse:
            # 入库
            total_in += qty
        elif entry.s_warehouse and entry.t_warehouse:
            # 调拨，不影响总量
            pass
    
    print(f"\n=== 库存事务统计 ===")
    print(f"总入库数量: {total_in}")
    print(f"总出库数量: {total_out}")
    print(f"净库存变化: {total_in - total_out}")
    
    print(f"\n=== 按类型统计 ===")
    for entry_type, data in entry_types.items():
        print(f"{entry_type}: {data['count']}笔, 总数量: {data['total_qty']}")
    
    # 显示该物料的所有库存事务
    print(f"\n=== 该物料的所有库存事务明细 ===")
    print(f"总共有 {len(stock_entries)} 笔库存事务")
    
    for i, entry in enumerate(stock_entries):
        print(f"\n{i+1}. {entry.stock_entry} - {entry.stock_entry_type} - 数量: {entry.qty} - 日期: {entry.posting_date} - 状态: {entry.docstatus}")
        if entry.s_warehouse:
            print(f"   从仓库: {entry.s_warehouse}")
        if entry.t_warehouse:
            print(f"   到仓库: {entry.t_warehouse}")
        if entry.purpose:
            print(f"   目的: {entry.purpose}")
    
    # 检查是否有未提交的库存事务
    pending_entries = [e for e in stock_entries if e.docstatus == 0]
    print(f"\n=== 未提交的库存事务 ===")
    print(f"未提交事务数量: {len(pending_entries)}")
    for entry in pending_entries:
        print(f"  - {entry.stock_entry}: {entry.stock_entry_type} - 数量: {entry.qty} - 状态: {entry.docstatus}")
    
    return stock_entries

def check_bin_details():
    """查询Bin表的详细信息"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== Bin表详细信息 ===")
    
    # 查询该物料在所有仓库的Bin记录
    bin_records = frappe.db.sql("""
        SELECT 
            warehouse,
            actual_qty,
            projected_qty,
            reserved_qty,
            ordered_qty,
            planned_qty,
            reserved_qty_for_production
        FROM `tabBin` 
        WHERE item_code = %s
        ORDER BY actual_qty DESC
    """, (item_code,), as_dict=True)
    
    print(f"Bin记录数量: {len(bin_records)}")
    
    for i, bin_record in enumerate(bin_records):
        print(f"\n仓库 {i+1}: {bin_record.warehouse}")
        print(f"  实际库存: {bin_record.actual_qty}")
        print(f"  预计库存: {bin_record.projected_qty}")
        print(f"  预留库存: {bin_record.reserved_qty}")
        print(f"  已订购: {bin_record.ordered_qty}")
        print(f"  计划库存: {bin_record.planned_qty}")
        print(f"  生产预留: {bin_record.reserved_qty_for_production}")
    
    return bin_records

def check_stock_ledger():
    """查询库存明细账，按时间顺序显示入库、出库和累计库存"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== 库存明细账 - {item_code} ===")
    
    # 查询该物料的所有库存事务，包括Stock Entry和Purchase Receipt
    stock_entries = frappe.db.sql("""
        SELECT 
            sed.parent as voucher_no,
            sed.item_code,
            sed.qty,
            sed.s_warehouse,
            sed.t_warehouse,
            se.stock_entry_type as voucher_type,
            se.purpose,
            se.posting_date,
            se.posting_time,
            se.docstatus
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON sed.parent = se.name
        WHERE sed.item_code = %s
        UNION ALL
        SELECT 
            pri.parent as voucher_no,
            pri.item_code,
            pri.qty,
            pri.warehouse as s_warehouse,
            pri.warehouse as t_warehouse,
            'Purchase Receipt' as voucher_type,
            'Material Receipt' as purpose,
            pr.posting_date,
            pr.posting_time,
            pr.docstatus
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
        WHERE pri.item_code = %s
        ORDER BY posting_date ASC, posting_time ASC
    """, (item_code, item_code), as_dict=True)
    
    print(f"库存事务总数: {len(stock_entries)}")
    
    # 按时间顺序计算库存明细
    running_balance = 0
    print(f"\n{'日期':<12} {'时间':<10} {'单据号':<20} {'类型':<15} {'入库':<10} {'出库':<10} {'累计库存':<12} {'仓库':<15}")
    print("-" * 100)
    
    for entry in stock_entries:
        date = str(entry.posting_date)
        time = str(entry.posting_time)
        doc_no = entry.voucher_no
        entry_type = entry.voucher_type
        qty = entry.qty or 0
        
        # 判断是入库还是出库
        in_qty = 0
        out_qty = 0
        
        if entry.voucher_type == "Purchase Receipt":
            # Purchase Receipt 总是入库
            in_qty = qty
            if entry.docstatus == 1:  # 只计算已提交的
                running_balance += qty
        elif entry.s_warehouse and not entry.t_warehouse:
            # 出库
            out_qty = qty
            if entry.docstatus == 1:  # 只计算已提交的
                running_balance -= qty
        elif entry.t_warehouse and not entry.s_warehouse:
            # 入库
            in_qty = qty
            if entry.docstatus == 1:  # 只计算已提交的
                running_balance += qty
        elif entry.s_warehouse and entry.t_warehouse:
            # 调拨，不影响总量
            pass
        
        warehouse = entry.t_warehouse or entry.s_warehouse or ""
        
        if entry.docstatus == 1:
            print(f"{date:<12} {time:<10} {doc_no:<20} {entry_type:<15} {in_qty:<10.2f} {out_qty:<10.2f} {running_balance:<12.2f} {warehouse:<15}")
        else:
            print(f"{date:<12} {time:<10} {doc_no:<20} {entry_type:<15} {'0.00':<10} {'0.00':<10} {running_balance:<12.2f} {warehouse:<15} (未提交)")
    
    print("-" * 100)
    print(f"最终累计库存: {running_balance:.2f}")
    
    # 与Bin表数据对比
    bin_data = frappe.db.sql("""
        SELECT SUM(actual_qty) as total_actual_qty
        FROM `tabBin` 
        WHERE item_code = %s
    """, (item_code,), as_dict=True)
    
    bin_actual_qty = bin_data[0].total_actual_qty if bin_data and bin_data[0] else 0
    print(f"Bin表显示实际库存: {bin_actual_qty}")
    print(f"差异: {bin_actual_qty - running_balance}")
    
    return stock_entries, running_balance, bin_actual_qty

def check_material_request():
    """检查Material Request的数量"""
    item_code = "STO-ITEM-2025-00038-红"
    
    print(f"\n=== 检查Material Request ===")
    
    # 查询Material Request
    material_requests = frappe.db.sql("""
        SELECT 
            mri.parent as material_request,
            mri.item_code,
            mri.qty,
            mri.ordered_qty,
            mri.qty - mri.ordered_qty as pending_qty,
            mr.material_request_type,
            mr.status,
            mr.docstatus
        FROM `tabMaterial Request Item` mri
        JOIN `tabMaterial Request` mr ON mri.parent = mr.name
        WHERE mri.item_code = %s
        AND mr.docstatus = 1
        AND mr.status != 'Cancelled'
    """, (item_code,), as_dict=True)
    
    print(f"Material Request数量: {len(material_requests)}")
    
    total_pending = 0
    for mr in material_requests:
        pending_qty = mr.pending_qty or 0
        total_pending += pending_qty
        print(f"  - {mr.material_request}: 申请{mr.qty}，已订购{mr.ordered_qty}，待处理{pending_qty}，类型{mr.material_request_type}，状态{mr.status}")
    
    print(f"\nMaterial Request总待处理数量: {total_pending}")
    
    # 检查是否等于117
    if total_pending == 117:
        print(f"✅ 找到差异来源！Material Request的待处理数量正好是117")
    else:
        print(f"❌ Material Request数量({total_pending})不等于117")
    
    return total_pending

if __name__ == "__main__":
    test_stock_calculation()
    check_ordered_qty_detailed()
    check_related_documents() 
    check_all_stock_quantities() 
    check_production_plan_structure() 
    check_stock_entry_details()
    check_bin_details() 
    check_stock_ledger()
    check_material_request() 