# RG Production Progress 列表筛选 — 后端说明

## 背景

- Doctype：`RG Production Progress`（`customer` 为 **Data**，常存客户编码/名称片段）。
- 仅对 `customer` 做 `LIKE` 无法稳定命中 **Customer.customer_name**（中文公司名）。
- Frappe 的 `filters` + 单一 `or_filters` 组在语义上是  
  `AND (filter1...) AND (or1 OR or2 OR ...)`，**无法**表达  
  `(款式 product OR style) AND (客户字段 OR 客户显示名)` 这类 **两组 OR 再 AND**，组合筛选时需后端专用接口。

## 1. 新增字段 `customer_name_display`

- **类型**：Data，只读，列表可见。
- **含义**：当 `customer` 等于某条 `Customer.name` 时，在 `validate` 中写入 `Customer.customer_name`，供列表 `LIKE` 与旧接口扩展。
- **历史数据**：迁移 Patch `backfill_rg_production_progress_customer_name_display` 已按 `LEFT JOIN tabCustomer` 回填。

## 2. 白名单 API（推荐：组合筛选 / 中文客户名模糊）

与 `frappe.client.get_list` / `get_count` **同一套权限**（`reportview.get_match_cond`），分页 **总数与列表 SQL 条件一致**。

| 方法 | 路径 |
|------|------|
| 列表 + total | `POST /api/method/rongguan_erp.utils.api.production_progress_list.get_production_progress_list` |
| 仅总数 | `POST /api/method/rongguan_erp.utils.api.production_progress_list.get_production_progress_count` |

### 参数

| 参数 | 说明 |
|------|------|
| `customer_eq` | 精确匹配 `customer`（对应前端「从建议选中」） |
| `customer_text` | 手输模糊：`(customer LIKE OR customer_name_display LIKE)`，子串匹配 |
| `product_text` | 款式：`(product_name LIKE OR style_code LIKE)` |
| `style_text` | 款号：仅 `style_code LIKE` |
| `fields` | JSON 数组或逗号分隔，同 `get_list`，默认含 `name` |
| `limit_start` | 偏移 |
| `limit_page_length` | 每页条数 |
| `order_by` | 默认 `modified desc`；仅允许安全字段名 + `asc`/`desc` |

多条件之间为 **AND**。模糊规则：去首尾空白、全角 ASCII 转半角；`LIKE` 对用户输入中的 `%` `_` `\` 做转义；英文比较使用 `LOWER(...)`。

### 返回

- `get_production_progress_list`：`{ "data": [...], "total": number }`
- `get_production_progress_count`：整数

### 示例

```bash
# 总数
curl -s -X POST "https://<站点>/api/method/rongguan_erp.utils.api.production_progress_list.get_production_progress_count" \
  -H "Authorization: token <api_key>:<api_secret>" \
  -H "Content-Type: application/json" \
  -d '{"customer_text":"某某公司","product_text":"连衣裙"}'

# 列表
curl -s -X POST "https://<站点>/api/method/rongguan_erp.utils.api.production_progress_list.get_production_progress_list" \
  -H "Authorization: token <api_key>:<api_secret>" \
  -H "Content-Type: application/json" \
  -d '{"customer_text":"某某","limit_start":0,"limit_page_length":20,"fields":"[\"name\",\"customer\",\"customer_name_display\",\"style_code\",\"product_name\"]"}'
```

## 3. 仍使用 `frappe.client.get_list` 时

- **仅客户手输、且未与「款式」的 OR 冲突**：可把原来的 `customer` 一条 `LIKE` 拆成 `or_filters` 两条：  
  `["customer", "like", ...]` 与 `["customer_name_display", "like", ...]`，**不要**与「款式」的 `or_filters` 混在同一组（见上文语义限制）。
- **组合筛选**：请改用第 2 节 API，由 FastAPI 代理转发。

## 4. 与编辑/权限

- 列表数据第二次经 `frappe.get_list` 拉字段，仍走 **读权限与字段级权限**。
- `customer_name_display` 只读，保存时由 `validate` 自动维护，与现有单元格编辑 **无冲突**（不依赖用户手改该字段）。

---

**文档版本**：2025-03-21
