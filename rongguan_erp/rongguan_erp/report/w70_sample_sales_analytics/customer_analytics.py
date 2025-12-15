# Copyright (c) 2025, Rongguan ERP and contributors
# For license information, please see license.txt

"""
客户分析统计服务
"""

import frappe
import json
from typing import Dict, List, Optional
from frappe import _

from .filters import fetch_base_data, apply_filters
from .calculations import (
    safe_sum,
    get_unique_values,
    calculate_coverage_rate,
    calculate_success_rate,
    calculate_roi_rating,
    safe_max
)


@frappe.whitelist()
def get_customer_analytics(
    time_range: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    business_type: Optional[str] = None,
    search_keyword: Optional[str] = None
) -> Dict:
    """
    获取客户分析统计数据
    
    Args:
        time_range: 时间范围 ('3m', '6m', '12m', 'year', 'custom')
        start_date: 开始日期（ISO 格式字符串，用于 custom 模式）
        end_date: 结束日期（ISO 格式字符串，用于 custom 模式）
        business_type: 业务类型 ('all', '外贸', '内销')
        search_keyword: 搜索关键词（客户名称、款号等）
    
    Returns:
        客户分析统计数据
    """
    try:
        # 构建过滤条件
        filters = {
            'time_range': time_range,
            'start_date': start_date,
            'end_date': end_date,
            'business_type': business_type,
            'search_keyword': search_keyword
        }
        
        # 获取基础数据
        development_data, sales_data = fetch_base_data(filters)
        
        # 计算客户指标
        customer_metrics = _calculate_customer_metrics(development_data, sales_data)
        
        # 计算汇总信息
        summary = _calculate_summary(customer_metrics, development_data, sales_data)
        
        # 计算评级分布
        rating_distribution = _calculate_rating_distribution(customer_metrics)
        
        # 获取顶级客户（按利润排序）
        top_customers = _get_top_customers_by_profit(customer_metrics, limit=10)
        
        return {
            'summary': summary,
            'customers': customer_metrics,
            'ratingDistribution': rating_distribution,
            'topCustomers': top_customers
        }
    
    except Exception as e:
        frappe.log_error(f"客户分析统计错误: {str(e)}", "W70 Customer Analytics Error")
        frappe.throw(_("获取客户分析数据时发生错误: {0}").format(str(e)))


def _calculate_customer_metrics(
    development_data: List[Dict],
    sales_data: List[Dict]
) -> List[Dict]:
    """
    计算客户指标
    
    Args:
        development_data: 打样数据
        sales_data: 销样数据
    
    Returns:
        客户指标列表
    """
    # 获取所有客户
    all_customers = set()
    for d in development_data:
        if d.get('customer'):
            all_customers.add(d['customer'])
    for d in sales_data:
        if d.get('customer'):
            all_customers.add(d['customer'])
    
    customer_metrics = []
    
    for customer in all_customers:
        # 过滤该客户的打样数据
        dev_records = [d for d in development_data if d.get('customer') == customer]
        # 过滤该客户的销样数据
        sales_records = [d for d in sales_data if d.get('customer') == customer]

        # 合并该客户的所有记录（用于利润统计）
        all_customer_records = dev_records + sales_records

        # 统计打样数据
        total_development_cost = safe_sum(dev_records, 'total_cost')
        development_style_numbers = get_unique_values(dev_records, 'style_number')
        development_style_count = len(development_style_numbers)

        # 统计所有利润数据（包括打样和销样记录中的利润）
        total_order_profit = safe_sum(all_customer_records, 'gross_profit')
        order_count = len([r for r in all_customer_records if r.get('gross_profit', 0) != 0])  # 只计算有利润的记录
        successful_style_numbers = get_unique_values(all_customer_records, 'style_number')
        successful_style_count = len(successful_style_numbers)
        
        # 计算指标
        coverage_rate = calculate_coverage_rate(total_order_profit, total_development_cost)
        success_rate = calculate_success_rate(successful_style_count, development_style_count) if development_style_count > 0 else 0.0
        roi_rating = calculate_roi_rating(coverage_rate)
        average_return_per_style = total_order_profit / development_style_count if development_style_count > 0 else 0.0
        
        # 获取业务类型（从数据中获取，优先使用有利润的记录）
        business_type = None
        if all_customer_records:
            # 优先使用有利润的记录
            profitable_records = [r for r in all_customer_records if r.get('gross_profit', 0) != 0]
            if profitable_records:
                business_type = profitable_records[0].get('business_type')
            else:
                business_type = all_customer_records[0].get('business_type')
        
        # 最后订单时间
        last_order_date = safe_max(all_customer_records, 'contract_date')
        
        customer_metrics.append({
            'customer': customer,
            'businessType': business_type or '',
            'totalDevelopmentCost': round(total_development_cost, 2),
            'totalOrderProfit': round(total_order_profit, 2),
            'coverageRate': round(coverage_rate, 1),
            'successRate': round(success_rate, 1),
            'roiRating': roi_rating,
            'averageReturnPerStyle': round(average_return_per_style, 2),
            'developmentStyleCount': development_style_count,
            'successfulStyleCount': successful_style_count,
            'orderCount': order_count,
            'lastOrderDate': last_order_date
        })
    
    # 按累计订单利润排序
    customer_metrics.sort(key=lambda x: x['totalOrderProfit'], reverse=True)
    
    return customer_metrics


