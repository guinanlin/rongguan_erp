// Copyright (c) 2025, Rongguan ERP and contributors
// For license information, please see license.txt

frappe.listview_settings['W70 Sample Sales Base'] = {
	refresh: function(list_view) {
		console.log('[统计分析] refresh 被调用');

		// 检查是否已经添加过统计分析按钮组
		var existing = list_view.page.custom_actions.find('.custom-btn-group').filter(function() {
			var label = $(this).find('.custom-btn-group-label').text().trim();
			return label === __('统计分析') || label === '统计分析';
		});

		if (existing.length > 0) {
			console.log('[统计分析] 按钮组已存在，跳过');
			return;
		}

		console.log('[统计分析] 开始添加按钮组');

		// 添加统计分析下拉按钮组
		var dropdown_menu = list_view.page.add_custom_button_group(__('统计分析'), 'fa fa-bar-chart');
		console.log('[统计分析] 按钮组已添加，dropdown_menu:', dropdown_menu);

		// 添加客户分析菜单项
		list_view.page.add_custom_menu_item(dropdown_menu, __('客户分析'), function() {
			console.log('[统计分析] 点击了客户分析');
			frappe.call({
				method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.customer_analytics.get_customer_analytics',
				args: {
					time_range: '12m'
				},
				callback: function(r) {
					if (r.message) {
						var dialog = new frappe.ui.Dialog({
							title: __('客户分析'),
							fields: [
								{
									fieldtype: 'HTML',
									options: '<div id="customer-analytics-content"></div>'
								}
							],
							size: 'extra-large'
						});

						var content = format_customer_analytics(r.message);
						dialog.$wrapper.find('#customer-analytics-content').html(content);
						dialog.show();
					}
				}
			});
		}, false);

		// 添加款式分析菜单项
		list_view.page.add_custom_menu_item(dropdown_menu, __('款式分析'), function() {
			console.log('[统计分析] 点击了款式分析');
			frappe.call({
				method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.style_analytics.get_style_analytics',
				args: {
					time_range: '12m'
				},
				callback: function(r) {
					if (r.message) {
						var dialog = new frappe.ui.Dialog({
							title: __('款式分析'),
							fields: [
								{
									fieldtype: 'HTML',
									options: '<div id="style-analytics-content"></div>'
								}
							],
							size: 'extra-large'
						});

						var content = format_style_analytics(r.message);
						dialog.$wrapper.find('#style-analytics-content').html(content);
						dialog.show();
					}
				}
			});
		}, false);

		// 添加业务对比菜单项
		list_view.page.add_custom_menu_item(dropdown_menu, __('业务对比'), function() {
			console.log('[统计分析] 点击了业务对比');
			frappe.call({
				method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.business_comparison.get_business_comparison',
				args: {
					time_range: '12m'
				},
				callback: function(r) {
					if (r.message) {
						var dialog = new frappe.ui.Dialog({
							title: __('业务对比'),
							fields: [
								{
									fieldtype: 'HTML',
									options: '<div id="business-comparison-content"></div>'
								}
							],
							size: 'extra-large'
						});

						var content = format_business_comparison(r.message);
						dialog.$wrapper.find('#business-comparison-content').html(content);
						dialog.show();
					}
				}
			});
		}, false);

		// 添加预警监控菜单项
		list_view.page.add_custom_menu_item(dropdown_menu, __('预警监控'), function() {
			console.log('[统计分析] 点击了预警监控');
			frappe.call({
				method: 'rongguan_erp.rongguan_erp.report.w70_sample_sales_analytics.alert_monitoring.get_alert_monitoring',
				args: {
					time_range: '3m'
				},
				callback: function(r) {
					if (r.message) {
						var dialog = new frappe.ui.Dialog({
							title: __('预警监控'),
							fields: [
								{
									fieldtype: 'HTML',
									options: '<div id="alert-monitoring-content"></div>'
								}
							],
							size: 'extra-large'
						});

						var content = format_alert_monitoring(r.message);
						dialog.$wrapper.find('#alert-monitoring-content').html(content);
						dialog.show();
					}
				}
			});
		}, false);

		console.log('[统计分析] 所有菜单项已添加完成');
	}
};

