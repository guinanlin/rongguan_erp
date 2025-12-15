# Copyright (c) 2025, Rongguan ERP and contributors
# For license information, please see license.txt

"""
W70 Sample Sales Base 统计分析模块

提供客户分析、款式分析、业务对比和预警监控功能
"""

from .customer_analytics import get_customer_analytics
from .style_analytics import get_style_analytics
from .business_comparison import get_business_comparison
from .alert_monitoring import get_alert_monitoring

__all__ = [
    "get_customer_analytics",
    "get_style_analytics",
    "get_business_comparison",
    "get_alert_monitoring",
]
