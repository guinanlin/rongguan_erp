import jwt
import frappe
from frappe.utils.password import get_decrypted_password
from frappe.utils.oauth import login_oauth_user
from frappe.integrations.oauth2 import get_token
from urllib.parse import parse_qs
from frappe.integrations.oauth2 import encode_params
from frappe.tests.test_api import get_test_client, make_request, suppress_stdout
from frappe.auth import LoginManager

@frappe.whitelist(allow_guest=True)
def hello():
    return "hello from server"
    # return "hello"

@frappe.whitelist(allow_guest=True)
def decode_jwt_token_test(token, secret_key):
    """
    解密 JWT token 并返回解密后的信息

    :param token: JWT token
    :param secret_key: 用于解密的密钥
    :return: 解密后的信息
    """
    info = {}

    try:
        decoded = jwt.decode(token, secret_key, audience=["fastapi-users:auth"],algorithms=["HS256"])
        info.update({'custom_field': decoded['custom_field']})
        info.update({'sub': decoded['sub']})

        token = get_token(token, as_dict=True)
        info.update({'access_token': token})
        # user = frappe.get_all("User", filters={"username": decoded['username']}, fields=["email"])
        # if user:
        #     info.update({'email': user[0].get("email")})
        # else:
        #     info.update({'email': None})

        return info
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None

def decode_jwt_token(token, secret_key):
    """
    解密 JWT token 并返回解密后的信息

    :param token: JWT token
    :param secret_key: 用于解密的密钥
    :return: 解密后的信息
    """
    info = {}

    try:
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        info.update({'name': decoded['username']})
        info.update({'sub': decoded['username']})
        user = frappe.get_all("User", filters={"username": decoded['username']}, fields=["email"])
        if user:
            info.update({'email': user[0].get("email")})
        else:
            info.update({'email': None})

        return info
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None

@frappe.whitelist(allow_guest=True)
def login_via_erpnextcn(code: str, state: str):
    # 打印请求头信息
    request_headers = frappe.local.request.headers
    print("Request Headers:", request_headers)

    providers = frappe.get_all("Social Login Key", fields=["*"], filters={"social_login_provider": "ERPNextCN"})
    out = {}
    for provider in providers:
        out[provider.name] = {
            "client_id": provider.client_id,
            "redirect_to": provider.custom_sucess_redirect_url,
            "client_secret": get_decrypted_password("Social Login Key", provider.name, "client_secret")
        }
    
    info = decode_jwt_token(code, out['erpnextcn']['client_secret'])

    login_oauth_user(info, provider='erpnextcn', state={
        'token': state,
        'redirect_to': out['erpnextcn']['redirect_to']
    })

def generate_access_token_for_user(username, client_id):
    # 模拟用户会话
    frappe.set_user("Administrator")  # 需要管理员权限
    user = frappe.get_doc("User", username)
    
    # 生成 OAuth Token
    token_data = {
        "grant_type": "client_credentials",  # 或其他支持的类型
        "client_id": client_id,
        "client_secret": frappe.db.get_value("OAuth Client", client_id, "client_secret"),
        "user": user.name
    }
    # token = get_token(token_data, as_dict=True)
    token = None
    return token