// 格式化客户分析数据
function format_customer_analytics(data) {
	var html = '<div class="customer-analytics">';

	// 汇总信息
	if (data.summary) {
		html += '<div class="summary-section" style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">';
		html += '<h4>' + __('汇总信息') + '</h4>';
		html += '<div class="row">';
		html += '<div class="col-md-3"><strong>' + __('总客户数') + ':</strong> ' + (data.summary.totalCustomers || 0) + '</div>';
		html += '<div class="col-md-3"><strong>' + __('高价值客户') + ':</strong> ' + (data.summary.highValueCustomers || 0) + '</div>';
		html += '<div class="col-md-3"><strong>' + __('高风险客户') + ':</strong> ' + (data.summary.highRiskCustomers || 0) + '</div>';
		html += '<div class="col-md-3"><strong>' + __('平均覆盖率') + ':</strong> ' + (data.summary.averageCoverageRate || 0) + '%</div>';
		html += '</div>';
		html += '</div>';
	}

	// 客户列表
	if (data.customers && data.customers.length > 0) {
		html += '<div class="customers-section">';
		html += '<h4>' + __('客户明细') + '</h4>';
		html += '<table class="table table-bordered table-striped">';
		html += '<thead><tr>';
		html += '<th>' + __('客户') + '</th>';
		html += '<th>' + __('业务类型') + '</th>';
		html += '<th>' + __('开发成本') + '</th>';
		html += '<th>' + __('订单利润') + '</th>';
		html += '<th>' + __('覆盖率') + '</th>';
		html += '<th>' + __('成功率') + '</th>';
		html += '<th>' + __('ROI评级') + '</th>';
		html += '</tr></thead><tbody>';

		data.customers.slice(0, 20).forEach(function(customer) {
			html += '<tr>';
			html += '<td>' + (customer.customer || '') + '</td>';
			html += '<td>' + (customer.businessType || '') + '</td>';
			html += '<td>' + format_currency(customer.totalDevelopmentCost) + '</td>';
			html += '<td>' + format_currency(customer.totalOrderProfit) + '</td>';
			html += '<td>' + (customer.coverageRate || 0) + '%</td>';
			html += '<td>' + (customer.successRate || 0) + '%</td>';
			html += '<td><span class="badge badge-' + get_rating_class(customer.roiRating) + '">' + (customer.roiRating || 'D') + '</span></td>';
			html += '</tr>';
		});

		html += '</tbody></table>';
		html += '</div>';
	}

	html += '</div>';
	return html;
}

// 格式化款式分析数据
function format_style_analytics(data) {
	var html = '<div class="style-analytics">';

	if (data.summary) {
		html += '<div class="summary-section" style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">';
		html += '<h4>' + __('汇总信息') + '</h4>';
		html += '<div class="row">';
		html += '<div class="col-md-3"><strong>' + __('总款式数') + ':</strong> ' + (data.summary.totalStyles || 0) + '</div>';
		html += '<div class="col-md-3"><strong>' + __('盈利款式') + ':</strong> ' + (data.summary.profitableStyles || 0) + '</div>';
		html += '<div class="col-md-3"><strong>' + __('亏损款式') + ':</strong> ' + (data.summary.lossStyles || 0) + '</div>';
		html += '<div class="col-md-3"><strong>' + __('平均覆盖率') + ':</strong> ' + (data.summary.averageCoverageRate || 0) + '%</div>';
		html += '</div>';
		html += '</div>';
	}

	if (data.styles && data.styles.length > 0) {
		html += '<div class="styles-section">';
		html += '<h4>' + __('款式明细') + '</h4>';
		html += '<table class="table table-bordered table-striped">';
		html += '<thead><tr>';
		html += '<th>' + __('款号') + '</th>';
		html += '<th>' + __('款式名称') + '</th>';
		html += '<th>' + __('开发成本') + '</th>';
		html += '<th>' + __('订单利润') + '</th>';
		html += '<th>' + __('覆盖率') + '</th>';
		html += '<th>' + __('盈利状态') + '</th>';
		html += '</tr></thead><tbody>';

		data.styles.slice(0, 20).forEach(function(style) {
			html += '<tr>';
			html += '<td>' + (style.styleNumber || '') + '</td>';
			html += '<td>' + (style.styleName || '') + '</td>';
			html += '<td>' + format_currency(style.developmentCost) + '</td>';
			html += '<td>' + format_currency(style.orderProfit) + '</td>';
			html += '<td>' + (style.coverageRate || 0) + '%</td>';
			html += '<td><span class="badge badge-' + get_status_class(style.profitStatus) + '">' + (style.profitStatus || '持平') + '</span></td>';
			html += '</tr>';
		});

		html += '</tbody></table>';
		html += '</div>';
	}

	html += '</div>';
	return html;
}

