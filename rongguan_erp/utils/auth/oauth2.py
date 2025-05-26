import json
from urllib.parse import parse_qs, quote, urlencode, urlparse
from http import cookies

from oauthlib.oauth2 import FatalClientError, OAuth2Error
from oauthlib.openid.connect.core.endpoints.pre_configured import Server as WebApplicationServer

import frappe
from frappe.integrations.doctype.oauth_provider_settings.oauth_provider_settings import (
	get_oauth_settings,
)
from frappe.oauth import (
	OAuthWebRequestValidator,
	generate_json_error_response,
	get_server_url,
	get_userinfo,
)


def get_oauth_server():
	if not getattr(frappe.local, "oauth_server", None):
		oauth_validator = OAuthWebRequestValidator()
		frappe.local.oauth_server = WebApplicationServer(oauth_validator)

	return frappe.local.oauth_server


def sanitize_kwargs(param_kwargs):
	"""Remove 'data' and 'cmd' keys, if present."""
	arguments = param_kwargs
	arguments.pop("data", None)
	arguments.pop("cmd", None)

	return arguments


def encode_params(params):
	"""
	Encode a dict of params into a query string.

	Use `quote_via=urllib.parse.quote` so that whitespaces will be encoded as
	`%20` instead of as `+`. This is needed because oauthlib cannot handle `+`
	as a whitespace.
	"""
	return urlencode(params, quote_via=quote)


@frappe.whitelist()
def approve(*args, **kwargs):
	r = frappe.request

	try:
		(
			scopes,
			frappe.flags.oauth_credentials,
		) = get_oauth_server().validate_authorization_request(r.url, r.method, r.get_data(), r.headers)

		headers, body, status = get_oauth_server().create_authorization_response(
			uri=frappe.flags.oauth_credentials["redirect_uri"],
			body=r.get_data(),
			headers=r.headers,
			scopes=scopes,
			credentials=frappe.flags.oauth_credentials,
		)
		uri = headers.get("Location", None)
		print(f"uri===========================: {uri}")
		# 提取code和state
		code = parse_qs(urlparse(uri).query).get('code', [None])[0]
		state = parse_qs(urlparse(uri).query).get('state', [None])[0]
		print(f"code===========================: {code}")
		print(f"state===========================: {state}")
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = uri
		return

	except (FatalClientError, OAuth2Error) as e:
		# 添加错误日志
		frappe.log_error(title="OAuth Approval Error", message=str(e))
		return generate_json_error_response(e)


