# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, add_days


def test_qc_patrol_records_api():
	"""
	测试QC巡查记录API的bench execute方法
	使用方法: bench execute rongguan_erp.rongguan_erp.doctype.qc_patrol_record.test_qc_patrol_record.test_qc_patrol_records_api
	"""
	
	print("=" * 60)
	print("开始测试QC巡查记录API")
	print("=" * 60)
	
	# 1. 测试分页查询 - 基础查询
	print("\n1. 测试基础分页查询:")
	try:
		result = frappe.call(
			'rongguan_erp.rongguan_erp.doctype.qc_patrol_record.qc_patrol_record.get_qc_patrol_records',
			page=1,
			page_size=5
		)
		print(f"✅ 基础查询成功: {result.get('message')}")
		print(f"   总记录数: {result['data']['pagination']['total_count']}")
		print(f"   当前页记录数: {len(result['data']['records'])}")
	except Exception as e:
		print(f"❌ 基础查询失败: {str(e)}")
	
	# 2. 测试带过滤条件的查询
	print("\n2. 测试带过滤条件的查询:")
	try:
		filters = {
			"patrol_date_from": "2025-01-01",
			"patrol_date_to": "2025-12-31",
			"overall_evaluation": "合格"
		}
		result = frappe.call(
			'rongguan_erp.rongguan_erp.doctype.qc_patrol_record.qc_patrol_record.get_qc_patrol_records',
			page=1,
			page_size=10,
			filters=filters
		)
		print(f"✅ 过滤查询成功: {result.get('message')}")
		print(f"   过滤后记录数: {result['data']['pagination']['total_count']}")
	except Exception as e:
		print(f"❌ 过滤查询失败: {str(e)}")
	
	# 3. 测试搜索功能
	print("\n3. 测试搜索功能:")
	try:
		result = frappe.call(
			'rongguan_erp.rongguan_erp.doctype.qc_patrol_record.qc_patrol_record.get_qc_patrol_records',
			page=1,
			page_size=10,
			search="QC"
		)
		print(f"✅ 搜索查询成功: {result.get('message')}")
		print(f"   搜索结果数: {result['data']['pagination']['total_count']}")
	except Exception as e:
		print(f"❌ 搜索查询失败: {str(e)}")
	
	# 4. 测试排序功能
	print("\n4. 测试排序功能:")
	try:
		result = frappe.call(
			'rongguan_erp.rongguan_erp.doctype.qc_patrol_record.qc_patrol_record.get_qc_patrol_records',
			page=1,
			page_size=5,
			order_by="patrol_date desc"
		)
		print(f"✅ 排序查询成功: {result.get('message')}")
		if result['data']['records']:
			print(f"   第一条记录日期: {result['data']['records'][0].get('patrol_date')}")
	except Exception as e:
		print(f"❌ 排序查询失败: {str(e)}")
	
	# 5. 测试详情查询
	print("\n5. 测试详情查询:")
	try:
		# 先获取一条记录的名称
		list_result = frappe.call(
			'rongguan_erp.rongguan_erp.doctype.qc_patrol_record.qc_patrol_record.get_qc_patrol_records',
			page=1,
			page_size=1
		)
		
		if list_result['data']['records']:
			record_name = list_result['data']['records'][0]['name']
			detail_result = frappe.call(
				'rongguan_erp.rongguan_erp.doctype.qc_patrol_record.qc_patrol_record.get_qc_patrol_record_detail',
				record_name=record_name
			)
			print(f"✅ 详情查询成功: {detail_result.get('message')}")
			print(f"   记录名称: {record_name}")
			print(f"   检查项目数: {len(detail_result['data'].get('check_items', []))}")
			print(f"   问题记录数: {len(detail_result['data'].get('problem_records', []))}")
		else:
			print("⚠️  没有找到记录，跳过详情查询测试")
	except Exception as e:
		print(f"❌ 详情查询失败: {str(e)}")
	
	# 6. 测试错误处理
	print("\n6. 测试错误处理:")
	try:
		result = frappe.call(
			'rongguan_erp.rongguan_erp.doctype.qc_patrol_record.qc_patrol_record.get_qc_patrol_record_detail',
			record_name="不存在的记录"
		)
		if not result['success']:
			print(f"✅ 错误处理正常: {result.get('message')}")
		else:
			print("⚠️  错误处理异常: 应该返回失败但返回了成功")
	except Exception as e:
		print(f"❌ 错误处理测试失败: {str(e)}")
	
	print("\n" + "=" * 60)
	print("QC巡查记录API测试完成")
	print("=" * 60)


