"""
测试脚本：get_items_by_sku_and_color

使用方法：
1. 通过 bench 命令测试：
   bench --site site1.local execute rongguan_erp.utils.api.item.item_api_for_agent.get_items_by_sku_and_color --kwargs '{"items_data": [{"sku_code": "zNF-16-RED", "color": "红"}]}'

2. 通过 Python 脚本测试：
   python -c "import frappe; frappe.connect('site1.local'); from rongguan_erp.utils.api.item.item_api_for_agent import get_items_by_sku_and_color; print(get_items_by_sku_and_color([{'sku_code': 'zNF-16-RED', 'color': '红'}]))"

3. 通过 API 调用（需要认证）：
   POST http://your-site/api/method/rongguan_erp.utils.api.item.item_api_for_agent.get_items_by_sku_and_color
   Headers: Authorization: token api_key:api_secret
   Body: {"items_data": [{"sku_code": "zNF-16-RED", "color": "红"}]}
"""

import json
import frappe
from rongguan_erp.utils.api.item.item_api_for_agent import get_items_by_sku_and_color


def test_single_item():
    """测试单个item查询"""
    print("=" * 50)
    print("测试单个item查询")
    print("=" * 50)
    
    items_data = [
        {"sku_code": "zNF-16-RED", "color": "红"}
    ]
    
    result = get_items_by_sku_and_color(items_data)
    print(f"查询结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result


def test_multiple_items():
    """测试批量item查询"""
    print("=" * 50)
    print("测试批量item查询")
    print("=" * 50)
    
    items_data = [
        {"sku_code": "zNF-16-RED", "color": "红"},
        {"sku_code": "不存在的SKU", "color": "蓝色"},
        {"sku_code": "zNF-16-RED", "color": "不存在的颜色"}
    ]
    
    result = get_items_by_sku_and_color(items_data)
    print(f"查询结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result


def test_empty_sku():
    """测试空SKU的情况"""
    print("=" * 50)
    print("测试空SKU的情况")
    print("=" * 50)
    
    items_data = [
        {"sku_code": "", "color": "红"}
    ]
    
    result = get_items_by_sku_and_color(items_data)
    print(f"查询结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result


if __name__ == "__main__":
    # 连接 Frappe 站点（需要根据实际情况修改站点名称）
    # frappe.connect('site1.local')
    
    try:
        # 测试1: 单个item查询
        test_single_item()
        
        print("\n")
        
        # 测试2: 批量查询
        test_multiple_items()
        
        print("\n")
        
        # 测试3: 空SKU
        test_empty_sku()
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
