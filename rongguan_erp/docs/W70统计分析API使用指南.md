# W70 Sample Sales Base 统计分析 API 使用指南

## 概述

本文档介绍如何通过 API 接口访问 W70 Sample Sales Base 的统计分析功能，包括客户分析、款式分析、业务对比和预警监控。

所有接口都使用 `@frappe.whitelist()` 装饰器，可以通过 HTTP 请求、Python 代码或 JavaScript 代码进行调用。

## API 接口总览

| 功能模块 | 方法名 | 描述 |
|----------|--------|------|
| 客户分析 | `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics` | 分析客户开发成本、订单利润、覆盖率等指标 |
| 款式分析 | `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics` | 分析款式盈利状况、覆盖率等指标 |
| 业务对比 | `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison` | 对比外贸与内销业务的各项指标 |
| 预警监控 | `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring` | 监控高风险客户、低利润订单等预警信息 |

## HTTP API 调用

### 1. 客户分析接口

**请求地址：**
```
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics
```

**请求参数：**
- `time_range` (可选): 时间范围 ('3m', '6m', '12m', 'year', 'custom')
- `start_date` (可选): 开始日期（ISO 格式字符串，用于 custom 模式）
- `end_date` (可选): 结束日期（ISO 格式字符串，用于 custom 模式）
- `business_type` (可选): 业务类型 ('all', '外贸', '内销')
- `search_keyword` (可选): 搜索关键词（客户名称、款号等）

**调用示例：**
```bash
# 最近12个月的外贸客户分析
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics?time_range=12m&business_type=外贸

# 自定义时间范围的客户分析
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics?time_range=custom&start_date=2024-01-01&end_date=2024-12-31
```

### 2. 款式分析接口

**请求地址：**
```
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics
```

**请求参数：**
- `time_range` (可选): 时间范围
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期
- `business_type` (可选): 业务类型
- `season` (可选): 季节 ('all', '春季', '夏季', '秋季', '冬季')
- `search_keyword` (可选): 搜索关键词

**调用示例：**
```bash
# 最近6个月春季款式分析
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics?time_range=6m&season=春季

# 外贸业务款式分析
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics?business_type=外贸
```

### 3. 业务对比接口

**请求地址：**
```
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison
```

**请求参数：**
- `time_range` (可选): 时间范围
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期
- `season` (可选): 季节

**调用示例：**
```bash
# 全年业务对比
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison?time_range=year

# 最近12个月业务对比
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison?time_range=12m
```

### 4. 预警监控接口

**请求地址：**
```
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring
```

**请求参数：**
- `time_range` (可选): 时间范围
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期

**调用示例：**
```bash
# 最近3个月预警监控
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring?time_range=3m

# 最近6个月预警监控
GET /api/method/rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring?time_range=6m
```

## Python 代码调用

### 基本用法

```python
import frappe

# 客户分析
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics',
    time_range='12m',
    business_type='外贸'
)

# 款式分析
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics',
    time_range='6m',
    season='春季'
)

# 业务对比
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison',
    time_range='year'
)

# 预警监控
result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring',
    time_range='3m'
)
```

### 带回调的调用

```python
def process_customer_analytics(result):
    if result:
        summary = result.get('summary', {})
        customers = result.get('customers', [])

        print(f"总客户数: {summary.get('totalCustomers')}")
        print(f"高价值客户: {summary.get('highValueCustomers')}")
        print(f"平均覆盖率: {summary.get('averageCoverageRate')}%")

        for customer in customers[:5]:  # 只显示前5个客户
            print(f"客户: {customer.get('customer')}, 覆盖率: {customer.get('coverageRate')}%")

# 调用并处理结果
frappe.call({
    'method': 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics',
    'args': {'time_range': '12m'},
    'callback': process_customer_analytics
})
```

## JavaScript 代码调用

### 前端调用示例

```javascript
// 客户分析
frappe.call({
    method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics',
    args: {
        time_range: '12m',
        business_type: '外贸'
    },
    callback: function(r) {
        if (r.message) {
            console.log('客户分析结果:', r.message);

            // 处理汇总信息
            var summary = r.message.summary;
            frappe.msgprint(`总客户数: ${summary.totalCustomers}`);

            // 处理客户列表
            var customers = r.message.customers;
            customers.forEach(function(customer) {
                console.log(`${customer.customer}: 覆盖率 ${customer.coverageRate}%`);
            });
        }
    }
});

// 款式分析
frappe.call({
    method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics',
    args: {
        time_range: '6m',
        season: '春季'
    },
    callback: function(r) {
        if (r.message) {
            var styles = r.message.styles;
            // 处理款式数据...
        }
    }
});

// 业务对比
frappe.call({
    method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison',
    args: {
        time_range: 'year'
    },
    callback: function(r) {
        if (r.message) {
            var foreignTrade = r.message.foreignTrade;
            var domesticSales = r.message.domesticSales;
            var comparison = r.message.comparisonDetails;
            // 处理对比数据...
        }
    }
});

// 预警监控
frappe.call({
    method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring',
    args: {
        time_range: '3m'
    },
    callback: function(r) {
        if (r.message) {
            var alerts = r.message.summary;
            frappe.msgprint(`高风险客户: ${alerts.highRiskCustomerCount} 个`);

            // 显示高风险客户详情
            var highRiskCustomers = r.message.highRiskCustomers;
            if (highRiskCustomers.length > 0) {
                console.log('高风险客户列表:', highRiskCustomers);
            }
        }
    }
});
```

