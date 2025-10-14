// Copyright (c) 2025, guinan.lin@foxmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Rg Cost Calculations', {
	refresh: function(frm) {
		// 添加自定义按钮
		if (frm.doc.docstatus === 0) {
			// 草稿状态显示提交审核按钮
			if (frm.doc.status === 'draft') {
				frm.add_custom_button(__('提交审核'), function() {
					frm.call('submit_for_approval').then(() => {
						frm.reload_doc();
					});
				});
			}
			
			// 待审核状态显示批准和拒绝按钮
			if (frm.doc.status === 'pending') {
				frm.add_custom_button(__('批准'), function() {
					frm.call('approve').then(() => {
						frm.reload_doc();
					});
				}, __('审批'));
				
				frm.add_custom_button(__('拒绝'), function() {
					frappe.prompt({
						label: __('拒绝原因'),
						fieldname: 'reason',
						fieldtype: 'Small Text'
					}, (values) => {
						frm.call('reject', { reason: values.reason }).then(() => {
							frm.reload_doc();
						});
					}, __('请输入拒绝原因'));
				}, __('审批'));
			}
			
			// 已批准状态显示创建新版本按钮
			if (frm.doc.status === 'approved') {
				frm.add_custom_button(__('创建新版本'), function() {
					frappe.prompt({
						label: __('版本说明'),
						fieldname: 'version_remark',
						fieldtype: 'Small Text'
					}, (values) => {
						frm.call('create_new_version', {
							version_remark: values.version_remark
						}).then((r) => {
							if (r.message) {
								frappe.set_route('Form', 'Rg Cost Calculations', r.message);
							}
						});
					}, __('请输入版本说明'));
				});
			}
		}
		
		// 根据状态设置只读
		if (frm.doc.status === 'approved') {
			frm.set_df_property('fabric_items', 'read_only', 1);
			frm.set_df_property('accessory_items', 'read_only', 1);
			frm.set_df_property('process_items', 'read_only', 1);
			frm.set_df_property('production_items', 'read_only', 1);
		}
	},
	
	customer: function(frm) {
		// 客户变化时重新生成业务主键
		if (frm.doc.customer && frm.doc.style_number) {
			frm.set_value('business_key', `${frm.doc.customer}-${frm.doc.style_number}`);
		}
	},
	
	style_number: function(frm) {
		// 款号变化时重新生成业务主键
		if (frm.doc.customer && frm.doc.style_number) {
			frm.set_value('business_key', `${frm.doc.customer}-${frm.doc.style_number}`);
		} else if (frm.doc.style_number) {
			frm.set_value('business_key', frm.doc.style_number);
		}
	},
	
	profit_percentage: function(frm) {
		// 利润百分比变化时重新计算
		calculate_totals(frm);
	},
	
	fabric_items_on_form_rendered: function(frm) {
		calculate_totals(frm);
	},
	
	accessory_items_on_form_rendered: function(frm) {
		calculate_totals(frm);
	},
	
	process_items_on_form_rendered: function(frm) {
		calculate_totals(frm);
	},
	
	production_items_on_form_rendered: function(frm) {
		calculate_totals(frm);
	}
});

// 明细表事件
frappe.ui.form.on('Rg Cost Calculation Items', {
	unit_price: function(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},
	
	net_consumption: function(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},
	
	loss_rate: function(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},
	
	quantity: function(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},
	
	fabric_items_add: function(frm, cdt, cdn) {
		set_item_type(frm, cdt, cdn, 'fabric');
	},
	
	accessory_items_add: function(frm, cdt, cdn) {
		set_item_type(frm, cdt, cdn, 'accessory');
	},
	
	process_items_add: function(frm, cdt, cdn) {
		set_item_type(frm, cdt, cdn, 'process');
	},
	
	production_items_add: function(frm, cdt, cdn) {
		set_item_type(frm, cdt, cdn, 'production');
	},
	
	fabric_items_remove: function(frm) {
		calculate_totals(frm);
	},
	
	accessory_items_remove: function(frm) {
		calculate_totals(frm);
	},
	
	process_items_remove: function(frm) {
		calculate_totals(frm);
	},
	
	production_items_remove: function(frm) {
		calculate_totals(frm);
	}
});

// 辅助函数：设置明细类型
function set_item_type(frm, cdt, cdn, item_type) {
	let item = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, 'item_type', item_type);
	
	// 自动设置序号
	let table_field = item_type + '_items';
	let items = frm.doc[table_field] || [];
	frappe.model.set_value(cdt, cdn, 'sequence', items.length);
}

// 辅助函数：计算单个明细项的金额
function calculate_item_amount(frm, cdt, cdn) {
	let item = locals[cdt][cdn];
	
	if (item.item_type === 'production') {
		// 生产成本：金额 = 单价 × 数量
		if (item.unit_price && item.quantity) {
			let amount = item.unit_price * item.quantity;
			frappe.model.set_value(cdt, cdn, 'amount', amount);
		}
	} else {
		// 面料、辅料、工艺：先计算总耗，再计算金额
		if (item.net_consumption) {
			let loss_rate = item.loss_rate || 0;
			let total_consumption = item.net_consumption * (1 + loss_rate / 100);
			frappe.model.set_value(cdt, cdn, 'total_consumption', total_consumption);
			
			if (item.unit_price) {
				let amount = item.unit_price * total_consumption;
				frappe.model.set_value(cdt, cdn, 'amount', amount);
			}
		}
	}
	
	// 延迟计算汇总，避免重复计算
	setTimeout(() => {
		calculate_totals(frm);
	}, 100);
}

// 辅助函数：计算汇总成本
function calculate_totals(frm) {
	if (!frm.doc) return;
	
	// 计算面料成本
	let fabric_cost = 0;
	(frm.doc.fabric_items || []).forEach(item => {
		fabric_cost += (item.amount || 0);
	});
	frm.set_value('fabric_cost', fabric_cost);
	
	// 计算辅料成本
	let accessory_cost = 0;
	(frm.doc.accessory_items || []).forEach(item => {
		accessory_cost += (item.amount || 0);
	});
	frm.set_value('accessory_cost', accessory_cost);
	
	// 计算工艺成本
	let process_cost = 0;
	(frm.doc.process_items || []).forEach(item => {
		process_cost += (item.amount || 0);
	});
	frm.set_value('process_cost', process_cost);
	
	// 计算生产成本
	let production_cost = 0;
	(frm.doc.production_items || []).forEach(item => {
		production_cost += (item.amount || 0);
	});
	frm.set_value('production_cost', production_cost);
	
	// 计算总成本
	let total_production_cost = fabric_cost + accessory_cost + process_cost + production_cost;
	frm.set_value('total_production_cost', total_production_cost);
	
	// 计算利润
	let profit_percentage = frm.doc.profit_percentage || 15;
	let profit_amount = total_production_cost * profit_percentage / 100;
	frm.set_value('profit_amount', profit_amount);
	
	// 计算FOB价格
	let fob_price = total_production_cost + profit_amount;
	frm.set_value('fob_price', fob_price);
}