@frappe.whitelist(allow_guest=True)
def authorize(**kwargs):
	success_url = "/api/method/rongguan_erp.utils.auth.oauth2.approve?" + encode_params(sanitize_kwargs(kwargs))
	failure_url = frappe.form_dict["redirect_uri"] + "?error=access_denied"

	print(f"frappe.session.user===========================: {frappe.session.user}")
	if frappe.session.user == "Guest":
		# Force login, redirect to preauth again.
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/login?" + encode_params({"redirect-to": frappe.request.url})
	else:
		try:
			# 修改请求的 cookie
			# frappe.local.cookie_manager.set_cookie("user_id", "dty@datangyuan.cn")
			# frappe.local.cookie_manager.set_cookie("full_name", "dty")
			# frappe.local.cookie_manager.set_cookie("system_user", "yes")
			# frappe.local.cookie_manager.set_cookie("sid", "11483c983ede148379f8d0a2d2de670102fdfa95ff6c240ef4ec5660")
			# frappe.local.cookie_manager.set_cookie("user_image", "")

			r = frappe.request
			# print(f"修改后的 Cookie: {frappe.local.cookie_manager.cookies}")
			print(f"frappe.session.user===========================: {frappe.session.user}")
			print(f"frappe.flags.oauth_credentials===========================: {frappe.flags.oauth_credentials}")
			(
				scopes,
				frappe.flags.oauth_credentials,
			) = get_oauth_server().validate_authorization_request(r.url, r.method, r.get_data(), r.headers)
			print(f"scopes===========================: {scopes}")
			print(f"frappe.flags.oauth_credentials===========================: {frappe.flags.oauth_credentials}")
			skip_auth = frappe.db.get_value(
				"OAuth Client",
				frappe.flags.oauth_credentials["client_id"],
				"skip_authorization",
			)
			unrevoked_tokens = frappe.get_all("OAuth Bearer Token", filters={"status": "Active"})
			print(f"skip_auth===========================: {skip_auth}")
			print(f"unrevoked_tokens===========================: {unrevoked_tokens}")

			if skip_auth or (get_oauth_settings().skip_authorization == "Auto" and unrevoked_tokens):
				# 直接在authorize方法中生成code和state
				headers, body, status = get_oauth_server().create_authorization_response(
					uri=frappe.flags.oauth_credentials["redirect_uri"],
					body=r.get_data(),
					headers=r.headers,
					scopes=scopes,
					credentials=frappe.flags.oauth_credentials,
				)
				uri = headers.get("Location", None)
				
				# 提取code和state
				code = parse_qs(urlparse(uri).query).get('code', [None])[0]
				state = parse_qs(urlparse(uri).query).get('state', [None])[0]
				
				# 使用Frappe框架标准方式返回JSON响应
				frappe.response["type"] = "json"
				frappe.response["data"] = {
					"code": code,
					"state": state
				}
				return
			else:
				# 处理用户确认
				if "openid" in scopes:
					scopes.remove("openid")
					scopes.extend(["Full Name", "Email", "User Image", "Roles"])

				response_html_params = frappe._dict(
					{
						"client_id": frappe.db.get_value("OAuth Client", kwargs["client_id"], "app_name"),
						"success_url": success_url,
						"failure_url": failure_url,
						"details": scopes,
					}
				)
				resp_html = frappe.render_template(
					"templates/includes/oauth_confirmation.html", response_html_params
				)
				frappe.respond_as_web_page(frappe._("Confirm Access"), resp_html, primary_action=None)
		except (FatalClientError, OAuth2Error) as e:
			return generate_json_error_response(e)


@frappe.whitelist(allow_guest=True)
def get_token(*args, **kwargs):
	"""
	处理 OAuth2 令牌请求。

	该方法根据 OAuth2 规范生成访问令牌。它接受来自客户端的请求，并根据请求的参数生成相应的令牌响应。

	输入数据格式（表单数据）：
	- grant_type: 授权类型（必需）
	- client_id: 客户端唯一标识符（必需）
	- client_secret: 客户端密钥（可选）
	- redirect_uri: 授权成功后重定向的 URI（可选）
	- code: 授权码（必需，仅在 grant_type 为 authorization_code 时使用）
	- refresh_token: 刷新令牌（必需，仅在 grant_type 为 refresh_token 时使用）
	- scope: 请求的权限范围（可选）

	返回：
	- 成功时返回访问令牌及相关信息。
	- 失败时返回错误信息及 HTTP 状态码 400。
	"""
	try:
		r = frappe.request
		# 调试输出请求的原始数据
		print("Received request data:", r.form)
		print("oauth_credentials===========================:", frappe.flags.oauth_credentials)
		
		# 从授权码获取用户信息
		auth_code = r.form.get("code")
		auth_code_doc = frappe.get_doc("OAuth Authorization Code", {"authorization_code": auth_code})
		
		# 设置oauth_credentials
		if not frappe.flags.oauth_credentials:
			frappe.flags.oauth_credentials = {
				"user": auth_code_doc.user,
				"client": r.form.get("client_id")
			}

		print("oauth_credentials===========================:", frappe.flags.oauth_credentials)
		# 然后再调用create_token_response
		headers, body, status = get_oauth_server().create_token_response(
			r.url, r.method, r.form, r.headers, frappe.flags.oauth_credentials
		)
		
		# 调试输出生成的响应头和状态
		print("Response headers:", headers)
		print("Response status:", status)

		body = frappe._dict(json.loads(body))

		# 调试输出解析后的响应体
		print("Parsed response body:", body)

		if body.error:
			frappe.local.response = body
			frappe.local.response["http_status_code"] = 400
			print("Error in response:", body.error)
			return

		# 直接返回解析后的响应体为 JSON 格式
		frappe.response["type"] = "json"
		frappe.response["data"] = {
			"access_token": body.access_token,
			"expires_in": body.expires_in,
			"token_type": body.token_type,
			"scope": body.scope,
			"refresh_token": body.refresh_token
		}
		return

	except (FatalClientError, OAuth2Error) as e:
		print("Exception occurred:", str(e))
		return generate_json_error_response(e)


