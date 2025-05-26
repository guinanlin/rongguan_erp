import jwt
import frappe
from frappe.utils.password import get_decrypted_password
from frappe import login_oauth_user

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
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        info.update({'name': decoded['username']})
        info.update({'sub': decoded['username']})
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
