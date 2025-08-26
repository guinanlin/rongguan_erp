# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate


class QCPatrolRecord(Document):
	pass


@frappe.whitelist()
def get_qc_patrol_records(
	page=1, 
	page_size=20, 
	filters=None, 
	search=None,
	order_by="modified desc"
):
	"""
	获取QC巡查记录的分页查询方法
	
	Args:
		page (int): 页码，从1开始
		page_size (int): 每页记录数
		filters (dict): 过滤条件
		search (str): 搜索关键词
		order_by (str): 排序方式
	
	Returns:
		dict: 包含记录列表和分页信息的字典
	"""
	try:
		# 参数验证和默认值设置
		page = int(page) if page else 1
		page_size = int(page_size) if page_size else 20
		filters = filters or {}
		
		# 构建查询条件
		conditions = []
		params = {}
		
		# 基础过滤条件
		if filters.get("patrol_date_from"):
			conditions.append("patrol_date >= %(patrol_date_from)s")
			params["patrol_date_from"] = filters.get("patrol_date_from")
		
		if filters.get("patrol_date_to"):
			conditions.append("patrol_date <= %(patrol_date_to)s")
			params["patrol_date_to"] = filters.get("patrol_date_to")
		
		if filters.get("inspector"):
			conditions.append("inspector LIKE %(inspector)s")
			params["inspector"] = f"%{filters.get('inspector')}%"
		
		if filters.get("factory"):
			conditions.append("factory = %(factory)s")
			params["factory"] = filters.get("factory")
		
		if filters.get("process_stage"):
			conditions.append("process_stage = %(process_stage)s")
			params["process_stage"] = filters.get("process_stage")
		
		if filters.get("overall_evaluation"):
			conditions.append("overall_evaluation = %(overall_evaluation)s")
			params["overall_evaluation"] = filters.get("overall_evaluation")
		
		if filters.get("need_recheck"):
			conditions.append("need_recheck = %(need_recheck)s")
			params["need_recheck"] = filters.get("need_recheck")
		
		# 搜索条件
		if search:
			search_conditions = [
				"report_number LIKE %(search)s",
				"product_name LIKE %(search)s",
				"order_number LIKE %(search)s",
				"inspector LIKE %(search)s"
			]
			conditions.append(f"({' OR '.join(search_conditions)})")
			params["search"] = f"%{search}%"
		
		# 构建WHERE子句
		where_clause = " AND ".join(conditions) if conditions else "1=1"
		
		# 计算总数
		count_sql = f"""
			SELECT COUNT(*) as total
			FROM `tabQC Patrol Record`
			WHERE {where_clause}
		"""
		total_count = frappe.db.sql(count_sql, params, as_dict=True)[0].total
		
		# 计算分页
		offset = (page - 1) * page_size
		total_pages = (total_count + page_size - 1) // page_size
		
		# 查询主表数据
		main_sql = f"""
			SELECT 
				name,
				report_number,
				patrol_date,
				start_time,
				end_time,
				inspector,
				factory,
				order_number,
				product_name,
				process_stage,
				sample_quantity,
				total_quantity,
				overall_evaluation,
				recommendations,
				need_recheck,
				recheck_date,
				creation,
				modified,
				modified_by
			FROM `tabQC Patrol Record`
			WHERE {where_clause}
			ORDER BY {order_by}
			LIMIT %(page_size)s OFFSET %(offset)s
		"""
		params.update({
			"page_size": page_size,
			"offset": offset
		})
		
		main_records = frappe.db.sql(main_sql, params, as_dict=True)
		
		# 获取子表数据
		for record in main_records:
			# 获取检查项目子表数据
			check_items = frappe.get_all(
				"QC Patrol Check Item",
				filters={"parent": record.name},
				fields=["*"],
				order_by="idx"
			)
			record["check_items"] = check_items
			
			# 获取问题记录子表数据
			problem_records = frappe.get_all(
				"QC Patrol Problem Record",
				filters={"parent": record.name},
				fields=["*"],
				order_by="idx"
			)
			record["problem_records"] = problem_records
		
		# 返回结果
		return {
			"success": True,
			"data": {
				"records": main_records,
				"pagination": {
					"current_page": page,
					"page_size": page_size,
					"total_count": total_count,
					"total_pages": total_pages,
					"has_next": page < total_pages,
					"has_prev": page > 1
				}
			},
			"message": f"成功获取 {len(main_records)} 条记录"
		}
		
	except Exception as e:
		frappe.log_error(f"获取QC巡查记录失败: {str(e)}", "QC Patrol Record API Error")
		return {
			"success": False,
			"message": f"获取QC巡查记录失败: {str(e)}",
			"data": None
		}


@frappe.whitelist()
def get_qc_patrol_record_detail(record_name):
	"""
	获取单个QC巡查记录的详细信息
	
	Args:
		record_name (str): 记录名称
	
	Returns:
		dict: 包含主表和子表完整信息的字典
	"""
	try:
		if not record_name:
			return {
				"success": False,
				"message": "记录名称不能为空",
				"data": None
			}
		
		# 获取主表信息
		main_record = frappe.get_doc("QC Patrol Record", record_name)
		if not main_record:
			return {
				"success": False,
				"message": "记录不存在",
				"data": None
			}
		
		# 转换为字典
		record_dict = main_record.as_dict()
		
		# 获取子表数据
		record_dict["check_items"] = []
		record_dict["problem_records"] = []
		
		for check_item in main_record.qc_patrol_check_item:
			record_dict["check_items"].append(check_item.as_dict())
		
		for problem_record in main_record.qc_patrol_problem_record:
			record_dict["problem_records"].append(problem_record.as_dict())
		
		return {
			"success": True,
			"data": record_dict,
			"message": "成功获取记录详情"
		}
		
	except Exception as e:
		frappe.log_error(f"获取QC巡查记录详情失败: {str(e)}", "QC Patrol Record API Error")
		return {
			"success": False,
			"message": f"获取QC巡查记录详情失败: {str(e)}",
			"data": None
		}
