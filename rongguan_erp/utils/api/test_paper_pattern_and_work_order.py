import frappe
import json
import unittest
from rongguan_erp.utils.api.paper_pattern_and_work_order import create_paper_pattern_and_work_order

class TestPaperPatternAndWorkOrder(unittest.TestCase):
    def test_create_paper_pattern_and_work_order(self):
        paper_pattern_data = {
            "style_no": "dddd",
            "style_name": "SDK连衣裙-WHI-M",
            "style_code": "dsadfaf",
            "customer": "DEREK LAM 10 CROSBY",
            "fabric_info": "344343",
            "lining_info": "4334",
            "process_instructions": "343",
            "remarks": "3443",
            "material_usages": [
                {
                    "type": "面料",
                    "item_name": "2025年新款-2025年新款连衣裙",
                    "amount": 3434,
                    "unit": "Nos",
                    "remarks": "3434"
                }
            ]
        }

        work_order_data = {
            "naming_series": "MFG-WO-.YYYY.-",
            "production_item": "SDK连衣裙-WHI-M",
            "item_name": "SDK连衣裙-WHI-M",
            "bom_no": "BOM-SDK连衣裙-WHI-M-003",
            "company": "DTY",
            "qty": 1,
            "custom_work_oder_type": "纸样工单",
            "use_multi_level_bom": 1,
            "update_consumed_material_cost_in_project": 1,
            "wip_warehouse": "在制品 - D",
            "fg_warehouse": "在制品 - D",
            "transfer_material_against": "Work Order",
            "planned_start_date": "2025-06-24 04:46:06",
            "expected_delivery_date": "2025-05-31",
            "description": "SDK连衣裙-WHI-M",
            "stock_uom": "Nos",
            "required_items": [
                {
                    "item_code": "P30-桌腿",
                    "source_warehouse": "仓库 - D",
                    "item_name": "P30-桌腿",
                    "description": "P30-桌腿",
                    "allow_alternative_item": 0,
                    "include_item_in_manufacturing": 1,
                    "required_qty": 1,
                    "stock_uom": "Nos",
                    "rate": 40,
                    "amount": 40
                },
                {
                    "item_code": "2025年新款-2025年新款连衣裙",
                    "source_warehouse": "仓库 - D",
                    "item_name": "2025年新款连衣裙",
                    "description": "2025年新款连衣裙",
                    "allow_alternative_item": 0,
                    "include_item_in_manufacturing": 1,
                    "required_qty": 2,
                    "stock_uom": "米",
                    "rate": 0,
                    "amount": 0
                }
            ]
        }

        try:
            result = create_paper_pattern_and_work_order(
                json.dumps(paper_pattern_data),
                json.dumps(work_order_data)
            )
            self.assertIn("paper_pattern", result)
            self.assertIn("work_order", result)
            
            # 打印创建的单据号
            print("\n创建的单据号：")
            print(f"纸样单号: {result['paper_pattern']}")
            print(f"工单号: {result['work_order']}")
            
            # 获取并验证创建的文档
            paper_pattern = frappe.get_doc("RG Paper Pattern", result["paper_pattern"])
            work_order = frappe.get_doc("Work Order", result["work_order"])
            
            # 验证文档状态
            print("\n文档状态：")
            print(f"纸样单状态: {paper_pattern.docstatus}")
            print(f"工单状态: {work_order.docstatus}")
            
        except Exception as e:
            self.fail(f"接口调用异常: {e}")

if __name__ == "__main__":
    unittest.main() 