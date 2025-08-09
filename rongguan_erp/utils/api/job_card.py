import frappe
import json
from frappe import _
from frappe.utils import now_datetime, flt, get_datetime


@frappe.whitelist()
def complete_job_card(**args):
    """
    通过 API 完成 Job Card
    
    参数:
    - job_card_name: Job Card 的名称 (必需)
    - completed_qty: 完成数量 (可选，默认使用 for_quantity)
    - to_time: 结束时间 (可选，默认使用当前时间)
    - employee: 员工 (可选)
    
    返回:
    - 成功信息和更新后的 Job Card 状态
    """
    try:
        # 获取参数
        job_card_name = args.get("job_card_name")
        completed_qty = args.get("completed_qty")
        to_time = args.get("to_time")
        employee = args.get("employee")
        
        # 检查必需参数
        if not job_card_name:
            return {
                "status": "error",
                "message": _("job_card_name is required"),
                "job_card": None
            }
        
        # 获取 Job Card 文档
        job_card = frappe.get_doc("Job Card", job_card_name)
        
        # 检查 Job Card 是否已经完成
        if job_card.status == "Completed":
            return {
                "status": "warning",
                "message": _("Job Card {0} is already completed").format(job_card_name),
                "job_card": job_card.name
            }
        
        # 检查 Work Order 是否关闭
        if job_card.is_work_order_closed():
            frappe.throw(_("Cannot complete Job Card since Work Order is closed"))
        
        # 设置默认值
        if not to_time:
            to_time = now_datetime()
        
        if not completed_qty:
            completed_qty = flt(job_card.for_quantity)
        
        # 准备时间日志参数
        time_log_args = frappe._dict({
            "job_card_id": job_card_name,
            "complete_time": to_time,
            "status": "Complete",
            "completed_qty": completed_qty
        })
        
        # 如果提供了员工信息
        if employee:
            time_log_args["employees"] = [{"employee": employee}]
        
        # 验证序列ID
        job_card.validate_sequence_id()
        
        # 添加时间日志
        job_card.add_time_log(time_log_args)
        
        # 如果没有时间日志，创建一个基本的时间日志
        if not job_card.time_logs:
            job_card.append("time_logs", {
                "from_time": get_datetime(to_time),
                "to_time": get_datetime(to_time),
                "completed_qty": completed_qty,
                "employee": employee
            })
            job_card.save()
        
        # 提交文档
        if job_card.docstatus == 0:
            job_card.submit()
        
        return {
            "status": "success",
            "message": _("Job Card {0} completed successfully").format(job_card_name),
            "job_card": job_card.name,
            "completed_qty": completed_qty,
            "final_status": job_card.status
        }
        
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"Error completing Job Card {args.get('job_card_name', 'Unknown')}"
        )
        return {
            "status": "error",
            "message": _("Error completing Job Card: {0}").format(str(e)),
            "job_card": args.get("job_card_name")
        }


@frappe.whitelist()
def get_job_card_status(job_card_name):
    """
    获取 Job Card 的状态信息
    
    参数:
    - job_card_name: Job Card 的名称
    
    返回:
    - Job Card 的详细状态信息
    """
    try:
        job_card = frappe.get_doc("Job Card", job_card_name)
        
        return {
            "status": "success",
            "job_card": {
                "name": job_card.name,
                "status": job_card.status,
                "work_order": job_card.work_order,
                "operation": job_card.operation,
                "for_quantity": job_card.for_quantity,
                "total_completed_qty": job_card.total_completed_qty,
                "docstatus": job_card.docstatus,
                "time_logs_count": len(job_card.time_logs) if job_card.time_logs else 0
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": _("Error getting Job Card status: {0}").format(str(e))
        }


@frappe.whitelist()
def batch_complete_job_cards(job_card_names, completed_qty=None, to_time=None, employee=None):
    """
    批量完成多个 Job Card
    
    参数:
    - job_card_names: Job Card 名称列表 (JSON 字符串或列表)
    - completed_qty: 完成数量 (可选)
    - to_time: 结束时间 (可选)
    - employee: 员工 (可选)
    
    返回:
    - 批量操作结果
    """
    if isinstance(job_card_names, str):
        job_card_names = json.loads(job_card_names)
    
    results = []
    success_count = 0
    error_count = 0
    
    for job_card_name in job_card_names:
        result = complete_job_card(
            job_card_name=job_card_name,
            completed_qty=completed_qty,
            to_time=to_time,
            employee=employee
        )
        results.append(result)
        
        if result["status"] == "success":
            success_count += 1
        else:
            error_count += 1
    
    return {
        "status": "completed",
        "message": _("Batch operation completed: {0} success, {1} errors").format(success_count, error_count),
        "results": results,
        "summary": {
            "total": len(job_card_names),
            "success": success_count,
            "errors": error_count
        }
    }

"""
API 使用示例:

1. 完成单个 Job Card:
   POST /api/method/rongguan_erp.utils.api.job_card.complete_job_card
   参数:
   {
       "job_card_name": "JOB-CARD-0001",
       "completed_qty": 10,
       "to_time": "2024-01-15 10:30:00",
       "employee": "EMP-0001"
   }

2. 获取 Job Card 状态:
   GET /api/method/rongguan_erp.utils.api.job_card.get_job_card_status?job_card_name=JOB-CARD-0001

3. 批量完成 Job Card:
   POST /api/method/rongguan_erp.utils.api.job_card.batch_complete_job_cards
   参数:
   {
       "job_card_names": ["JOB-CARD-0001", "JOB-CARD-0002"],
       "completed_qty": 10,
       "employee": "EMP-0001"
   }

使用 curl 调用示例:
curl -X POST "http://your-site/api/method/rongguan_erp.utils.api.job_card.complete_job_card" \
  -H "Content-Type: application/json" \
  -H "Authorization: token your_api_key:your_api_secret" \
  -d '{
    "job_card_name": "JOB-CARD-0001",
    "completed_qty": 10,
    "employee": "EMP-0001"
  }'

返回格式:
{
    "status": "success|error|warning",
    "message": "操作结果消息",
    "job_card": "Job Card 名称",
    "completed_qty": 完成数量,
    "final_status": "最终状态"
}

注意事项:
- job_card_name 是必需参数
- Job Card 必须处于可完成状态
- Work Order 不能是已关闭状态
- 如果不提供 completed_qty，将使用 Job Card 的 for_quantity
- 如果不提供 to_time，将使用当前时间
- API 会自动处理时间日志的创建和文档提交
- 使用 **args 格式，支持灵活的参数传递
"""
