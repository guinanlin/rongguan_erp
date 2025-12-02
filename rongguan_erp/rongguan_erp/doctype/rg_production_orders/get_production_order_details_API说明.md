# get_production_order_details API 说明文档

## 概述

`get_production_order_details` 是一个 whitelist 方法，用于获取生产订单（RG Production Orders）的详细信息，包括所有子表数据和关联状态信息。

## 方法签名

```python
@frappe.whitelist()
def get_production_order_details(docname)
```

## 参数

- `docname` (str): 生产订单文档的名称（必填）

## 返回值

返回一个字典，包含生产订单的所有字段和子表数据，以及以下额外计算字段：

### 新增字段：sales_order_status

**字段说明：** 根据 `order_number` 字段获取对应的销售订单（Sales Order）的 `docstatus` 状态。

**返回逻辑：**

1. **如果 `order_number` 存在且有效：**
   - 根据 `order_number` 查询 Sales Order 文档
   - 如果找到对应的销售订单，返回其 `docstatus` 原始值（整数类型）
   - 如果未找到对应的销售订单，返回 `None`

2. **如果 `order_number` 为空或不存在：**
   - 返回 `None`

3. **如果查询过程中发生异常：**
   - 记录错误日志
   - 返回 `None`

**docstatus 值说明：**
- `0`: 草稿状态（Draft）
- `1`: 已提交状态（Submitted）
- `2`: 已取消状态（Cancelled）

**返回类型：** `int` 或 `None`

## 使用示例

### API 调用

```javascript
// 前端调用示例
frappe.call({
    method: 'rongguan_erp.rongguan_erp.doctype.rg_production_orders.rg_production_orders.get_production_order_details',
    args: {
        docname: 'POM-00105'
    },
    callback: function(r) {
        if (r.message) {
            const data = r.message;
            console.log('订单号:', data.order_number);
            console.log('销售订单状态:', data.sales_order_status);
            
            // 根据状态值进行判断
            if (data.sales_order_status === 0) {
                console.log('销售订单状态：草稿');
            } else if (data.sales_order_status === 1) {
                console.log('销售订单状态：已提交');
            } else if (data.sales_order_status === 2) {
                console.log('销售订单状态：已取消');
            } else if (data.sales_order_status === null) {
                console.log('销售订单状态：未找到或未设置');
            }
        }
    }
});
```

### 返回数据示例

```json
{
    "name": "POM-00105",
    "order_number": "SAL-ORD-2025-00082",
    "sales_order_status": 1,
    "paper_pattern_status": "",
    "items": [...],
    "rg_size_details": [...],
    "rg_bom_detail_listing": [...],
    ...
}
```

## 注意事项

1. `sales_order_status` 返回的是原始 `docstatus` 值（整数），不是中文描述
2. 如果 `order_number` 对应的销售订单不存在，`sales_order_status` 为 `None`
3. 前端需要根据 `docstatus` 值自行进行状态显示和判断
4. 该方法会同时返回其他计算字段，如 `paper_pattern_status`、`rg_size_details` 等

## 相关字段

- `order_number`: 销售订单号（Sales Order 文档名称）
- `sales_order_status`: 销售订单状态（docstatus 原始值）

## 更新日期

2025-11-28