def _calculate_summary(
    customer_metrics: List[Dict],
    development_data: List[Dict],
    sales_data: List[Dict]
) -> Dict:
    """
    计算汇总信息
    
    Args:
        customer_metrics: 客户指标列表
        development_data: 打样数据
        sales_data: 销样数据
    
    Returns:
        汇总信息
    """
    total_customers = len(customer_metrics)
    
    # 高价值客户（覆盖率 >= 150）
    high_value_customers = len([c for c in customer_metrics if c.get('coverageRate', 0) >= 150])
    
    # 高风险客户（覆盖率 < 50）
    high_risk_customers = len([c for c in customer_metrics if c.get('coverageRate', 0) < 50])
    
    # 平均覆盖率
    if customer_metrics:
        average_coverage_rate = sum(c.get('coverageRate', 0) for c in customer_metrics) / len(customer_metrics)
    else:
        average_coverage_rate = 0.0
    
    # 平均成功率
    if customer_metrics:
        average_success_rate = sum(c.get('successRate', 0) for c in customer_metrics) / len(customer_metrics)
    else:
        average_success_rate = 0.0
    
    # 总订单利润（从所有数据中获取，包括打样记录的利润）
    all_data = development_data + sales_data
    total_order_profit = safe_sum(all_data, 'gross_profit')
    
    return {
        'totalCustomers': total_customers,
        'highValueCustomers': high_value_customers,
        'highRiskCustomers': high_risk_customers,
        'averageCoverageRate': round(average_coverage_rate, 1),
        'averageSuccessRate': round(average_success_rate, 1),
        'totalOrderProfit': round(total_order_profit, 2)
    }


def _calculate_rating_distribution(customer_metrics: List[Dict]) -> List[Dict]:
    """
    计算评级分布
    
    Args:
        customer_metrics: 客户指标列表
    
    Returns:
        评级分布数据
    """
    rating_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    
    for customer in customer_metrics:
        rating = customer.get('roiRating', 'D')
        if rating in rating_counts:
            rating_counts[rating] += 1
    
    return [
        {'rating': 'A', 'count': rating_counts['A']},
        {'rating': 'B', 'count': rating_counts['B']},
        {'rating': 'C', 'count': rating_counts['C']},
        {'rating': 'D', 'count': rating_counts['D']}
    ]


def _get_top_customers_by_profit(
    customer_metrics: List[Dict],
    limit: int = 10
) -> List[Dict]:
    """
    获取按利润排序的顶级客户
    
    Args:
        customer_metrics: 客户指标列表
        limit: 返回数量限制
    
    Returns:
        顶级客户列表
    """
    sorted_customers = sorted(
        customer_metrics,
        key=lambda x: x.get('totalOrderProfit', 0),
        reverse=True
    )
    
    return [
        {
            'customer': c['customer'],
            'totalOrderProfit': c['totalOrderProfit'],
            'coverageRate': c['coverageRate'],
            'roiRating': c['roiRating']
        }
        for c in sorted_customers[:limit]
    ]
