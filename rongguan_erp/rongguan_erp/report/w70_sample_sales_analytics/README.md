# W70 Sample Sales Base 统计分析 API

本模块提供 W70 Sample Sales Base 的统计分析功能，包括客户分析、款式分析、业务对比和预警监控。

## 目录结构

```
w70_analytics/
├── __init__.py              # 模块初始化
├── filters.py               # 数据过滤工具函数
├── calculations.py          # 通用计算函数
├── customer_analytics.py     # 客户分析服务
├── style_analytics.py        # 款式分析服务
├── business_comparison.py    # 业务对比服务
└── alert_monitoring.py      # 预警监控服务
```

## API 接口

所有接口都使用 `@frappe.whitelist()` 装饰器，可通过 ERPNext API 调用。

### 1. 客户分析接口

**方法名：** `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics`

**请求参数：**
- `time_range` (可选): 时间范围 ('3m', '6m', '12m', 'year', 'custom')
- `start_date` (可选): 开始日期（ISO 格式字符串，用于 custom 模式）
- `end_date` (可选): 结束日期（ISO 格式字符串，用于 custom 模式）
- `business_type` (可选): 业务类型 ('all', '外贸', '内销')
- `search_keyword` (可选): 搜索关键词（客户名称、款号等）

**调用示例：**
```python
# 通过 API 调用
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics?time_range=12m&business_type=外贸

# 或通过 Python 代码调用
import frappe
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics',
    time_range='12m',
    business_type='外贸'
)
```

**返回数据结构：**
```json
{
  "summary": {
    "totalCustomers": 10,
    "highValueCustomers": 3,
    "highRiskCustomers": 2,
    "averageCoverageRate": 125.5,
    "averageSuccessRate": 65.2,
    "totalOrderProfit": 50000.00
  },
  "customers": [
    {
      "customer": "客户A",
      "businessType": "外贸",
      "totalDevelopmentCost": 10000.00,
      "totalOrderProfit": 15000.00,
      "coverageRate": 150.0,
      "successRate": 70.0,
      "roiRating": "B",
      "averageReturnPerStyle": 1500.00,
      "developmentStyleCount": 10,
      "successfulStyleCount": 7,
      "orderCount": 15,
      "lastOrderDate": "2025-01-15"
    }
  ],
  "ratingDistribution": [
    {"rating": "A", "count": 2},
    {"rating": "B", "count": 3},
    {"rating": "C", "count": 3},
    {"rating": "D", "count": 2}
  ],
  "topCustomers": [...]
}
```

### 2. 款式分析接口

**方法名：** `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics`

**请求参数：**
- `time_range` (可选): 时间范围
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期
- `business_type` (可选): 业务类型
- `season` (可选): 季节 ('all', '春季', '夏季', '秋季', '冬季')
- `search_keyword` (可选): 搜索关键词

**调用示例：**
```python
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics',
    time_range='6m',
    season='春季'
)
```

**返回数据结构：**
```json
{
  "summary": {
    "totalStyles": 50,
    "profitableStyles": 30,
    "lossStyles": 10,
    "averageCoverageRate": 120.5,
    "averageProfitMargin": 25.3,
    "totalOrderProfit": 100000.00
  },
  "styles": [
    {
      "styleNumber": "STYLE-001",
      "styleName": "款式名称",
      "season": "春季",
      "businessType": "外贸",
      "developmentCost": 5000.00,
      "orderProfit": 8000.00,
      "coverageRate": 160.0,
      "averageProfitMargin": 30.0,
      "profitStatus": "盈利",
      "orderCount": 5,
      "totalSalesAmount": 10000.00,
      "mainCustomers": ["客户A", "客户B", "客户C"],
      "firstDevelopmentDate": "2024-01-15",
      "lastOrderDate": "2024-12-20"
    }
  ],
  "profitStatusDistribution": [...],
  "topStyles": [...]
}
```

### 3. 业务对比接口

**方法名：** `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison`

**请求参数：**
- `time_range` (可选): 时间范围
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期
- `season` (可选): 季节

**调用示例：**
```python
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison',
    time_range='year'
)
```

**返回数据结构：**
```json
{
  "foreignTrade": {
    "businessType": "外贸",
    "developmentStyleCount": 100,
    "successfulStyleCount": 70,
    "sampleDevelopmentSuccessRate": 70.0,
    "totalDevelopmentCost": 500000.00,
    "totalOrderProfit": 750000.00,
    "developmentCostCoverageRate": 150.0,
    "roi": 150.0,
    "orderCount": 200,
    "averageOrderAmount": 10000.00,
    "averageOrderProfitMargin": 25.0
  },
  "domesticSales": {...},
  "comparisonDetails": [
    {
      "dimension": "打样款号数",
      "foreignTradeValue": 100,
      "domesticSalesValue": 80,
      "difference": 20,
      "differencePercentage": 25.0,
      "advantage": "外贸",
      "unit": "个"
    }
  ],
  "comprehensiveEvaluation": {
    "overallAdvantage": "外贸",
    "foreignScore": 2,
    "domesticScore": 1,
    "advantageScore": 2,
    "totalIndicators": 3
  }
}
```

### 4. 预警监控接口

**方法名：** `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring`

**请求参数：**
- `time_range` (可选): 时间范围
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期

**调用示例：**
```python
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring',
    time_range='3m'
)
```

**返回数据结构：**
```json
{
  "summary": {
    "highRiskCustomerCount": 5,
    "lowProfitOrderCount": 10,
    "noOrderCustomerCount": 3,
    "abnormalCostCount": 8
  },
  "highRiskCustomers": [
    {
      "customer": "客户X",
      "coverageRate": 30.0,
      "totalDevelopmentCost": 20000.00,
      "totalOrderProfit": 6000.00,
      "riskLevel": "高风险"
    }
  ],
  "lowProfitOrders": [...],
  "noOrderCustomers": [...],
  "abnormalCosts": [...]
}
```

## 计算公式

### 客户分析

1. **开发费用覆盖率** = (累计订单利润 / 累计开发成本) × 100
2. **样衣开发成功率** = (成功款号数 / 打样款号数) × 100
3. **投资回报评级**：
   - A: 覆盖率 >= 200%
   - B: 覆盖率 >= 150%
   - C: 覆盖率 >= 100%
   - D: 覆盖率 < 100%
4. **单款样衣平均回报** = 累计订单利润 / 打样款号数

### 款式分析

1. **开发费用覆盖率** = (订单利润 / 开发成本) × 100
2. **订单平均利润率** = (订单利润 / 订单总金额) × 100
3. **盈利状态判断**：
   - 盈利: 覆盖率 >= 110% 且 订单利润 > 0
   - 亏损: 覆盖率 < 90% 或 订单利润 < 0
   - 持平: 其他情况

### 预警规则

1. **高风险客户**：开发费用覆盖率 < 50%
2. **低利润订单**：利润率 < 10%
3. **无订单客户**：有打样记录但无销样记录
4. **异常成本**：某项成本超过平均值2倍

## 注意事项

1. 所有金额字段保留 2 位小数
2. 所有百分比字段保留 1 位小数
3. 除零错误已处理，返回默认值 0
4. 空数据返回空列表或默认值
5. 日期字段使用 ISO 格式字符串

## 错误处理

所有接口都包含错误处理，错误信息会记录到 Frappe 错误日志中，并返回友好的错误提示。

## 性能优化建议

1. 对于大量数据，建议使用时间范围过滤
2. 可以使用缓存减少重复计算
3. 数据库查询已优化，使用索引字段进行过滤
