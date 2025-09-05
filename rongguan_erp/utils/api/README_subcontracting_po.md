# 委外加工服务费采购订单 API

## 概述

本模块提供了专门用于创建委外加工服务费采购订单的白名单方法。这些方法会自动使用标准的委外加工服务费物料（STO-ITEM-2025-00053），并调用标准的采购订单接口来创建委外加工服务费的采购订单。

## 功能特性

- ✅ 自动使用委外加工服务费标准物料
- ✅ 支持多种创建方式（简单、完整、字典）
- ✅ 自动设置委外加工标记
- ✅ 供应商验证功能
- ✅ 错误处理和日志记录
- ✅ 支持批量创建
- ✅ 自动计算税费和总计

## 标准物料信息

- **物料代码**: STO-ITEM-2025-00053
- **物料组**: 服务
- **物料名称**: 委外加工
- **默认费用科目**: 5403 - 机械作业 - D
- **默认成本中心**: 主 - D
- **默认仓库**: 仓库 - D

## API 方法

### 1. 创建委外加工服务费采购订单（完整版）

```python
@frappe.whitelist()
def create_subcontracting_service_purchase_order(**kwargs)
```

**参数说明:**
- `supplier` (必需): 供应商代码
- `qty` (必需): 数量
- `rate` (必需): 单价
- `supplier_name` (可选): 供应商名称（会自动获取）
- `company` (可选): 公司代码（默认使用全局默认公司）
- `transaction_date` (可选): 交易日期（默认为今天）
- `schedule_date` (可选): 计划日期（默认为7天后）
- `description` (可选): 描述
- `warehouse` (可选): 仓库（默认为"仓库 - D"）
- `cost_center` (可选): 成本中心
- `project` (可选): 项目
- `expense_account` (可选): 费用科目

**使用示例:**
```python
result = create_subcontracting_service_purchase_order(
    supplier="DLZ",
    qty=10,
    rate=100.00,
    description="服装裁剪加工服务费"
)
```

### 2. 创建委外加工服务费采购订单（简单版）

```python
@frappe.whitelist()
def create_subcontracting_service_po_simple(supplier, qty, rate, **kwargs)
```

**参数说明:**
- `supplier` (必需): 供应商代码
- `qty` (必需): 数量
- `rate` (必需): 单价
- `**kwargs`: 其他可选参数

**使用示例:**
```python
result = create_subcontracting_service_po_simple(
    supplier="DLZ",
    qty=10,
    rate=100.00,
    description="委外加工服务费"
)
```

### 3. 从字典创建委外加工服务费采购订单

```python
@frappe.whitelist()
def create_subcontracting_service_po_from_dict(data_dict=None)
```

**参数说明:**
- `data_dict`: 包含采购订单数据的字典

**使用示例:**
```python
po_data = {
    "supplier": "DLZ",
    "qty": 15,
    "rate": 120.00,
    "description": "高级定制服装加工费",
    "project": "VIP客户定制项目"
}

result = create_subcontracting_service_po_from_dict(po_data)
```

### 4. 获取委外加工服务费标准信息

```python
@frappe.whitelist()
def get_subcontracting_service_info()
```

**返回信息:**
```json
{
    "item_code": "STO-ITEM-2025-00053",
    "item_group": "服务",
    "item_name": "委外加工",
    "description": "委外加工服务费",
    "default_expense_account": "5403 - 机械作业 - D",
    "default_cost_center": "主 - D",
    "default_warehouse": "仓库 - D"
}
```

### 5. 验证供应商

```python
@frappe.whitelist()
def validate_subcontracting_supplier(supplier)
```

**参数说明:**
- `supplier`: 供应商代码

**返回信息:**
```json
{
    "valid": true,
    "supplier_name": "大连制衣厂",
    "supplier_type": "Company",
    "country": "China",
    "supplier_group": "Manufacturer"
}
```

## 使用示例

### 基本使用

```python
# 最简单的使用方式
result = create_subcontracting_service_po_simple(
    supplier="DLZ",
    qty=10,
    rate=100.00
)
```

### 带描述的使用

```python
# 添加描述信息
result = create_subcontracting_service_po_simple(
    supplier="DLZ",
    qty=5,
    rate=150.00,
    description="服装裁剪加工服务费"
)
```

### 完整参数使用

