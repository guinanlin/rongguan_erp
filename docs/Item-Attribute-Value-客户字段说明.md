# Item Attribute Value — Customer 字段说明

## 字段位置

- **单据**：**Item Attribute**（物料属性）
- **区域**：子表 **Item Attribute Values**（每一行是一条 `Item Attribute Value`）
- **列名**：**Customer**（自定义字段 `customer`，Link → **Customer**）

**Desk 路径**：Stock → **Item Attribute** → 打开某属性（如「颜色」）→ 在子表 **Item Attribute Values** 各行末尾可填 **Customer**。

## 含义

- **留空**：该属性值对所有客户通用。
- **已选客户**：仅针对该客户（筛选由接口或前端实现）。

## 数据从哪里来

颜色/尺寸管理页表格数据来自 **`fetchItemsAttribute`**，对应 ERP 白名单接口：

```
GET /api/method/rongguan_erp.utils.api.items.get_items_attribute_with_value
```

返回的每条记录包含 `customer` 字段，前端可据此展示或过滤。

## 接口调用方式

| 调用方式 | 说明 |
|----------|------|
| `filters={}` 或不传 | 返回所有属性值，每条含 `customer` |
| `filters={"customer": "客户名"}` | 仅返回该客户可用的属性值（`customer` 为空或等于该客户） |

**示例（cURL）**：

```bash
# 全部
curl -H "Authorization: token xxx:yyy" "http://站点/api/method/rongguan_erp.utils.api.items.get_items_attribute_with_value"

# 仅某客户
curl -H "Authorization: token xxx:yyy" "http://站点/api/method/rongguan_erp.utils.api.items.get_items_attribute_with_value?filters=%7B%22customer%22%3A%22CustomerName%22%7D"
```

**返回示例**（每条记录的 `customer` 字段）：

```json
{
  "message": [
    {
      "name": "xxx",
      "attribute_value": "红",
      "abbr": "RED",
      "parent": "颜色",
      "customer": null,
      "item_attribute": { "is_color": 1, "is_size": 0, ... }
    },
    {
      "name": "yyy",
      "attribute_value": "蓝",
      "abbr": "BLU",
      "parent": "颜色",
      "customer": "某客户",
      "item_attribute": { ... }
    }
  ]
}
```

## 配置

`apps/rongguan_erp/rongguan_erp/rongguan_erp/custom/item_attribute_value.json`（`sync_on_migrate`）。
