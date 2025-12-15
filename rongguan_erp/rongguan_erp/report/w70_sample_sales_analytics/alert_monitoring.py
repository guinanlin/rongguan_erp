# Copyright (c) 2025, Rongguan ERP and contributors
# For license information, please see license.txt

"""
预警监控统计服务
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
    safe_max
)
from frappe.utils import flt


@frappe.whitelist()
def get_alert_monitoring(
    time_range: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """
    获取预警监控统计数据
    
    Args:
        time_range: 时间范围 ('3m', '6m', '12m', 'year', 'custom')
        start_date: 开始日期（ISO 格式字符串，用于 custom 模式）
        end_date: 结束日期（ISO 格式字符串，用于 custom 模式）
    
    Returns:
        预警监控统计数据
    """
    try:
        # 构建过滤条件
        filters = {
            'time_range': time_range,
            'start_date': start_date,
            'end_date': end_date
        }
        
        # 获取基础数据
        development_data, sales_data = fetch_base_data(filters)
        
        # 检测高风险客户
        high_risk_customers = _detect_high_risk_customers(development_data, sales_data)
        
        # 检测低利润订单
        low_profit_orders = _detect_low_profit_orders(sales_data)
        
        # 检测无订单客户
        no_order_customers = _detect_no_order_customers(development_data, sales_data)
        
        # 检测异常成本
        abnormal_costs = _detect_abnormal_costs(development_data)
        
        # 计算汇总信息
        summary = {
            'highRiskCustomerCount': len(high_risk_customers),
            'lowProfitOrderCount': len(low_profit_orders),
            'noOrderCustomerCount': len(no_order_customers),
            'abnormalCostCount': len(abnormal_costs)
        }
        
        return {
            'summary': summary,
            'highRiskCustomers': high_risk_customers,
            'lowProfitOrders': low_profit_orders,
            'noOrderCustomers': no_order_customers,
            'abnormalCosts': abnormal_costs
        }
    
    except Exception as e:
        frappe.log_error(f"预警监控统计错误: {str(e)}", "W70 Alert Monitoring Error")
        frappe.throw(_("获取预警监控数据时发生错误: {0}").format(str(e)))


def _detect_high_risk_customers(
    development_data: List[Dict],
    sales_data: List[Dict]
) -> List[Dict]:
    """
    检测高风险客户（覆盖率 < 50%）
    
    Args:
        development_data: 打样数据
        sales_data: 销样数据
    
    Returns:
        高风险客户列表
    """
    # 获取所有客户
    all_customers = set()
    for d in development_data:
        if d.get('customer'):
            all_customers.add(d['customer'])
    
    high_risk_customers = []
    
    for customer in all_customers:
        # 过滤该客户的打样数据
        dev_records = [d for d in development_data if d.get('customer') == customer]
        # 过滤该客户的销样数据
        sales_records = [d for d in sales_data if d.get('customer') == customer]

        # 合并该客户的所有记录（用于利润统计）
        all_customer_records = dev_records + sales_records

        if not dev_records:
            continue

        # 计算指标
        total_development_cost = safe_sum(dev_records, 'total_cost')
        total_order_profit = safe_sum(all_customer_records, 'gross_profit')
        coverage_rate = calculate_coverage_rate(total_order_profit, total_development_cost)
        
        # 如果覆盖率 < 50%，则标记为高风险
        if coverage_rate < 50:
            high_risk_customers.append({
                'customer': customer,
                'coverageRate': round(coverage_rate, 1),
                'totalDevelopmentCost': round(total_development_cost, 2),
                'totalOrderProfit': round(total_order_profit, 2),
                'riskLevel': '高风险'
            })
    
    # 按覆盖率排序（从低到高）
    high_risk_customers.sort(key=lambda x: x['coverageRate'])
    
    return high_risk_customers


def _detect_low_profit_orders(sales_data: List[Dict]) -> List[Dict]:
    """
    检测低利润订单（利润率 < 10%）
    
    Args:
        sales_data: 销样数据
    
    Returns:
        低利润订单列表
    """
    low_profit_orders = []
    
    for order in sales_data:
        amount = order.get('amount', 0)
        profit = order.get('gross_profit', 0)
        
        if amount > 0:
            from .calculations import calculate_profit_margin
            profit_margin = calculate_profit_margin(profit, amount)
            
            # 如果利润率 < 10%，则标记为低利润订单
            if profit_margin < 10:
                low_profit_orders.append({
                    'orderId': order.get('name', ''),
                    'customer': order.get('customer', ''),
                    'styleNumber': order.get('style_number', ''),
                    'amount': round(amount, 2),
                    'profit': round(profit, 2),
                    'profitMargin': round(profit_margin, 1),
                    'contractDate': order.get('contract_date')
                })
    
    # 按利润率排序（从低到高）
    low_profit_orders.sort(key=lambda x: x['profitMargin'])
    
    return low_profit_orders


def _detect_no_order_customers(
    development_data: List[Dict],
    sales_data: List[Dict]
) -> List[Dict]:
    """
    检测无订单客户（有打样但无销样）
    
    Args:
        development_data: 打样数据
        sales_data: 销样数据
    
    Returns:
        无订单客户列表
    """
    # 获取有打样的客户
    customers_with_development = set()
    for d in development_data:
        if d.get('customer'):
            customers_with_development.add(d['customer'])
    
    # 获取有销样的客户
    customers_with_sales = set()
    for d in sales_data:
        if d.get('customer'):
            customers_with_sales.add(d['customer'])
    
    # 找出有打样但无销样的客户
    no_order_customers_set = customers_with_development - customers_with_sales
    
    no_order_customers = []
    
    for customer in no_order_customers_set:
        # 过滤该客户的打样数据
        dev_records = [d for d in development_data if d.get('customer') == customer]
        
        development_style_numbers = get_unique_values(dev_records, 'style_number')
        total_development_cost = safe_sum(dev_records, 'total_cost')
        last_development_date = safe_max(dev_records, 'contract_date')
        
        no_order_customers.append({
            'customer': customer,
            'developmentStyleCount': len(development_style_numbers),
            'totalDevelopmentCost': round(total_development_cost, 2),
            'lastDevelopmentDate': last_development_date
        })
    
    # 按开发成本排序（从高到低）
    no_order_customers.sort(key=lambda x: x['totalDevelopmentCost'], reverse=True)
    
    return no_order_customers


def _detect_abnormal_costs(development_data: List[Dict]) -> List[Dict]:
    """
    检测异常成本（超过平均值2倍）
    
    Args:
        development_data: 打样数据
    
    Returns:
        异常成本列表
    """
    if not development_data:
        return []
    
    # 计算各项成本的平均值
    cost_fields = [
        ('fabric_lining_cost', '面里料费用'),
        ('accessory_cost', '辅料费用'),
        ('freight_cost', '货代费用'),
        ('pattern_cost', '纸样费'),
        ('special_process_cost', '特殊工艺费用'),
        ('production_cost', '生产费用'),
        ('logistics_cost', '物流费用'),
        ('management_cost', '管理费用'),
        ('other_cost', '其他费用')
    ]
    
    # 计算平均值
    averages = {}
    for field, _ in cost_fields:
        values = [flt(d.get(field, 0)) for d in development_data if d.get(field)]
        if values:
            averages[field] = sum(values) / len(values)
        else:
            averages[field] = 0
    
    abnormal_costs = []
    
    for record in development_data:
        for field, cost_name in cost_fields:
            cost_value = flt(record.get(field, 0))
            avg_cost = averages[field]
            
            # 如果成本值超过平均值的2倍，则标记为异常
            if avg_cost > 0 and cost_value > avg_cost * 2:
                deviation = ((cost_value / avg_cost) - 1) * 100
                
                abnormal_costs.append({
                    'recordId': record.get('name', ''),
                    'customer': record.get('customer', ''),
                    'styleNumber': record.get('style_number', ''),
                    'costType': cost_name,
                    'cost': round(cost_value, 2),
                    'averageCost': round(avg_cost, 2),
                    'deviation': round(deviation, 1),
                    'contractDate': record.get('contract_date')
                })
    
    # 按偏差百分比排序（从高到低）
    abnormal_costs.sort(key=lambda x: x['deviation'], reverse=True)
    
    return abnormal_costs


