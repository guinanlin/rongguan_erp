# Copyright (c) 2025, guinan.lin@foxmail.com and contributors
# For license information, please see license.txt
"""
RG Production Progress 列表：客户中文名模糊 + 款式/款号 AND 组合（与 frappe.client.get_list 单一 or_filters 不兼容时的后端实现）。

Frappe API:
- POST /api/method/rongguan_erp.utils.api.production_progress_list.get_production_progress_list
- POST /api/method/rongguan_erp.utils.api.production_progress_list.get_production_progress_count

语义（均为子串模糊，同一关键词在 customer / customer_name_display 上 OR；款式为 product_name OR style_code；与款号 AND）：
- customer_eq: customer 精确匹配（与建议选中一致）
- customer_text: 手输模糊 → (customer LIKE OR customer_name_display LIKE)
- product_text: 款式 → (product_name LIKE OR style_code LIKE)
- style_text: 款号 → style_code LIKE

权限：复用 reportview.get_match_cond，与列表/总数 SQL 一致。
"""

from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe.desk.reportview import get_match_cond


DOCTYPE = "RG Production Progress"
TABLE = "`tabRG Production Progress`"


def normalize_search_keyword(keyword: str | None) -> str:
	"""去首尾空白；全角 ASCII（FF01–FF5E）转为半角，便于与 ERP 中半角编码对齐。"""
	if keyword is None:
		return ""
	s = keyword.strip()
	if not s:
		return ""
	out: list[str] = []
	for ch in s:
		code = ord(ch)
		if 0xFF01 <= code <= 0xFF5E:
			out.append(chr(code - 0xFEE0))
		else:
			out.append(ch)
	return "".join(out)


def escape_like_pattern(user_fragment: str) -> str:
	"""LIKE 通配符转义（保留用户输入的 % _ 字面含义需转义）。"""
	if not user_fragment:
		return ""
	return user_fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_arg(value: Any, default: Any = None):
	if value is None or value == "":
		return default
	if isinstance(value, str):
		v = value.strip()
		if v.startswith(("{", "[")):
			try:
				return json.loads(v)
			except json.JSONDecodeError:
				return value
		return value
	return value


def _parse_fields(fields) -> list | None:
	fields = _parse_arg(fields)
	if fields is None:
		return None
	if isinstance(fields, str):
		try:
			fields = json.loads(fields)
		except json.JSONDecodeError:
			fields = [f.strip() for f in fields.split(",")]
	if isinstance(fields, list):
		return fields
	return None


_ORDER_BY_PATTERN = re.compile(r"^[a-zA-Z0-9_`,.\s\-]+$")


def _sanitize_order_by(order_by: str | None) -> str:
	if not order_by or not isinstance(order_by, str):
		return "`tabRG Production Progress`.`modified` desc"
	ob = order_by.strip()
	if not _ORDER_BY_PATTERN.match(ob):
		return "`tabRG Production Progress`.`modified` desc"
	if "`" not in ob and "tabRG Production Progress" not in ob:
		parts = ob.split()
		if len(parts) >= 2:
			field, direction = parts[0], parts[-1].lower()
			if field.replace("_", "").isalnum() and direction in ("asc", "desc"):
				return f"`tabRG Production Progress`.`{field}` {direction}"
	return "`tabRG Production Progress`.`modified` desc"


def _build_search_where(params: dict) -> tuple[str, list]:
	"""返回 SQL 片段（不含 WHERE 关键字）与参数列表。"""
	t = TABLE
	clauses: list[str] = []
	bind: list = []

	if params.get("customer_eq"):
		clauses.append(f"{t}.`customer` = %s")
		bind.append(params["customer_eq"])

	if params.get("customer_text"):
		kw = normalize_search_keyword(params["customer_text"])
		if kw:
			like = "%" + escape_like_pattern(kw) + "%"
			clauses.append(
				f"(LOWER({t}.`customer`) LIKE LOWER(%s) ESCAPE '\\\\' OR "
				f"LOWER(IFNULL({t}.`customer_name_display`,'')) LIKE LOWER(%s) ESCAPE '\\\\')"
			)
			bind.extend([like, like])

	if params.get("product_text"):
		kw = normalize_search_keyword(params["product_text"])
		if kw:
			like = "%" + escape_like_pattern(kw) + "%"
			clauses.append(
				f"(LOWER({t}.`product_name`) LIKE LOWER(%s) ESCAPE '\\\\' OR "
				f"LOWER({t}.`style_code`) LIKE LOWER(%s) ESCAPE '\\\\')"
			)
			bind.extend([like, like])

	if params.get("style_text"):
		kw = normalize_search_keyword(params["style_text"])
		if kw:
			like = "%" + escape_like_pattern(kw) + "%"
			clauses.append(f"LOWER({t}.`style_code`) LIKE LOWER(%s) ESCAPE '\\\\'")
			bind.append(like)

	if not clauses:
		return "1=1", []
	return "(" + " AND ".join(clauses) + ")", bind