@frappe.whitelist(allow_guest=True)
def revoke_token(*args, **kwargs):
	try:
		r = frappe.request
		headers, body, status = get_oauth_server().create_revocation_response(
			r.url,
			headers=r.headers,
			body=r.form,
			http_method=r.method,
		)
	except (FatalClientError, OAuth2Error):
		pass

	# status_code must be 200
	frappe.local.response = frappe._dict({})
	frappe.local.response["http_status_code"] = status or 200
	return


@frappe.whitelist(allow_guest=True)
def openid_profile(*args, **kwargs):
	print("openid_profile===========================:")
	
	# return {"code": "123456"}
	try:
		r = frappe.request
		# 调试输出请求的原始数据
		print(f"r data===========================: {r}")
		print(f"r headers===========================: {r.headers}")         
		print(f"r form===========================: {r.form}")
		print(f"r url===========================: {r.url}")
		print("Received request data for openid_profile:", r.form)
		print(f" frappe.session.user===========================: {frappe.session.user}")

		headers, body, status = get_oauth_server().create_userinfo_response(
			r.url,
			headers=r.headers,
			body=r.form,
		)
		
		# 调试输出生成的响应头和状态
		print("Response headers from userinfo response:", headers)
		print("Response status from userinfo response:", status)

		body = frappe._dict(json.loads(body))
		
		# 调试输出解析后的响应体
		print("Parsed response body from userinfo response:", body)

		frappe.local.response = body
		return

	except (FatalClientError, OAuth2Error) as e:
		print("Exception occurred in openid_profile:", str(e))
		return generate_json_error_response(e)


@frappe.whitelist(allow_guest=True)
def openid_configuration():
	frappe_server_url = get_server_url()
	frappe.local.response = frappe._dict(
		{
			"issuer": frappe_server_url,
			"authorization_endpoint": f"{frappe_server_url}/api/method/frappe.integrations.oauth2.authorize",
			"token_endpoint": f"{frappe_server_url}/api/method/frappe.integrations.oauth2.get_token",
			"userinfo_endpoint": f"{frappe_server_url}/api/method/frappe.integrations.oauth2.openid_profile",
			"revocation_endpoint": f"{frappe_server_url}/api/method/frappe.integrations.oauth2.revoke_token",
			"introspection_endpoint": f"{frappe_server_url}/api/method/frappe.integrations.oauth2.introspect_token",
			"response_types_supported": [
				"code",
				"token",
				"code id_token",
				"code token id_token",
				"id_token",
				"id_token token",
			],
			"subject_types_supported": ["public"],
			"id_token_signing_alg_values_supported": ["HS256"],
		}
	)


@frappe.whitelist(allow_guest=True)
def introspect_token(token=None, token_type_hint=None):
	if token_type_hint not in ["access_token", "refresh_token"]:
		token_type_hint = "access_token"
	try:
		bearer_token = None
		if token_type_hint == "access_token":
			bearer_token = frappe.get_doc("OAuth Bearer Token", {"access_token": token})
		elif token_type_hint == "refresh_token":
			bearer_token = frappe.get_doc("OAuth Bearer Token", {"refresh_token": token})

		client = frappe.get_doc("OAuth Client", bearer_token.client)

		token_response = frappe._dict(
			{
				"client_id": client.client_id,
				"trusted_client": client.skip_authorization,
				"active": bearer_token.status == "Active",
				"exp": round(bearer_token.expiration_time.timestamp()),
				"scope": bearer_token.scopes,
			}
		)

		if "openid" in bearer_token.scopes:
			sub = frappe.get_value(
				"User Social Login",
				{"provider": "frappe", "parent": bearer_token.user},
				"userid",
			)

			if sub:
				token_response.update({"sub": sub})
				user = frappe.get_doc("User", bearer_token.user)
				userinfo = get_userinfo(user)
				token_response.update(userinfo)

		frappe.local.response = token_response

	except Exception:
		frappe.local.response = frappe._dict({"active": False})
