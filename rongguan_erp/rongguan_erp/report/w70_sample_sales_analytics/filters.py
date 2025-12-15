# Copyright (c) 2025, Rongguan ERP and contributors
# For license information, please see license.txt

"""
数据过滤工具函数
"""

import frappe
from datetime import date, timedelta
from typing import List, Dict, Optional
from frappe.utils import getdate


def filter_by_time_range(
    data: List[Dict],
    time_range: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict]:
    """
    根据时间范围过滤数据
    
    Args:
        data: 数据列表
        time_range: 时间范围 ('3m', '6m', '12m', 'year', 'custom')
        start_date: 开始日期（ISO 格式字符串，用于 custom 模式）
        end_date: 结束日期（ISO 格式字符串，用于 custom 模式）
    
    Returns:
        过滤后的数据列表
    """
    if not time_range:
        return data
    
    if time_range == 'custom':
        if start_date and end_date:
            start = getdate(start_date)
            end = getdate(end_date)
            return [
                d for d in data
                if d.get('contract_date') and start <= getdate(d['contract_date']) <= end
            ]
    elif time_range == '3m':
        cutoff_date = date.today() - timedelta(days=90)
        return [
            d for d in data
            if d.get('contract_date') and getdate(d['contract_date']) >= cutoff_date
        ]
    elif time_range == '6m':
        cutoff_date = date.today() - timedelta(days=180)
        return [
            d for d in data
            if d.get('contract_date') and getdate(d['contract_date']) >= cutoff_date
        ]
    elif time_range == '12m':
        cutoff_date = date.today() - timedelta(days=365)
        return [
            d for d in data
            if d.get('contract_date') and getdate(d['contract_date']) >= cutoff_date
        ]
    elif time_range == 'year':
        current_year = date.today().year
        return [
            d for d in data
            if d.get('contract_date') and getdate(d['contract_date']).year == current_year
        ]
    
    return data


def filter_by_business_type(
    data: List[Dict],
    business_type: Optional[str] = None
) -> List[Dict]:
    """
    根据业务类型过滤数据
    
    Args:
        data: 数据列表
        business_type: 业务类型 ('all', '外贸', '内销')
    
    Returns:
        过滤后的数据列表
    """
    if not business_type or business_type == 'all':
        return data
    
    return [d for d in data if d.get('business_type') == business_type]


def filter_by_season(
    data: List[Dict],
    season: Optional[str] = None
) -> List[Dict]:
    """
    根据季节过滤数据
    
    Args:
        data: 数据列表
        season: 季节 ('all', '春季', '夏季', '秋季', '冬季')
    
    Returns:
        过滤后的数据列表
    """
    if not season or season == 'all':
        return data
    
    return [d for d in data if d.get('season') == season]


def filter_by_sheet_type(
    data: List[Dict],
    sheet_type: str
) -> List[Dict]:
    """
    根据工作表类型过滤数据
    
    Args:
        data: 数据列表
        sheet_type: 工作表类型 ('打样', '销样', '取消')
    
    Returns:
        过滤后的数据列表
    """
    return [d for d in data if d.get('sheet_type') == sheet_type]


def filter_by_customer(
    data: List[Dict],
    customer: Optional[str] = None
) -> List[Dict]:
    """
    根据客户过滤数据
    
    Args:
        data: 数据列表
        customer: 客户名称
    
    Returns:
        过滤后的数据列表
    """
    if not customer:
        return data
    
    return [d for d in data if d.get('customer') == customer]


def filter_by_style_number(
    data: List[Dict],
    style_number: Optional[str] = None
) -> List[Dict]:
    """
    根据款号过滤数据
    
    Args:
        data: 数据列表
        style_number: 款号
    
    Returns:
        过滤后的数据列表
    """
    if not style_number:
        return data
    
    return [d for d in data if d.get('style_number') == style_number]


