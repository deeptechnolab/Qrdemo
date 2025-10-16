from frappe.model.document import Document
import frappe
from frappe.utils import now_datetime
from qr_demo.qr_code import get_qr_code, get_barcode


class BarCode(Document):
    def autoname(self):
        today = now_datetime()
        date_part = today.strftime("%y%m%d")  

        last_barcode = frappe.db.sql("""
            SELECT name FROM `tabBarCode`
            WHERE name LIKE %s ORDER BY name DESC LIMIT 1
        """, (date_part + '%',))

        if last_barcode:
            last_seq = int(last_barcode[0][0][6:])  
            new_seq = last_seq + 1
        else:
            new_seq = 1

        sequence = str(new_seq).zfill(7)  
        self.name = f"{date_part}{sequence}"  

    def validate(self):
        self.qr_code = get_barcode(self.name)