### 在列表视图中的使用

```javascript
// 在 W70 Sample Sales Base 列表视图中使用
frappe.listview_settings['W70 Sample Sales Base'] = {
    refresh: function(list_view) {
        // 添加统计分析按钮
        var dropdown_menu = list_view.page.add_custom_button_group(__('统计分析'), 'fa fa-bar-chart');

        // 客户分析菜单项
        list_view.page.add_custom_menu_item(dropdown_menu, __('客户分析'), function() {
            frappe.call({
                method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics',
                args: { time_range: '12m' },
                callback: function(r) {
                    if (r.message) {
                        // 显示分析结果对话框
                        show_analytics_dialog('客户分析', r.message);
                    }
                }
            });
        }, false);

        // 其他分析菜单项...
    }
};
```

## 参数说明

### 时间范围参数 (time_range)

| 值 | 说明 |
|----|------|
| `3m` | 最近3个月 |
| `6m` | 最近6个月 |
| `12m` | 最近12个月 |
| `year` | 本年度 |
| `custom` | 自定义时间范围（需要同时提供 start_date 和 end_date） |

### 业务类型参数 (business_type)

| 值 | 说明 |
|----|------|
| `all` | 全部业务类型 |
| `外贸` | 外贸业务 |
| `内销` | 内销业务 |

### 季节参数 (season)

| 值 | 说明 |
|----|------|
| `all` | 全部季节 |
| `春季` | 春季款式 |
| `夏季` | 夏季款式 |
| `秋季` | 秋季款式 |
| `冬季` | 冬季款式 |

## 返回数据结构

### 客户分析返回格式

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

### 款式分析返回格式

```json
{
  "summary": {
    "totalStyles": 50,
    "profitableStyles": 30,
    "lossStyles": 10,
    "averageCoverageRate": 120.5,
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
      "profitStatus": "盈利",
      "orderCount": 5,
      "totalSalesAmount": 10000.00,
      "firstDevelopmentDate": "2024-01-15",
      "lastOrderDate": "2024-12-20"
    }
  ],
  "profitStatusDistribution": [...],
  "topStyles": [...]
}
```

### 业务对比返回格式

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
    "orderCount": 200,
    "averageOrderAmount": 10000.00
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

### 预警监控返回格式

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

## 注意事项

1. **认证要求**: 调用 API 需要有效的 ERPNext 会话或 API 密钥
2. **权限控制**: 用户需要有相应模块的读取权限
3. **性能考虑**: 大数据量时建议使用时间范围参数进行过滤
4. **错误处理**: API 调用失败时会返回相应的错误信息
5. **数据格式**: 金额保留2位小数，百分比保留1位小数

## 集成示例

### 定时任务调用

```python
# 每天早上8点生成日报表
import frappe
from datetime import datetime

def generate_daily_report():
    today = datetime.now().strftime('%Y-%m-%d')

    # 获取昨天的统计数据
    result = frappe.call('rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics',
        time_range='custom',
        start_date=f'{today} 00:00:00',
        end_date=f'{today} 23:59:59'
    )

    # 处理结果并发送邮件
    if result:
        # 生成报表并发送...
        pass

# 设置定时任务
frappe.utils.background_jobs.enqueue("my_app.reports.generate_daily_report", queue="long")
```

### 前端组件集成

```javascript
// 创建自定义的统计分析组件
class AnalyticsDashboard extends frappe.ui.Component {
    constructor(parent) {
        super(parent);
        this.setup();
    }

    setup() {
        this.load_data();
    }

    load_data() {
        // 并行加载多个分析数据
        Promise.all([
            this.call_api('customer_analytics'),
            this.call_api('style_analytics'),
            this.call_api('business_comparison'),
            this.call_api('alert_monitoring')
        ]).then(results => {
            this.render_dashboard(results);
        });
    }

    call_api(endpoint) {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: `rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.${endpoint}.get_${endpoint}`,
                args: { time_range: '12m' },
                callback: (r) => resolve(r.message),
                error: reject
            });
        });
    }

    render_dashboard(data) {
        // 渲染仪表板...
    }
}
```

---

*最后更新时间: 2025-01-15*
*文档版本: v1.0*