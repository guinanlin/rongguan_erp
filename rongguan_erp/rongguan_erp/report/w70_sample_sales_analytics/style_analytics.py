# Copyright (c) 2025, Rongguan ERP and contributors
# For license information, please see license.txt

"""
款式分析统计服务
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
    calculate_profit_margin,
    calculate_profit_status,
    get_top_customers,
    safe_min,
    safe_max
)


@frappe.whitelist()
def get_style_analytics(
    time_range: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    business_type: Optional[str] = None,
    season: Optional[str] = None,
    search_keyword: Optional[str] = None
) -> Dict:
    """
    获取款式分析统计数据
    
    Args:
        time_range: 时间范围 ('3m', '6m', '12m', 'year', 'custom')
        start_date: 开始日期（ISO 格式字符串，用于 custom 模式）
        end_date: 结束日期（ISO 格式字符串，用于 custom 模式）
        business_type: 业务类型 ('all', '外贸', '内销')
        season: 季节 ('all', '春季', '夏季', '秋季', '冬季')
        search_keyword: 搜索关键词（款号、款式名称等）
    
    Returns:
        款式分析统计数据
    """
    try:
        # 构建过滤条件
        filters = {
            'time_range': time_range,
            'start_date': start_date,
            'end_date': end_date,
            'business_type': business_type,
            'season': season,
            'search_keyword': search_keyword
        }
        
        # 获取基础数据
        development_data, sales_data = fetch_base_data(filters)
        
        # 计算款式指标
        style_metrics = _calculate_style_metrics(development_data, sales_data)
        
        # 计算汇总信息
        summary = _calculate_summary(style_metrics, development_data, sales_data)
        
        # 计算盈利状态分布
        profit_status_distribution = _calculate_profit_status_distribution(style_metrics)
        
        # 获取顶级款式（按利润排序）
        top_styles = _get_top_styles_by_profit(style_metrics, limit=10)
        
        return {
            'summary': summary,
            'styles': style_metrics,
            'profitStatusDistribution': profit_status_distribution,
            'topStyles': top_styles
        }
    
    except Exception as e:
        frappe.log_error(f"款式分析统计错误: {str(e)}", "W70 Style Analytics Error")
        frappe.throw(_("获取款式分析数据时发生错误: {0}").format(str(e)))


def _calculate_style_metrics(
    development_data: List[Dict],
    sales_data: List[Dict]
) -> List[Dict]:
    """
    计算款式指标
    
    Args:
        development_data: 打样数据
        sales_data: 销样数据
    
    Returns:
        款式指标列表
    """
    # 获取所有款号
    all_style_numbers = set()
    for d in development_data:
        if d.get('style_number'):
            all_style_numbers.add(d['style_number'])
    for d in sales_data:
        if d.get('style_number'):
            all_style_numbers.add(d['style_number'])
    
    style_metrics = []
    
    for style_number in all_style_numbers:
        # 过滤该款号的打样数据
        dev_records = [d for d in development_data if d.get('style_number') == style_number]
        # 过滤该款号的销样数据
        sales_records = [d for d in sales_data if d.get('style_number') == style_number]

        # 合并该款号的所有记录（用于利润统计）
        all_style_records = dev_records + sales_records

        # 统计打样数据
        development_cost = safe_sum(dev_records, 'total_cost')
        first_development_date = safe_min(dev_records, 'contract_date')

        # 统计所有利润数据（包括打样和销样记录中的利润）
        order_profit = safe_sum(all_style_records, 'gross_profit')
        total_sales_amount = safe_sum(all_style_records, 'amount')
        order_count = len([r for r in all_style_records if r.get('gross_profit', 0) != 0])  # 只计算有利润的记录
        last_order_date = safe_max(all_style_records, 'contract_date')
        main_customers_list = get_top_customers(all_style_records, limit=3)
        
        # 计算指标
        coverage_rate = calculate_coverage_rate(order_profit, development_cost)
        average_profit_margin = calculate_profit_margin(order_profit, total_sales_amount) if total_sales_amount > 0 else 0.0
        profit_status = calculate_profit_status(coverage_rate, order_profit)
        
        # 获取款式信息（从数据中获取）
        style_name = None
        season = None
        business_type = None
        
        if sales_records:
            style_name = sales_records[0].get('style_name')
            season = sales_records[0].get('season')
            business_type = sales_records[0].get('business_type')
        elif dev_records:
            style_name = dev_records[0].get('style_name')
            season = dev_records[0].get('season')
            business_type = dev_records[0].get('business_type')
        
        style_metrics.append({
            'styleNumber': style_number,
            'styleName': style_name or '',
            'season': season or '',
            'businessType': business_type or '',
            'developmentCost': round(development_cost, 2),
            'orderProfit': round(order_profit, 2),
            'coverageRate': round(coverage_rate, 1),
            'averageProfitMargin': round(average_profit_margin, 1),
            'profitStatus': profit_status,
            'orderCount': order_count,
            'totalSalesAmount': round(total_sales_amount, 2),
            'mainCustomers': main_customers_list,
            'firstDevelopmentDate': first_development_date,
            'lastOrderDate': last_order_date
        })
    
    # 按订单利润排序
    style_metrics.sort(key=lambda x: x['orderProfit'], reverse=True)
    
    return style_metrics


def _calculate_summary(
    style_metrics: List[Dict],
    development_data: List[Dict],
    sales_data: List[Dict]
) -> Dict:
    """
    计算汇总信息
    
    Args:
        style_metrics: 款式指标列表
        development_data: 打样数据
        sales_data: 销样数据
    
    Returns:
        汇总信息
    """
    total_styles = len(style_metrics)
    
    # 盈利款式数
    profitable_styles = len([s for s in style_metrics if s.get('profitStatus') == '盈利'])
    
    # 亏损款式数
    loss_styles = len([s for s in style_metrics if s.get('profitStatus') == '亏损'])
    
    # 平均覆盖率
    if style_metrics:
        average_coverage_rate = sum(s.get('coverageRate', 0) for s in style_metrics) / len(style_metrics)
    else:
        average_coverage_rate = 0.0
    
    # 平均利润率
    if style_metrics:
        average_profit_margin = sum(s.get('averageProfitMargin', 0) for s in style_metrics) / len(style_metrics)
    else:
        average_profit_margin = 0.0
    
    # 总订单利润（从所有数据中获取，包括打样记录的利润）
    all_data = development_data + sales_data
    total_order_profit = safe_sum(all_data, 'gross_profit')
    
    return {
        'totalStyles': total_styles,
        'profitableStyles': profitable_styles,
        'lossStyles': loss_styles,
        'averageCoverageRate': round(average_coverage_rate, 1),
        'averageProfitMargin': round(average_profit_margin, 1),
        'totalOrderProfit': round(total_order_profit, 2)
    }


def _calculate_profit_status_distribution(style_metrics: List[Dict]) -> List[Dict]:
    """
    计算盈利状态分布
    
    Args:
        style_metrics: 款式指标列表
    
    Returns:
        盈利状态分布数据
    """
    status_counts = {'盈利': 0, '亏损': 0, '持平': 0}
    
    for style in style_metrics:
        status = style.get('profitStatus', '持平')
        if status in status_counts:
            status_counts[status] += 1
    
    return [
        {'status': '盈利', 'count': status_counts['盈利']},
        {'status': '亏损', 'count': status_counts['亏损']},
        {'status': '持平', 'count': status_counts['持平']}
    ]


def _get_top_styles_by_profit(
    style_metrics: List[Dict],
    limit: int = 10
) -> List[Dict]:
    """
    获取按利润排序的顶级款式
    
    Args:
        style_metrics: 款式指标列表
        limit: 返回数量限制
    
    Returns:
        顶级款式列表
    """
    sorted_styles = sorted(
        style_metrics,
        key=lambda x: x.get('orderProfit', 0),
        reverse=True
    )
    
    return [
        {
            'styleNumber': s['styleNumber'],
            'styleName': s['styleName'],
            'orderProfit': s['orderProfit'],
            'coverageRate': s['coverageRate'],
            'profitStatus': s['profitStatus']
        }
        for s in sorted_styles[:limit]
    ]
