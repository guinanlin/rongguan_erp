# Copyright (c) 2025, Rongguan ERP and contributors
# For license information, please see license.txt

"""
业务对比统计服务
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
    safe_divide,
    calculate_profit_margin
)


@frappe.whitelist()
def get_business_comparison(
    time_range: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    season: Optional[str] = None
) -> Dict:
    """
    获取业务对比统计数据
    
    Args:
        time_range: 时间范围 ('3m', '6m', '12m', 'year', 'custom')
        start_date: 开始日期（ISO 格式字符串，用于 custom 模式）
        end_date: 结束日期（ISO 格式字符串，用于 custom 模式）
        season: 季节 ('all', '春季', '夏季', '秋季', '冬季')
    
    Returns:
        业务对比统计数据
    """
    try:
        # 构建过滤条件
        filters = {
            'time_range': time_range,
            'start_date': start_date,
            'end_date': end_date,
            'season': season
        }
        
        # 获取基础数据
        development_data, sales_data = fetch_base_data(filters)
        
        # 分别统计外贸和内销数据
        foreign_trade_metrics = _calculate_business_metrics(
            development_data, sales_data, '外贸'
        )
        domestic_sales_metrics = _calculate_business_metrics(
            development_data, sales_data, '内销'
        )
        
        # 计算对比明细
        comparison_details = _calculate_comparison_details(
            foreign_trade_metrics, domestic_sales_metrics
        )
        
        # 计算综合评价
        comprehensive_evaluation = _calculate_comprehensive_evaluation(
            foreign_trade_metrics, domestic_sales_metrics
        )
        
        return {
            'foreignTrade': foreign_trade_metrics,
            'domesticSales': domestic_sales_metrics,
            'comparisonDetails': comparison_details,
            'comprehensiveEvaluation': comprehensive_evaluation
        }
    
    except Exception as e:
        frappe.log_error(f"业务对比统计错误: {str(e)}", "W70 Business Comparison Error")
        frappe.throw(_("获取业务对比数据时发生错误: {0}").format(str(e)))


def _calculate_business_metrics(
    development_data: List[Dict],
    sales_data: List[Dict],
    business_type: str
) -> Dict:
    """
    计算业务类型指标
    
    Args:
        development_data: 打样数据
        sales_data: 销样数据
        business_type: 业务类型 ('外贸', '内销')
    
    Returns:
        业务指标
    """
    # 过滤该业务类型的打样数据
    dev_records = [d for d in development_data if d.get('business_type') == business_type]
    # 过滤该业务类型的销样数据
    sales_records = [d for d in sales_data if d.get('business_type') == business_type]

    # 合并该业务类型的所有记录（用于利润统计）
    all_business_records = dev_records + sales_records

    # 统计打样数据
    total_development_cost = safe_sum(dev_records, 'total_cost')
    development_style_numbers = get_unique_values(dev_records, 'style_number')
    development_style_count = len(development_style_numbers)

    # 统计所有利润数据（包括打样和销样记录中的利润）
    total_order_profit = safe_sum(all_business_records, 'gross_profit')
    total_order_amount = safe_sum(all_business_records, 'amount')
    order_count = len([r for r in all_business_records if r.get('gross_profit', 0) != 0])  # 只计算有利润的记录
    successful_style_numbers = get_unique_values(all_business_records, 'style_number')
    successful_style_count = len(successful_style_numbers)
    
    # 计算指标
    sample_development_success_rate = calculate_success_rate(
        successful_style_count, development_style_count
    ) if development_style_count > 0 else 0.0
    
    development_cost_coverage_rate = calculate_coverage_rate(
        total_order_profit, total_development_cost
    )
    
    roi = development_cost_coverage_rate  # ROI 与覆盖率相同
    
    average_order_amount = safe_divide(total_order_amount, order_count, 0.0) if order_count > 0 else 0.0
    
    average_order_profit_margin = calculate_profit_margin(
        total_order_profit, total_order_amount
    ) if total_order_amount > 0 else 0.0
    
    return {
        'businessType': business_type,
        'developmentStyleCount': development_style_count,
        'successfulStyleCount': successful_style_count,
        'sampleDevelopmentSuccessRate': round(sample_development_success_rate, 1),
        'totalDevelopmentCost': round(total_development_cost, 2),
        'totalOrderProfit': round(total_order_profit, 2),
        'developmentCostCoverageRate': round(development_cost_coverage_rate, 1),
        'roi': round(roi, 1),
        'orderCount': order_count,
        'averageOrderAmount': round(average_order_amount, 2),
        'averageOrderProfitMargin': round(average_order_profit_margin, 1)
    }


def _calculate_comparison_details(
    foreign_trade: Dict,
    domestic_sales: Dict
) -> List[Dict]:
    """
    计算对比明细
    
    Args:
        foreign_trade: 外贸业务指标
        domestic_sales: 内销业务指标
    
    Returns:
        对比明细列表
    """
    dimensions = [
        {
            'name': '打样款号数',
            'field': 'developmentStyleCount',
            'unit': '个'
        },
        {
            'name': '成功款号数',
            'field': 'successfulStyleCount',
            'unit': '个'
        },
        {
            'name': '样衣开发成功率',
            'field': 'sampleDevelopmentSuccessRate',
            'unit': '%'
        },
        {
            'name': '累计开发成本',
            'field': 'totalDevelopmentCost',
            'unit': '元'
        },
        {
            'name': '累计订单利润',
            'field': 'totalOrderProfit',
            'unit': '元'
        },
        {
            'name': '开发费用覆盖率',
            'field': 'developmentCostCoverageRate',
            'unit': '%'
        },
        {
            'name': '投资回报率',
            'field': 'roi',
            'unit': '%'
        },
        {
            'name': '订单数量',
            'field': 'orderCount',
            'unit': '个'
        },
        {
            'name': '平均订单金额',
            'field': 'averageOrderAmount',
            'unit': '元'
        },
        {
            'name': '平均订单利润率',
            'field': 'averageOrderProfitMargin',
            'unit': '%'
        }
    ]
    
    comparison_details = []
    
    for dim in dimensions:
        field = dim['field']
        foreign_value = foreign_trade.get(field, 0)
        domestic_value = domestic_sales.get(field, 0)
        
        difference = foreign_value - domestic_value
        
        # 计算差异百分比（避免除零）
        if domestic_value != 0:
            difference_percentage = (difference / abs(domestic_value)) * 100
        else:
            difference_percentage = 0.0 if foreign_value == 0 else 100.0
        
        # 判断优势方
        if foreign_value > domestic_value:
            advantage = '外贸'
        elif foreign_value < domestic_value:
            advantage = '内销'
        else:
            advantage = '持平'
        
        comparison_details.append({
            'dimension': dim['name'],
            'foreignTradeValue': round(foreign_value, 2),
            'domesticSalesValue': round(domestic_value, 2),
            'difference': round(difference, 2),
            'differencePercentage': round(difference_percentage, 1),
            'advantage': advantage,
            'unit': dim['unit']
        })
    
    return comparison_details


def _calculate_comprehensive_evaluation(
    foreign_trade: Dict,
    domestic_sales: Dict
) -> Dict:
    """
    计算综合评价
    
    Args:
        foreign_trade: 外贸业务指标
        domestic_sales: 内销业务指标
    
    Returns:
        综合评价
    """
    # 计算关键指标得分
    key_indicators = [
        'developmentCostCoverageRate',  # 开发费用覆盖率
        'sampleDevelopmentSuccessRate',  # 样衣开发成功率
        'averageOrderProfitMargin'  # 平均订单利润率
    ]
    
    foreign_score = 0
    domestic_score = 0
    
    for indicator in key_indicators:
        foreign_value = foreign_trade.get(indicator, 0)
        domestic_value = domestic_sales.get(indicator, 0)
        
        if foreign_value > domestic_value:
            foreign_score += 1
        elif domestic_value > foreign_value:
            domestic_score += 1
    
    # 判断综合优势
    if foreign_score > domestic_score:
        overall_advantage = '外贸'
        advantage_score = foreign_score
    elif domestic_score > foreign_score:
        overall_advantage = '内销'
        advantage_score = domestic_score
    else:
        overall_advantage = '持平'
        advantage_score = foreign_score
    
    return {
        'overallAdvantage': overall_advantage,
        'foreignScore': foreign_score,
        'domesticScore': domestic_score,
        'advantageScore': advantage_score,
        'totalIndicators': len(key_indicators)
    }