def apply_filters(
    data: List[Dict],
    filters: Dict
) -> List[Dict]:
    """
    应用所有过滤器
    
    Args:
        data: 原始数据列表
        filters: 过滤条件字典
    
    Returns:
        过滤后的数据列表
    """
    result = data
    
    # 时间范围过滤
    if filters.get('time_range'):
        result = filter_by_time_range(
            result,
            filters.get('time_range'),
            filters.get('start_date'),
            filters.get('end_date')
        )
    
    # 业务类型过滤
    if filters.get('business_type'):
        result = filter_by_business_type(result, filters.get('business_type'))
    
    # 季节过滤
    if filters.get('season'):
        result = filter_by_season(result, filters.get('season'))
    
    # 客户过滤
    if filters.get('customer'):
        result = filter_by_customer(result, filters.get('customer'))
    
    # 款号过滤
    if filters.get('style_number'):
        result = filter_by_style_number(result, filters.get('style_number'))
    
    # 关键词搜索
    if filters.get('search_keyword'):
        keyword = filters.get('search_keyword').lower()
        result = [
            d for d in result
            if (
                (d.get('customer') and keyword in str(d['customer']).lower()) or
                (d.get('style_number') and keyword in str(d['style_number']).lower()) or
                (d.get('style_name') and keyword in str(d['style_name']).lower())
            )
        ]
    
    return result


def fetch_base_data(filters: Optional[Dict] = None) -> tuple:
    """
    从数据库获取基础数据
    
    Args:
        filters: 过滤条件
    
    Returns:
        (development_data, sales_data) 元组
    """
    # 构建基础查询条件
    conditions = []
    values = []
    
    if filters:
        if filters.get('time_range') == 'custom' and filters.get('start_date') and filters.get('end_date'):
            conditions.append("contract_date BETWEEN %s AND %s")
            values.extend([filters['start_date'], filters['end_date']])
        elif filters.get('time_range') == '3m':
            conditions.append("contract_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)")
        elif filters.get('time_range') == '6m':
            conditions.append("contract_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)")
        elif filters.get('time_range') == '12m':
            conditions.append("contract_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)")
        elif filters.get('time_range') == 'year':
            conditions.append("YEAR(contract_date) = YEAR(CURDATE())")
        
        if filters.get('business_type') and filters.get('business_type') != 'all':
            conditions.append("business_type = %s")
            values.append(filters['business_type'])
        
        if filters.get('season') and filters.get('season') != 'all':
            conditions.append("season = %s")
            values.append(filters['season'])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # 查询所有数据
    query = f"""
        SELECT 
            name,
            sheet_type,
            customer,
            style_number,
            style_name,
            business_type,
            season,
            contract_date,
            amount,
            gross_profit,
            total_cost,
            fabric_lining_cost,
            accessory_cost,
            freight_cost,
            pattern_cost,
            special_process_cost,
            production_cost,
            logistics_cost,
            management_cost,
            other_cost,
            quantity,
            unit_price
        FROM `tabW70 Sample Sales Base`
        WHERE {where_clause}
        ORDER BY contract_date DESC
    """
    
    all_data = frappe.db.sql(query, tuple(values), as_dict=True)
    
    # 分离打样和销样数据
    development_data = [d for d in all_data if d.get('sheet_type') == '打样']
    sales_data = [d for d in all_data if d.get('sheet_type') == '销样']
    
    # 应用额外的过滤条件（如搜索关键词）
    if filters:
        if filters.get('search_keyword'):
            keyword = filters.get('search_keyword').lower()
            development_data = [
                d for d in development_data
                if (
                    (d.get('customer') and keyword in str(d['customer']).lower()) or
                    (d.get('style_number') and keyword in str(d['style_number']).lower()) or
                    (d.get('style_name') and keyword in str(d.get('style_name', '')).lower())
                )
            ]
            sales_data = [
                d for d in sales_data
                if (
                    (d.get('customer') and keyword in str(d['customer']).lower()) or
                    (d.get('style_number') and keyword in str(d['style_number']).lower()) or
                    (d.get('style_name') and keyword in str(d.get('style_name', '')).lower())
                )
            ]
    
    return development_data, sales_data
