import frappe
from frappe import _
from frappe.utils import cint
import json

def get_context(context):
    # 检查用户是否登录
    if frappe.session.user == 'Guest':
        frappe.throw(_("必须登录才能访问此页面"))
    
    # 检查用户是否有管理员权限
    if not frappe.has_permission("OAuth Client", "read"):
        frappe.throw(_("您没有足够的权限访问此页面"))
    
    # 获取可用的OAuth客户端列表供下拉选择
    context.oauth_clients = frappe.get_all("OAuth Client", 
        fields=["name", "app_name", "client_id"],
        filters={"client_type": "Public"})
    
    context.title = _("手动生成OAuth令牌")
    
    return context 