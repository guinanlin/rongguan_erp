import re
import frappe


# 驼峰转下划线
def camel_to_snake(camel_case):
    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_case).lower()
    return snake_case

def hello():
    print("Hello") 

# 下划线转驼峰
def snake_to_camel(snake_case):
    words = snake_case.split('_')
    camel_case = words[0] + ''.join(word.title() for word in words[1:])
    return camel_case    