```python
# 使用所有可选参数
result = create_subcontracting_service_purchase_order(
    supplier="DLZ",
    supplier_name="大连制衣厂",
    company="DTY",
    transaction_date="2025-01-15",
    schedule_date="2025-01-22",
    qty=20,
    rate=80.00,
    description="批量服装加工服务费",
    warehouse="仓库 - D",
    cost_center="主 - D",
    project="2025春季服装项目",
    expense_account="5403 - 机械作业 - D"
)
```

### 批量创建

```python
# 批量创建多个采购订单
batch_data = [
    {"supplier": "DLZ", "qty": 10, "rate": 100.00, "description": "批次1"},
    {"supplier": "DLZ", "qty": 15, "rate": 120.00, "description": "批次2"},
    {"supplier": "DLZ", "qty": 8, "rate": 150.00, "description": "批次3"}
]

results = []
for data in batch_data:
    result = create_subcontracting_service_po_simple(**data)
    results.append(result)
```

### 供应商验证

```python
# 先验证供应商，再创建采购订单
validation_result = validate_subcontracting_supplier("DLZ")

if validation_result.get("valid"):
    result = create_subcontracting_service_po_simple(
        supplier="DLZ",
        qty=8,
        rate=90.00,
        description="验证后的委外加工服务费"
    )
else:
    print(f"供应商验证失败: {validation_result.get('message')}")
```

## 返回结果格式

### 成功创建

```json
{
    "status": "success",
    "message": "委外加工服务费采购订单已创建: PUR-ORD-2025-00001",
    "purchase_order": "PUR-ORD-2025-00001",
    "doc": {
        // 完整的采购订单文档数据
    },
    "total_amount": 1000.00,
    "base_total_amount": 1000.00
}
```

### 创建成功但提交失败

```json
{
    "status": "partial_success",
    "message": "委外加工服务费采购订单已创建但提交失败: PUR-ORD-2025-00001",
    "purchase_order": "PUR-ORD-2025-00001",
    "error": "提交错误信息",
    "doc": {
        // 完整的采购订单文档数据
    },
    "total_amount": 1000.00,
    "base_total_amount": 1000.00
}
```

### 创建失败

```json
{
    "status": "error",
    "message": "创建委外加工服务费采购订单失败: 错误信息",
    "error": "详细错误信息"
}
```

## 错误处理

### 常见错误

1. **缺少必需参数**
   - 错误: "供应商（supplier）是必需参数"
   - 解决: 确保提供 supplier、qty、rate 参数

2. **供应商不存在**
   - 错误: "供应商 DLZ 不存在"
   - 解决: 检查供应商代码是否正确

3. **供应商已禁用**
   - 错误: "供应商 DLZ 已被禁用"
   - 解决: 启用供应商或选择其他供应商

### 错误处理示例

```python
try:
    result = create_subcontracting_service_po_simple(
        supplier="DLZ",
        qty=10,
        rate=100.00
    )
    
    if result.get("status") == "success":
        print(f"采购订单创建成功: {result.get('purchase_order')}")
    elif result.get("status") == "partial_success":
        print(f"采购订单创建成功但提交失败: {result.get('error')}")
    else:
        print(f"采购订单创建失败: {result.get('error')}")
        
except Exception as e:
    print(f"发生异常: {str(e)}")
```

## 测试

### 运行测试

```bash
# 在 Frappe bench 环境中运行测试
bench --site your-site.local execute rongguan_erp.utils.api.test_subcontracting_po.run_all_tests
```

### 运行示例

```bash
# 运行使用示例
bench --site your-site.local execute rongguan_erp.utils.api.subcontracting_po_examples.run_all_examples
```

## 注意事项

1. **物料代码**: 确保 STO-ITEM-2025-00053 物料在系统中存在
2. **供应商**: 确保供应商在系统中存在且未被禁用
3. **权限**: 确保用户有创建采购订单的权限
4. **公司设置**: 确保公司设置正确，包括默认货币等
5. **仓库**: 确保指定的仓库存在
6. **成本中心**: 确保指定的成本中心存在
7. **费用科目**: 确保指定的费用科目存在

## 相关文件

- `purchase_order_core.py`: 主要实现文件
- `test_subcontracting_po.py`: 测试文件
- `subcontracting_po_examples.py`: 使用示例文件
- `README_subcontracting_po.md`: 本文档

## 更新日志

- **v1.0.0**: 初始版本，支持基本的委外加工服务费采购订单创建功能
- 支持多种创建方式
- 支持供应商验证
- 支持错误处理和日志记录 