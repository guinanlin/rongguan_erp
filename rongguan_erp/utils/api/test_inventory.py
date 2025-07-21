import frappe
from rongguan_erp.utils.api.inventory import (
    get_stock_entries_with_items,
    get_stock_entry_detail,
    search_stock_entries
)


def test_basic_query():
    """
    测试基本查询功能
    使用方法: bench execute rongguan_erp.utils.api.test_inventory.test_basic_query
    """
    print("=== 测试基本查询功能 ===")
    
    try:
        result = get_stock_entries_with_items(page=1, page_length=5)
        
        print(f"返回结果类型: {type(result)}")
        print(f"返回结果: {result}")
        
        # 检查是否有错误
        if 'error' in result:
            print(f"❌ 查询出错: {result['error']}")
            return
        
        if isinstance(result, dict) and 'message' in result:
            message = result['message']
            
            # 检查message是否为列表
            if isinstance(message, list):
                print(f"✅ 查询成功")
                print(f"返回记录数: {len(message)}")
                
                # 安全获取分页信息
                pagination = result.get('pagination', {})
                if isinstance(pagination, dict):
                    print(f"分页信息: {pagination}")
                else:
                    print(f"分页信息类型异常: {type(pagination)}")
                    print(f"分页信息内容: {pagination}")
                
                if message:
                    first_record = message[0]
                    if isinstance(first_record, dict):
                        print(f"第一条记录: {first_record.get('name')}")
                        print(f"类型: {first_record.get('stock_entry_type')}")
                        
                        # 安全获取items
                        items = first_record.get('items', [])
                        if isinstance(items, list):
                            print(f"子表items数量: {len(items)}")
                        else:
                            print(f"子表items类型异常: {type(items)}")
                    else:
                        print(f"第一条记录类型异常: {type(first_record)}")
            else:
                print(f"❌ message不是列表: {type(message)}")
        else:
            print(f"❌ 查询失败: {result}")
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