@frappe.whitelist(allow_guest=True)
def generate_openid_code_id_token():
    """
    生成 OpenID Connect 代码和 ID 令牌。

    :return: 包含访问令牌和 ID 令牌的字典
    """
    form_header = {"content-type": "application/x-www-form-urlencoded"}
    client_id = "0quf58qqgb"
    scope = "all openid"
    response_type = "code"
    redirect_uri = "http://192.168.32.20"
    nonce = "1234567890"

    # 模拟用户已登录
    user = 'guinan.lin@foxmail.com'
    frappe.set_user(user)
    frappe.local.session.user = user
    frappe.local.session.data.user = user
    frappe.local.session.data.sid = frappe.session.sid
    
    # 获取当前会话的 sid
    sid = frappe.session.sid
    print("Current session sid:", sid)
    print("Current user:", frappe.session.user)

    # 创建测试客户端并设置 cookie
    TEST_CLIENT = get_test_client()
    TEST_CLIENT.set_cookie(key="sid", value=sid)
    TEST_CLIENT.set_cookie(key="user_id", value=user)
    TEST_CLIENT.set_cookie(key="system_user", value="yes")
    TEST_CLIENT.set_cookie(key="full_name", value=user)

    # 获取授权码
    with suppress_stdout():
        resp = make_request(
            target=TEST_CLIENT.get,
            args=("/api/method/frappe.integrations.oauth2.authorize",),
            kwargs={
                "query_string": {
                    "client_id": client_id,
                    "scope": scope,
                    "response_type": response_type,
                    "redirect_uri": redirect_uri,
                    "state": nonce,
                },
                "follow_redirects": True,
                "base_url": "http://192.168.32.20",
                "environ_base": {
                    "REMOTE_USER": user,
                    "HTTP_COOKIE": f"sid={sid}; user_id={user}; system_user=yes",
                    "wsgi.url_scheme": "http",
                    "SERVER_NAME": "192.168.32.20",
                    "SERVER_PORT": "80"
                }
            },
            site=frappe.local.site
        )

    # 打印响应信息以进行调试
    print("Initial Response URL:", resp.request.url)
    print("Final Response URL:", resp.url if hasattr(resp, 'url') else 'No URL')
    print("Response Query String:", resp.request.environ.get("QUERY_STRING"))
    print("Response Cookies:", resp.headers.get('Set-Cookie', 'No cookies'))
    print("Response Status:", resp.status_code)
    print("Response Headers:", resp.headers)
    
    # 从响应中获取重定向 URL
    query = parse_qs(resp.request.environ.get("QUERY_STRING", ""))
    print("Query:", query)
    
    # 首先检查最终响应 URL 中是否有授权码
    final_query = parse_qs(resp.url.split('?')[1]) if hasattr(resp, 'url') and '?' in resp.url else {}
    if "code" in final_query:
        auth_code = final_query["code"][0]
        print("Authorization code found in final response:", auth_code)
    elif 'redirect-to' in query:
        redirect_url = query['redirect-to'][0]
        print("Redirect URL:", redirect_url)
        
        # 访问重定向 URL
        with suppress_stdout():
            redirect_resp = make_request(
                target=TEST_CLIENT.get,
                args=(redirect_url,),
                kwargs={
                    "follow_redirects": True,
                    "base_url": "http://192.168.32.20",
                    "environ_base": {
                        "REMOTE_USER": user,
                        "HTTP_COOKIE": f"sid={sid}; user_id={user}; system_user=yes",
                        "wsgi.url_scheme": "http",
                        "SERVER_NAME": "192.168.32.20",
                        "SERVER_PORT": "80"
                    }
                },
                site=frappe.local.site
            )
        
        # 从重定向响应中获取授权码
        print("Final Redirect URL:", redirect_resp.url if hasattr(redirect_resp, 'url') else 'No URL')
        print("Redirect Response Cookies:", redirect_resp.headers.get('Set-Cookie', 'No cookies'))
        print("Redirect Response Status:", redirect_resp.status_code)
        print("Redirect Response Headers:", redirect_resp.headers)
        final_query = parse_qs(redirect_resp.url.split('?')[1]) if hasattr(redirect_resp, 'url') and '?' in redirect_resp.url else {}
        
        if "code" in final_query:
            auth_code = final_query["code"][0]
            print("Authorization code found in redirect:", auth_code)
        else:
            print("No authorization code found in redirect response")
            print("Response status:", redirect_resp.status_code)
            print("Response headers:", redirect_resp.headers)
            return {"error": "No authorization code found in redirect"}
    else:
        print("No redirect URL or code found in response")
        print("Response status:", resp.status_code)
        print("Response headers:", resp.headers)
        return {"error": "No redirect URL or code found"}

    # 请求 bearer token
    token_response = make_request(
        target=TEST_CLIENT.post,
        args=("/api/method/frappe.integrations.oauth2.get_token",),
        kwargs={
            "headers": {
                **form_header,
                "Cookie": f"sid={sid}; user_id={user}; system_user=yes"
            },
            "data": encode_params({
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "scope": scope,
            }),
            "base_url": "http://192.168.32.20",
            "environ_base": {
                "REMOTE_USER": user,
                "HTTP_COOKIE": f"sid={sid}; user_id={user}; system_user=yes",
                "wsgi.url_scheme": "http",
                "SERVER_NAME": "192.168.32.20",
                "SERVER_PORT": "80"
            }
        },
        site=frappe.local.site
    )

    # 解析 bearer token json
    try:
        bearer_token = token_response.json
        print("Bearer token response:", bearer_token)
        return bearer_token
    except Exception as e:
        print("Error parsing token response:", str(e))
        print("Raw response:", token_response.get_data(as_text=True))
        return {"error": "Failed to parse token response"}