def _collect_params(
	customer_eq=None,
	customer_text=None,
	product_text=None,
	style_text=None,
) -> dict:
	return {
		"customer_eq": _parse_arg(customer_eq),
		"customer_text": _parse_arg(customer_text),
		"product_text": _parse_arg(product_text),
		"style_text": _parse_arg(style_text),
	}


@frappe.whitelist()
def get_production_progress_count(
	customer_eq=None,
	customer_text=None,
	product_text=None,
	style_text=None,
):
	"""与列表接口相同的筛选语义下的总数（用于分页 total）。"""
	params = _collect_params(
		customer_eq=customer_eq,
		customer_text=customer_text,
		product_text=product_text,
		style_text=style_text,
	)
	where_sql, bind = _build_search_where(params)
	match_cond = get_match_cond(DOCTYPE)
	sql = (
		f"SELECT COUNT(*) AS cnt FROM {TABLE} WHERE {where_sql} {match_cond}"
	)
	row = frappe.db.sql(sql, tuple(bind), as_dict=True)
	return int(row[0]["cnt"]) if row else 0


@frappe.whitelist()
def get_production_progress_list(
	fields=None,
	limit_start=None,
	limit_page_length=20,
	order_by=None,
	customer_eq=None,
	customer_text=None,
	product_text=None,
	style_text=None,
):
	"""
	返回 { data: [...], total: N }。data 中记录顺序与权限、排序一致。
	"""
	limit_start = int(_parse_arg(limit_start) or 0)
	limit_page_length = int(_parse_arg(limit_page_length) or 20)
	if limit_page_length < 1:
		limit_page_length = 20
	if limit_start < 0:
		limit_start = 0

	params = _collect_params(
		customer_eq=customer_eq,
		customer_text=customer_text,
		product_text=product_text,
		style_text=style_text,
	)
	where_sql, bind = _build_search_where(params)
	match_cond = get_match_cond(DOCTYPE)
	order_sql = _sanitize_order_by(_parse_arg(order_by))

	sql_names = (
		f"SELECT {TABLE}.`name` FROM {TABLE} WHERE {where_sql} {match_cond} "
		f"ORDER BY {order_sql} LIMIT %s OFFSET %s"
	)
	bind_names = list(bind) + [limit_page_length, limit_start]
	names_rows = frappe.db.sql(sql_names, tuple(bind_names), as_dict=True)
	names = [r["name"] for r in names_rows]

	field_list = _parse_fields(fields)
	if not names:
		return {
			"data": [],
			"total": get_production_progress_count(
				customer_eq=params["customer_eq"],
				customer_text=params["customer_text"],
				product_text=params["product_text"],
				style_text=params["style_text"],
			),
		}

	if not field_list:
		field_list = ["name"]

	# 二次拉取字段并保留读权限过滤（与 get_list 一致）
	rows = frappe.get_list(
		DOCTYPE,
		filters=[["name", "in", names]],
		fields=field_list,
		limit_page_length=len(names),
		order_by=None,
	)
	by_name = {r["name"]: r for r in rows}
	ordered = [by_name[n] for n in names if n in by_name]
	total = get_production_progress_count(
		customer_eq=params["customer_eq"],
		customer_text=params["customer_text"],
		product_text=params["product_text"],
		style_text=params["style_text"],
	)
	return {"data": ordered, "total": total}