def test_pagination():
    """
    测试分页功能
    使用方法: bench execute rongguan_erp.utils.api.test_inventory.test_pagination
    """
    print("=== 测试分页功能 ===")
    
    try:
        # 测试第一页
        result1 = get_stock_entries_with_items(page=1, page_length=3)
        print(f"第1页记录数: {len(result1.get('message', []))}")
        
        # 测试第二页
        result2 = get_stock_entries_with_items(page=2, page_length=3)
        print(f"第2页记录数: {len(result2.get('message', []))}")
        
        # 比较两页数据
        if result1.get('message') and result2.get('message'):
            first_page_names = [r['name'] for r in result1['message']]
            second_page_names = [r['name'] for r in result2['message']]
            
            # 检查是否有重复
            common = set(first_page_names) & set(second_page_names)
            if not common:
                print("✅ 分页数据无重复")
            else:
                print(f"⚠️ 发现重复数据: {common}")
        
        # 显示分页信息
        pagination = result1.get('pagination', {})
        if isinstance(pagination, dict):
            print(f"总记录数: {pagination.get('total_count')}")
            print(f"总页数: {pagination.get('total_pages')}")
            print(f"当前页: {pagination.get('current_page')}")
            print(f"每页记录数: {pagination.get('page_length')}")
        else:
            print(f"分页信息类型异常: {type(pagination)}")
        
    except Exception as e:
        print(f"❌ 分页测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


def test_filters():
    """
    测试过滤功能
    使用方法: bench execute rongguan_erp.utils.api.test_inventory.test_filters
    """
    print("=== 测试过滤功能 ===")
    
    try:
        # 测试按类型过滤
        filters = [['stock_entry_type', '=', 'Material Receipt']]
        result = get_stock_entries_with_items(page=1, page_length=10, filters=filters)
        
        print(f"Material Receipt类型记录数: {len(result.get('message', []))}")
        
        # 检查所有记录是否都是Material Receipt类型
        if result.get('message'):
            all_material_receipt = all(
                entry.get('stock_entry_type') == 'Material Receipt' 
                for entry in result['message']
            )
            
            if all_material_receipt:
                print("✅ 过滤条件生效")
            else:
                print("❌ 过滤条件未生效")
                
        # 测试多条件过滤
        multi_filters = [
            ['stock_entry_type', 'in', ['Material Receipt', 'Manufacture']],
            ['docstatus', '=', 1]
        ]
        result2 = get_stock_entries_with_items(page=1, page_length=10, filters=multi_filters)
        print(f"多条件过滤记录数: {len(result2.get('message', []))}")
        
    except Exception as e:
        print(f"❌ 过滤测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


def test_search():
    """
    测试搜索功能
    使用方法: bench execute rongguan_erp.utils.api.test_inventory.test_search
    """
    print("=== 测试搜索功能 ===")
    
    try:
        search_terms = ['MAT', 'STE', '2025', '2024']
        
        for term in search_terms:
            print(f"\n搜索关键词: '{term}'")
            result = search_stock_entries(term, page=1, page_length=5)
            
            count = len(result.get('message', []))
            print(f"搜索结果数: {count}")
            
            if result.get('message'):
                print("前3个结果:")
                for i, entry in enumerate(result['message'][:3]):
                    print(f"  {i+1}. {entry.get('name')} - {entry.get('stock_entry_type')}")
                    
                # 检查搜索结果是否包含搜索词
                names = [entry.get('name', '') for entry in result['message']]
                matching = [name for name in names if term.upper() in name.upper()]
                print(f"包含'{term}'的记录数: {len(matching)}")
        
    except Exception as e:
        print(f"❌ 搜索测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


def test_detail():
    """
    测试详情查询
    使用方法: bench execute rongguan_erp.utils.api.test_inventory.test_detail
    """
    print("=== 测试详情查询 ===")
    
    try:
        # 先获取一个Stock Entry
        result = get_stock_entries_with_items(page=1, page_length=1)
        
        if result.get('message'):
            first_entry = result['message'][0]
            entry_name = first_entry['name']
            
            print(f"查询详情: {entry_name}")
            detail = get_stock_entry_detail(entry_name)
            
            if 'message' in detail:
                stock_entry = detail['message']['stock_entry']
                items = detail['message']['items']
                
                print(f"✅ 详情查询成功")
                print(f"主表字段数: {len(stock_entry)}")
                print(f"子表items数: {len(items)}")
                
                if items:
                    print("第一个item信息:")
                    first_item = items[0]
                    print(f"  Item Code: {first_item.get('item_code')}")
                    print(f"  Qty: {first_item.get('qty')}")
                    print(f"  Warehouse: {first_item.get('warehouse')}")
            else:
                print(f"❌ 详情查询失败: {detail.get('error', '未知错误')}")
        else:
            print("❌ 没有找到可测试的Stock Entry")
            
    except Exception as e:
        print(f"❌ 详情测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


def test_data_structure():
    """
    测试数据结构
    使用方法: bench execute rongguan_erp.utils.api.test_inventory.test_data_structure
    """
    print("=== 测试数据结构 ===")
    
    try:
        result = get_stock_entries_with_items(page=1, page_length=1)
        
        if result.get('message'):
            record = result['message'][0]
            
            print("主表字段:")
            for key, value in record.items():
                if key != 'items':
                    print(f"  {key}: {type(value).__name__} = {value}")
            
            # 安全获取items
            items = record.get('items', [])
            if isinstance(items, list):
                print(f"\n子表items数量: {len(items)}")
                
                if items:
                    print("子表字段:")
                    first_item = items[0]
                    for key, value in first_item.items():
                        print(f"  {key}: {type(value).__name__} = {value}")
            else:
                print(f"子表items类型异常: {type(items)}")
            
            # 安全获取分页信息
            pagination = result.get('pagination', {})
            if isinstance(pagination, dict):
                print(f"\n分页信息:")
                for key, value in pagination.items():
                    print(f"  {key}: {value}")
            else:
                print(f"分页信息类型异常: {type(pagination)}")
                
    except Exception as e:
        print(f"❌ 数据结构测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


def test_all():
    """
    运行所有测试
    使用方法: bench execute rongguan_erp.utils.api.test_inventory.test_all
    """
    print("🚀 开始运行所有测试...\n")
    
    tests = [
        test_basic_query,
        test_pagination,
        test_filters,
        test_search,
        test_detail,
        test_data_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
            print("✅ 测试通过\n")
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}\n")
    
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
