# Copyright (c) 2025, Rongguan ERP and contributors
# For license information, please see license.txt

"""
通用计算函数
"""

from typing import List, Dict, Optional
from frappe.utils import flt


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法，避免除零错误
    
    Args:
        numerator: 分子
        denominator: 分母
        default: 分母为0时的默认值
    
    Returns:
        计算结果
    """
    if denominator == 0 or denominator is None:
        return default
    return flt(numerator) / flt(denominator)


def calculate_coverage_rate(order_profit: float, development_cost: float) -> float:
    """
    计算开发费用覆盖率
    
    Args:
        order_profit: 订单利润
        development_cost: 开发成本
    
    Returns:
        覆盖率（百分比）
    """
    if development_cost == 0 or development_cost is None:
        return 0.0
    
    return flt(safe_divide(order_profit, development_cost, 0.0) * 100, 1)


def calculate_success_rate(successful_count: int, total_count: int) -> float:
    """
    计算成功率
    
    Args:
        successful_count: 成功数量
        total_count: 总数量
    
    Returns:
        成功率（百分比）
    """
    return flt(safe_divide(successful_count, total_count, 0.0) * 100, 1)


def calculate_roi_rating(coverage_rate: float) -> str:
    """
    计算投资回报评级
    
    Args:
        coverage_rate: 开发费用覆盖率
    
    Returns:
        评级 ('A', 'B', 'C', 'D')
    """
    if coverage_rate >= 200:
        return 'A'
    elif coverage_rate >= 150:
        return 'B'
    elif coverage_rate >= 100:
        return 'C'
    else:
        return 'D'


def calculate_profit_status(coverage_rate: float, order_profit: float) -> str:
    """
    计算盈利状态
    
    Args:
        coverage_rate: 开发费用覆盖率
        order_profit: 订单利润
    
    Returns:
        盈利状态 ('盈利', '亏损', '持平')
    """
    if coverage_rate >= 110 and order_profit > 0:
        return '盈利'
    elif coverage_rate < 90 or order_profit < 0:
        return '亏损'
    else:
        return '持平'


def calculate_profit_margin(profit: float, amount: float) -> float:
    """
    计算利润率
    
    Args:
        profit: 利润
        amount: 金额
    
    Returns:
        利润率（百分比）
    """
    return flt(safe_divide(profit, amount, 0.0) * 100, 1)


def get_unique_values(data: List[Dict], field: str) -> List[str]:
    """
    获取字段的唯一值列表
    
    Args:
        data: 数据列表
        field: 字段名
    
    Returns:
        唯一值列表
    """
    values = [d.get(field) for d in data if d.get(field)]
    return list(set(values))


def get_top_customers(data: List[Dict], limit: int = 3) -> List[str]:
    """
    获取主要客户列表（按订单金额排序）
    
    Args:
        data: 数据列表
        limit: 返回数量限制
    
    Returns:
        客户名称列表
    """
    if not data:
        return []
    
    # 按客户分组统计金额
    customer_amounts = {}
    for d in data:
        customer = d.get('customer')
        amount = flt(d.get('amount', 0))
        if customer:
            customer_amounts[customer] = customer_amounts.get(customer, 0) + amount
    
    # 按金额排序
    sorted_customers = sorted(
        customer_amounts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return [customer for customer, _ in sorted_customers[:limit]]


def safe_sum(data: List[Dict], field: str) -> float:
    """
    安全求和
    
    Args:
        data: 数据列表
        field: 字段名
    
    Returns:
        求和结果
    """
    total = 0.0
    for d in data:
        value = d.get(field)
        if value is not None:
            total += flt(value, 0.0)
    return flt(total, 2)


def safe_min(data: List[Dict], field: str) -> Optional[str]:
    """
    安全获取最小值（用于日期字段）
    
    Args:
        data: 数据列表
        field: 字段名
    
    Returns:
        最小日期值
    """
    if not data:
        return None
    
    dates = [d.get(field) for d in data if d.get(field)]
    if not dates:
        return None
    
    return min(dates)


def safe_max(data: List[Dict], field: str) -> Optional[str]:
    """
    安全获取最大值（用于日期字段）
    
    Args:
        data: 数据列表
        field: 字段名
    
    Returns:
        最大日期值
    """
    if not data:
        return None
    
    dates = [d.get(field) for d in data if d.get(field)]
    if not dates:
        return None
    
    return max(dates)