// 格式化业务对比数据
function format_business_comparison(data) {
	var html = '<div class="business-comparison">';

	if (data.foreignTrade && data.domesticSales) {
		html += '<div class="comparison-section">';
		html += '<h4>' + __('业务对比') + '</h4>';
		html += '<table class="table table-bordered table-striped">';
		html += '<thead><tr>';
		html += '<th>' + __('指标') + '</th>';
		html += '<th>' + __('外贸') + '</th>';
		html += '<th>' + __('内销') + '</th>';
		html += '<th>' + __('差异') + '</th>';
		html += '<th>' + __('优势方') + '</th>';
		html += '</tr></thead><tbody>';

		if (data.comparisonDetails) {
			data.comparisonDetails.forEach(function(detail) {
				html += '<tr>';
				html += '<td>' + (detail.dimension || '') + '</td>';
				html += '<td>' + format_value(detail.foreignTradeValue, detail.unit) + '</td>';
				html += '<td>' + format_value(detail.domesticSalesValue, detail.unit) + '</td>';
				html += '<td>' + format_value(detail.difference, detail.unit) + ' (' + (detail.differencePercentage || 0) + '%)</td>';
				html += '<td><span class="badge badge-info">' + (detail.advantage || '持平') + '</span></td>';
				html += '</tr>';
			});
		}

		html += '</tbody></table>';
		html += '</div>';
	}

	html += '</div>';
	return html;
}

// 格式化预警监控数据
function format_alert_monitoring(data) {
	var html = '<div class="alert-monitoring">';

	if (data.summary) {
		html += '<div class="summary-section" style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">';
		html += '<h4>' + __('预警汇总') + '</h4>';
		html += '<div class="row">';
		html += '<div class="col-md-3"><strong>' + __('高风险客户') + ':</strong> <span class="text-danger">' + (data.summary.highRiskCustomerCount || 0) + '</span></div>';
		html += '<div class="col-md-3"><strong>' + __('低利润订单') + ':</strong> <span class="text-warning">' + (data.summary.lowProfitOrderCount || 0) + '</span></div>';
		html += '<div class="col-md-3"><strong>' + __('无订单客户') + ':</strong> <span class="text-info">' + (data.summary.noOrderCustomerCount || 0) + '</span></div>';
		html += '<div class="col-md-3"><strong>' + __('异常成本') + ':</strong> <span class="text-warning">' + (data.summary.abnormalCostCount || 0) + '</span></div>';
		html += '</div>';
		html += '</div>';
	}

	// 高风险客户
	if (data.highRiskCustomers && data.highRiskCustomers.length > 0) {
		html += '<div class="high-risk-customers-section" style="margin-top: 20px;">';
		html += '<h5 class="text-danger">' + __('高风险客户') + '</h5>';
		html += '<table class="table table-bordered table-striped">';
		html += '<thead><tr>';
		html += '<th>' + __('客户') + '</th>';
		html += '<th>' + __('覆盖率') + '</th>';
		html += '<th>' + __('开发成本') + '</th>';
		html += '<th>' + __('订单利润') + '</th>';
		html += '</tr></thead><tbody>';

		data.highRiskCustomers.slice(0, 10).forEach(function(customer) {
			html += '<tr>';
			html += '<td>' + (customer.customer || '') + '</td>';
			html += '<td class="text-danger">' + (customer.coverageRate || 0) + '%</td>';
			html += '<td>' + format_currency(customer.totalDevelopmentCost) + '</td>';
			html += '<td>' + format_currency(customer.totalOrderProfit) + '</td>';
			html += '</tr>';
		});

		html += '</tbody></table>';
		html += '</div>';
	}

	html += '</div>';
	return html;
}

// 辅助函数：格式化货币
function format_currency(value) {
	if (value === null || value === undefined) return '0.00';
	return parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// 辅助函数：格式化值
function format_value(value, unit) {
	if (unit === '%') {
		return (value || 0).toFixed(1) + unit;
	} else if (unit === '元') {
		return format_currency(value);
	} else {
		return (value || 0) + (unit || '');
	}
}

// 辅助函数：获取评级样式类
function get_rating_class(rating) {
	var class_map = {
		'A': 'success',
		'B': 'info',
		'C': 'warning',
		'D': 'danger'
	};
	return class_map[rating] || 'default';
}

// 辅助函数：获取状态样式类
function get_status_class(status) {
	var class_map = {
		'盈利': 'success',
		'亏损': 'danger',
		'持平': 'warning'
	};
	return class_map[status] || 'default';
}