def create_test_data():
	"""
	创建测试数据的bench execute方法
	使用方法: bench execute rongguan_erp.rongguan_erp.doctype.qc_patrol_record.test_qc_patrol_record.create_test_data
	"""
	
	print("=" * 60)
	print("开始创建QC巡查记录测试数据")
	print("=" * 60)
	
	try:
		# 创建测试记录
		for i in range(1, 6):
			# 创建主记录
			patrol_record = frappe.get_doc({
				"doctype": "QC Patrol Record",
				"report_number": f"QC-2025-{i:03d}",
				"patrol_date": add_days(nowdate(), -i),
				"start_time": "09:00:00",
				"end_time": "11:00:00",
				"inspector": f"巡查员{i}",
				"factory": "工厂A" if i % 2 == 0 else "工厂B",
				"order_number": f"SO-2025-{i:03d}",
				"product_name": f"测试产品{i}",
				"process_stage": "生产加工",
				"sample_quantity": 50 + i * 10,
				"total_quantity": 1000 + i * 100,
				"overall_evaluation": "合格" if i % 3 == 0 else "良好",
				"recommendations": f"这是第{i}条测试记录的建议",
				"need_recheck": "否" if i % 2 == 0 else "是",
				"recheck_date": add_days(nowdate(), i) if i % 2 == 1 else None
			})
			
			# 添加检查项目
			for j in range(1, 4):
				patrol_record.append("qc_patrol_check_item", {
					"item_id": f"ITEM-{i}-{j}",
					"category": "工艺制作" if j == 1 else "尺寸规格" if j == 2 else "外观整理",
					"subcategory": f"子类别{j}",
					"standard": f"检查标准{i}-{j}",
					"result": "合格" if (i + j) % 3 == 0 else "不合格",
					"fail_count": (i + j) % 5,
					"remark": f"备注{i}-{j}"
				})
			
			# 添加问题记录
			if i % 2 == 1:  # 奇数记录添加问题
				for k in range(1, 3):
					patrol_record.append("qc_patrol_problem_record", {
						"problem_id": f"PROB-{i}-{k}",
						"description": f"问题描述{i}-{k}",
						"quantity": 5 + k,
						"severity": "中" if k == 1 else "高",
						"photo_attachments": ""
					})
			
			patrol_record.insert()
			print(f"✅ 创建测试记录 {i}: {patrol_record.name}")
		
		print(f"\n✅ 成功创建 {5} 条测试记录")
		print("=" * 60)
		
	except Exception as e:
		print(f"❌ 创建测试数据失败: {str(e)}")
		frappe.log_error(f"创建QC巡查记录测试数据失败: {str(e)}", "QC Patrol Record Test Error")


def cleanup_test_data():
	"""
	清理测试数据的bench execute方法
	使用方法: bench execute rongguan_erp.rongguan_erp.doctype.qc_patrol_record.test_qc_patrol_record.cleanup_test_data
	"""
	
	print("=" * 60)
	print("开始清理QC巡查记录测试数据")
	print("=" * 60)
	
	try:
		# 查找并删除测试记录
		test_records = frappe.get_all(
			"QC Patrol Record",
			filters={"report_number": ["like", "QC-2025-%"]},
			fields=["name"]
		)
		
		deleted_count = 0
		for record in test_records:
			frappe.delete_doc("QC Patrol Record", record.name)
			deleted_count += 1
			print(f"✅ 删除测试记录: {record.name}")
		
		print(f"\n✅ 成功删除 {deleted_count} 条测试记录")
		print("=" * 60)
		
	except Exception as e:
		print(f"❌ 清理测试数据失败: {str(e)}")
		frappe.log_error(f"清理QC巡查记录测试数据失败: {str(e)}", "QC Patrol Record Test Error")


def run_full_test():
	"""
	运行完整测试流程的bench execute方法
	使用方法: bench execute rongguan_erp.rongguan_erp.doctype.qc_patrol_record.test_qc_patrol_record.run_full_test
	"""
	
	print("=" * 80)
	print("开始运行QC巡查记录完整测试流程")
	print("=" * 80)
	
	# 1. 清理旧数据
	print("\n步骤1: 清理旧测试数据")
	cleanup_test_data()
	
	# 2. 创建测试数据
	print("\n步骤2: 创建测试数据")
	create_test_data()
	
	# 3. 运行API测试
	print("\n步骤3: 运行API测试")
	test_qc_patrol_records_api()
	
	# 4. 清理测试数据
	print("\n步骤4: 清理测试数据")
	cleanup_test_data()
	
	print("\n" + "=" * 80)
	print("QC巡查记录完整测试流程完成")
	print("=" * 80)
