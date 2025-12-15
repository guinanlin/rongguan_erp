// Copyright (c) 2025, guinan.lin@foxmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("W70 Sample Sales Base", {
	refresh(frm) {
		// 刷新时重新计算
		calculate_amount(frm);
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	
	quantity: function(frm) {
		calculate_amount(frm);
		calculate_gross_profit(frm);
	},
	
	unit_price: function(frm) {
		calculate_amount(frm);
		calculate_gross_profit(frm);
	},
	
	amount: function(frm) {
		calculate_gross_profit(frm);
	},
	
	// 所有费用字段变化时重新计算总成本和毛利
	freight_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	fabric_lining_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	accessory_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	pattern_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	special_process_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	production_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	logistics_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	management_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	other_cost: function(frm) {
		calculate_total_cost(frm);
		calculate_gross_profit(frm);
	},
	total_cost: function(frm) {
		calculate_gross_profit(frm);
	}
});

/**
 * 计算金额：数量 × 单价
 */
function calculate_amount(frm) {
	if (frm.doc.quantity && frm.doc.unit_price) {
		frm.set_value('amount', frm.doc.quantity * frm.doc.unit_price);
	}
}

/**
 * 计算总成本费用：所有费用字段的总和
 */
function calculate_total_cost(frm) {
	const cost_fields = [
		'freight_cost',          // 货代费用
		'fabric_lining_cost',    // 面里料费用
		'accessory_cost',        // 辅料费用
		'pattern_cost',          // 纸样费
		'special_process_cost',  // 特殊工艺费用
		'production_cost',       // 生产费用
		'logistics_cost',        // 物流费用
		'management_cost',       // 管理费用
		'other_cost'             // 其他费用
	];
	
	let total_costs = 0;
	cost_fields.forEach(function(field) {
		if (frm.doc[field]) {
			total_costs += parseFloat(frm.doc[field]) || 0;
		}
	});
	
	frm.set_value('total_cost', total_costs);
}

/**
 * 计算毛利：金额 - 总成本费用
 */
function calculate_gross_profit(frm) {
	if (!frm.doc.amount) {
		frm.set_value('gross_profit', 0);
		return;
	}
	
	// 使用 total_cost 计算毛利
	const total_costs = frm.doc.total_cost || 0;
	frm.set_value('gross_profit', frm.doc.amount - total_costs);
}
