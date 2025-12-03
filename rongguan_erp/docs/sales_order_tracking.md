# 销售订单跟踪 API

## 功能说明

根据销售订单号快速获取订单的关键状态信息，用于前端跟进订单进度。

## 接口信息

**方法名**: `get_sales_order_tracking`  
**路径**: `rongguan_erp.utils.api.sales_order_tracking.get_sales_order_tracking`  
**权限**: 需要登录（`allow_guest=False`）

## 输入参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| sales_order_number | string | 是 | 销售订单号 |

## 输出结果

### 成功响应

```json
{
  "success": true,
  "data": {
    "sales_order": {
      "document_number": "SAL-ORD-2025-00001",
      "order_status": "已提交",
      "approval_no": "APP-2025-001",
      "approval_status": null
    },
    "production_order": {
      "document_number": "POM-00001",
      "order_status": "完成",
      "approval_no": null,
      "approval_status": null
    }
  }
}
```

### 字段说明

#### sales_order（销售订单）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| document_number | string | 销售订单号（单据号） |
| order_status | string | 订单状态：草稿、已提交、已取消 |
| approval_no | string/null | 审批单号，如果有值表示已通过企业微信审批 |
| approval_status | null | 审批单状态（暂时返回null，字段不存在） |

#### production_order（生产制造通知单）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| document_number | string | 生产制造通知单号（单据号） |
| order_status | string | 订单状态：待处理、审批中、已审批、进行中、完成 |
| approval_no | null | 审批单号（暂时返回null，字段不存在） |
| approval_status | null | 审批单状态（暂时返回null，字段不存在） |

**注意**：如果销售订单没有对应的生产制造通知单，`production_order` 字段不会出现在返回结果中。

### 错误响应

```json
{
  "success": false,
  "error": "错误信息"
}
```

## 测试命令

### 方式一：使用 bench console（推荐）

```bash
bench --site all console
```

然后在 console 中执行：
```python
import frappe
frappe.init(site='all')
frappe.connect()
result = frappe.call('rongguan_erp.utils.api.sales_order_tracking.get_sales_order_tracking', sales_order_number='SAL-ORD-2025-00001')
print(result)
```

### 方式二：使用 bench execute

```bash
# 使用列表格式传递参数
bench execute rongguan_erp.utils.api.sales_order_tracking.get_sales_order_tracking --args '["SAL-ORD-2025-00001"]'
```

## 使用示例

### Python 调用

```python
import frappe

result = frappe.call(
    "rongguan_erp.utils.api.sales_order_tracking.get_sales_order_tracking",
    sales_order_number="SO-25-0611-00001-00"
)

if result.get("success"):
    sales_order = result["data"]["sales_order"]
    print(f"销售订单号: {sales_order['document_number']}")
    print(f"销售订单状态: {sales_order['order_status']}")
    print(f"审批单号: {sales_order['approval_no']}")
    
    # 生产制造通知单（如果存在）
    if "production_order" in result["data"]:
        production_order = result["data"]["production_order"]
        print(f"生产制造通知单号: {production_order['document_number']}")
        print(f"生产制造通知单状态: {production_order['order_status']}")
```

### HTTP API 调用

```bash
curl -X POST http://your-site/api/method/rongguan_erp.utils.api.sales_order_tracking.get_sales_order_tracking \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{"sales_order_number": "SO-25-0611-00001-00"}'
```

