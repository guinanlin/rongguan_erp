// Copyright (c) 2025, guinan.lin@foxmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('RG Production Orders', {
	refresh: function(frm) {
		console.log("Refresh function triggered"); // 添加日志
		// 清理旧的图片预览（如果存在）
		if (frm.custom_image_preview) {
			frm.custom_image_preview.remove();
			frm.custom_image_preview = null;
		}

		// 从 'kuan_shi_tu_shi' 字段获取图片 URL
		let image_url = frm.doc.kuan_shi_tu_shi;

		console.log("Image URL:", image_url); // 添加日志

		if (image_url) {
			// 获取字段的包装元素
			let field_wrapper = frm.get_field('kuan_shi_tu_shi').$wrapper;

			if (field_wrapper) {
				// 创建 <img> 元素
				let img = $('<img>')
					.attr('src', image_url)
					.css({
						'max-width': '200px',  // 根据需要调整大小
						'max-height': '200px', // 根据需要调整大小
						'margin-top': '10px',   // 添加一些间距
						'display': 'block'      // 确保图片独占一行
					});

				// 将图片附加到字段包装元素
				field_wrapper.find('.control-input-wrapper').append(img);

				// 存储图片元素的引用，以便后续清理
				frm.custom_image_preview = img;
			}
		}

		// 从销售订单导入的按钮只在新建时显示
		if(frm.doc.__islocal) {
			frm.add_custom_button(__('销售订单'), function() {
				erpnext.utils.map_current_doc({
					method: "rongguan_erp.rongguan_erp.doctype.rg_production_orders.rg_production_orders.make_from_sales_order",
					source_doctype: "Sales Order",
					target: frm,
					setters: {
						customer: frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: ["not in", ["Closed", "On Hold"]],
						per_delivered: ["<", 99.99],
						company: frm.doc.company
					}
				});
			}, __("从销售订单导入"));
		}

		// Create 下拉框在提交后显示
		if(frm.doc.docstatus === 1) {
			frm.add_custom_button(__('产品报价'), function() {
				console.log("点击了产品报价");
			}, __("创建"));
			
			// 设置 Create 按钮组为主要按钮组
			frm.page.set_inner_btn_group_as_primary(__("创建"));
		}
	},
	setup: function(frm) {
		// 添加自定义按钮
		frm.custom_make_buttons = {
			"产品报价": "产品报价"
		};

		// 绑定点击事件
		frm.add_custom_button(__('产品报价'), function() {
			console.log("点击了产品报价");
		}, __("创建"));
	},
	// rg_size: function(frm) {
	// 	console.log("rg_size changed:", frm.doc.rg_size); // Log: Check if function triggers

	// 	if (frm.doc.rg_size) {
	// 		// 清空当前的 rg_size_details 表格
	// 		frm.clear_table('rg_size_details');
	// 		console.log("rg_size_details table cleared."); // Log: Confirm table cleared

	// 		// 通过 API 获取 RG Size Type 文档及其子表数据
	// 		frappe.call({
	// 			method: 'frappe.client.get',
	// 			args: {
	// 				doctype: 'RG Size Type',
	// 				name: frm.doc.rg_size
	// 			},
	// 			callback: function(response) {
	// 				console.log("API response:", response); // Log: Inspect the full response

	// 				if (response.message) {
	// 					console.log("API response.message:", response.message); // Log: Inspect the message content

	// 					// 从 RG Size Type 文档中获取 size 子表数据 (修正字段名)
	// 					let fetched_size_details = response.message.size || [];
	// 					console.log("Fetched size details:", fetched_size_details); // Log: Check the fetched data

	// 					if (fetched_size_details.length === 0) {
	// 						console.warn("Warning: Fetched size details array ('size') is empty or not found in response.");
	// 					}
						
	// 					// 遍历获取到的尺码明细并添加到 rg_size_details 表格
	// 					fetched_size_details.forEach(detail => {
	// 						console.log("Processing detail:", detail); // Log: Check each detail item
	// 						let row = frm.add_child('rg_size_details');
	// 						// 使用正确的源字段名 '尺码' 映射到目标字段名 '尺码' (修正目标字段名)
	// 						row['尺码'] = detail['尺码']; 
	// 						// 使用正确的源字段名 '数量' 映射到目标字段名 '数量' (修正目标字段名)
	// 						row['数量'] = detail['数量'] || 0; 
	// 						console.log("Added row:", row); // Log: Check the added row
	// 					});
						
	// 					// 刷新表格以显示新添加的数据
	// 					frm.refresh_field('rg_size_details');
	// 					console.log("Refreshed rg_size_details field."); // Log: Confirm refresh called
	// 				} else {
	// 					console.error("API call successful, but response.message is empty.");
	// 				}
	// 			},
	// 			error: function(err) {
	// 				console.error("API call failed:", err); // Log: Log any API errors
	// 			}
	// 		});
	// 	} else {
    //         // 如果 rg_size 被清空，也清空尺码明细表
    //         console.log("rg_size cleared, clearing rg_size_details table."); // Log: Clearing due to empty rg_size
    //         frm.clear_table('rg_size_details');
    //         frm.refresh_field('rg_size_details');
    //     }
	// },
	// rg_size_type: function(frm) {
	// 	if (frm.doc.rg_size_type) {
	// 		frappe.call({
	// 			method: "frappe.client.get_list",
	// 			args: {
	// 				doctype: "RG Size Type Detail",
	// 				parent: "RG Size Type",
	// 				filters: {
	// 					parent: frm.doc.rg_size_type
	// 				},
	// 				fields: ["size", "size_sort_order"],
	// 				order_by: "size_sort_order asc"
	// 			},
	// 			callback: function(r) {
	// 				if (r.message) {
	// 					frm.clear_table("rg_size_details");
	// 					r.message.forEach(function(item) {
	// 						var child = frm.add_child("rg_size_details");
	// 						child.size = item.size;
	// 						child.size_sort_order = item.size_sort_order;
	// 					});
	// 					frm.refresh_field("rg_size_details");
	// 				}
	// 			}
	// 		});
	// 	} else {
	// 		frm.clear_table("rg_size_details");
	// 		frm.refresh_field("rg_size_details");
	// 	}
	// }
});
