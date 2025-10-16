# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.utils import scan_barcode


class BarCodeGenerator(Document):
    pass


@frappe.whitelist(allow_guest=True)
def create_bar_code(bar_code_genrator_id, number_of_qrcode, item, uom):
    try:
        number_of_qrcode = int(number_of_qrcode)
        no_of_boxes = 0
        item_doc = frappe.get_doc("Item", item)
        # default_uom = item.stock_uom
        for item in item_doc.uoms:
            if item.uom == uom:
                no_of_boxes = item.conversion_factor
                break

        for _ in range(number_of_qrcode):
            qr_code = frappe.new_doc("BarCode")
            qr_code.qr_code_generator_id = bar_code_genrator_id
            qr_code.item = item
            qr_code.uom = uom
            qr_code.default_uom = item_doc.stock_uom
            qr_code.no_of_boxes = no_of_boxes
            qr_code.save()

        frappe.db.set_value(
            "BarCode Generator", bar_code_genrator_id, "qr_generated", 1
        )

        return "success"

    except Exception as e:
        frappe.log_error(f"Bar Code Generation Failed: {str(e)}", "Bar Code Error")
        frappe.throw(f"Error generating Bar Codes: {str(e)}")

