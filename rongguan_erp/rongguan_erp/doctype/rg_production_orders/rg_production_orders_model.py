def get_default_production_order_data(partial_data=None):
    """
    提供 RG Production Orders 文档的默认数据结构
    
    参数:
        partial_data (dict, optional): 包含部分需要合并的数据字典。默认为 None。
    
    返回:
        dict: RG Production Orders 文档的完整数据字典
    """
    default_data = {
        "doctype": "RG Production Orders",
        "notificationNumber": "",
        "customerId": "",
        "businessType": "",
        "orderType": "",
        "orderNumber": "",
        "factoryDeadline": None,
        "productName": "",
        "orderStatus": "",
        "orderDate": None,
        "deliveryDate": None,
        "contractNumber": "",
        "followerId": "",
        "paperPatternMakerId": "",
        "mark": "",
        "salesId": "",
        "patternNumber": "",
        "countryCode": "",
        "factoryId": "",
        "quantity": 0,
        "processLine": "",
        "custom_copy_from": "",
        "displayImageData": {
            "front": {"file_url": ""},
            "back": {"file_url": ""},
            "brandLabel": {"file_url": ""},
            "washLabel": {"file_url": ""}
        },
        "materialData": {
            "itemGroup": "",
            "selectedColorChart": {},
            "selectedSizeChart": {},
            "materialList": []
        },
        "processSteps": [],
        "attachments": []
    }

    if partial_data:
        # 注意：这里进行浅层更新，如果需要深层合并，需要更复杂的逻辑
        default_data.update(partial_data)
        
    return default_data
