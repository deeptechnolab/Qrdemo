# Copyright (c) 2025, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.stock.utils import scan_barcode


class BoxBarCodeAssignment(Document):
    # def validate(self):
    #     self.check_barcode_serial_number()
    # self.create_repack_entry_on_stock_entry()

    def on_submit(doc, method=None):
        # ✅ Mark all related barcodes as used
        update_barcode_status(doc, 1)

    def on_cancel(doc, method=None):
        # 🔁 Mark all related barcodes as unused
        update_barcode_status(doc, 0)

    def create_repack_entry_on_stock_entry(self):
        """
        Create a stock entry for repacking when the document is submitted.
        """
        if not self.serial_no:
            frappe.throw(_("Serial Number is required."))

        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Repack"

        # 1. Add all items from child table
        for item_row in self.items:
            stock_entry.append(
                "items",
                {
                    "s_warehouse": "Stores - SPOSPL",
                    "item_code": item_row.item_code,
                    "qty": item_row.qty,
                    "uom": "Nos",
                },
            )

        # 2. Add the output item (main item from link field)
        stock_entry.append(
            "items",
            {
                "item_code": self.item,
                "qty": 1,
                "t_warehouse": "Stores - SPOSPL",
                "serial_no": self.serial_no,
                "use_serial_batch_fields": 1,
            },
        )
        stock_entry.append(
            "items",
            {
                "s_warehouse": "Stores - SPOSPL",
                "item_code": self.item,
                "qty": 1,
                # "serial_no": self.serial_no,
            },
        )

        stock_entry.insert()
        frappe.msgprint(_("Stock Entry created: {0}").format(stock_entry.name))

    def check_barcode_serial_number(self):
        if self.serial_no and self.qr_code:
            existing_serial_qr = frappe.db.get_value(
                "Box BarCode Assignment",
                {
                    "serial_no": self.serial_no,
                    "qr_code": self.qr_code,
                    "name": ["!=", self.name],
                },
                "name",
            )
            if existing_serial_qr:
                frappe.throw(
                    _("Serial Number and Bar Code already assigned in Box: {0}").format(
                        existing_serial_qr
                    )
                )

        if self.qr_code:
            existing_qr = frappe.db.get_value(
                "Box BarCode Assignment",
                {"qr_code": self.qr_code, "name": ["!=", self.name]},
                "name",
            )
            if existing_qr:
                frappe.throw(
                    _("Bar Code already assigned in Box: {0}").format(existing_qr)
                )

        if self.serial_no:
            existing_serial = frappe.db.get_value(
                "Box BarCode Assignment",
                {"serial_no": self.serial_no, "name": ["!=", self.name]},
                "name",
            )
            if existing_serial:
                frappe.throw(
                    _("Serial Number already assigned in Box: {0}").format(
                        existing_serial
                    )
                )


@frappe.whitelist()
def process_bar_code(scan_bar_code, docname=None):
    """
    Validate scanned barcode.

    Rules:
    - If barcode exists in the same record → allow (success).
    - If barcode exists in another record → reject (used).
    - If barcode not marked scanned but present in current doc → success (avoid duplicate row).
    - If new barcode → success.
    """

    if not scan_bar_code:
        frappe.throw("Bar Code is missing.")

    # Load current document if it exists
    current_doc = None
    if docname and not docname.startswith("new-"):
        current_doc = frappe.get_doc("Box BarCode Assignment", docname)

    # Fetch barcode info
    barcode = frappe.db.get_value(
        "BarCode",
        {"name": scan_bar_code},
        ["name", "item", "uom", "scanned"],
        as_dict=True,
    )

    if not barcode:
        return {"status": "error", "message": f"Barcode {scan_bar_code} not found."}
    

    # 🧩 Step 1 — Check if barcode exists in the current record's child table
    if current_doc:
        for row in current_doc.get("items", []):  # Adjust childtable fieldname
            if row.barcodes and scan_bar_code in row.barcodes:
                conversion_factor = (
                    frappe.db.get_value(
                        "UOM Conversion Detail",
                        {"parent": barcode.item, "uom": barcode.uom},
                        "conversion_factor",
                    )
                    or 1
                )

                return {
                    "status": "used",
                    "qr_code": barcode.name,
                    "item_code": barcode.item,
                    "uom": barcode.uom,
                    "qty": conversion_factor,
                    "message": f"✅ Barcode <b>{scan_bar_code}</b> already exists in this record.",
                }

    # 🧩 Step 2 — If marked scanned, check where it belongs
    if barcode.scanned:
        linked_record = frappe.db.get_value(
            "Items List",
            {"barcodes": ["like", f"%{scan_bar_code}%"]},
            "parent"
        )

        if current_doc and linked_record == current_doc.name:
            # Already in same record, allow
            conversion_factor = (
                frappe.db.get_value(
                    "UOM Conversion Detail",
                    {"parent": barcode.item, "uom": barcode.uom},
                    "conversion_factor",
                )
                or 1
            )

            return {
                "status": "success",
                "qr_code": barcode.name,
                "item_code": barcode.item,
                "uom": barcode.uom,
                "qty": conversion_factor,
                "message": f"✅ Barcode <b>{scan_bar_code}</b> already exists in this record.",
            }

        # 🚫 Used in another record
        msg = f"⚠️ Barcode <b>{scan_bar_code}</b> is already scanned."
        if linked_record:
            msg += f" It is linked with record <b>{linked_record}</b>."
        msg += " Cancel that record to reuse this barcode."

        return {"status": "used", "linked_record": linked_record, "message": msg}
    

    # 🧩 Step 3 — New barcode (not yet scanned anywhere)
    conversion_factor = (
        frappe.db.get_value(
            "UOM Conversion Detail",
            {"parent": barcode.item, "uom": barcode.uom},
            "conversion_factor",
        )
        or 1
    )

    return {
        "status": "success",
        "qr_code": barcode.name,
        "item_code": barcode.item,
        "uom": barcode.uom,
        "qty": conversion_factor,
        "message": f"✅ Barcode {scan_bar_code} linked successfully.",
    }



def update_barcode_status(doc, status):
    """
    Update scanned status (1 = used / 0 = unused)
    for both parent qr_code and all child barcodes.
    """
    barcode_ids = set()

    # ✅ Include parent QR code if present
    if getattr(doc, "qr_code", None):
        barcode_ids.add(doc.qr_code.strip())

    # ✅ Include all barcodes from child items
    for item in getattr(doc, "items", []):
        if getattr(item, "barcodes", None):
            for b in item.barcodes.splitlines():
                b = b.strip()
                if b:
                    barcode_ids.add(b)

    # ✅ Update barcode scanned status
    for barcode_id in barcode_ids:
        frappe.db.set_value("BarCode", barcode_id, "scanned", status)

    frappe.db.commit()


@frappe.whitelist()
def process_parent_qr(scan_bar_code, docname):
    """
    Process parent (Box-level) barcode scan.
    Ensures it’s unique and fetches item details.
    """
    if not scan_bar_code:
        frappe.throw("Bar Code is missing.")

    if docname and not docname.startswith("new-"):
        docname = frappe.get_doc("Box BarCode Assignment", docname)
    else:
        docname = None

    barcode = None

    barcode = frappe.db.get_value(
        "BarCode",
        {"name": scan_bar_code},
        ["name", "item", "uom", "scanned"],
        as_dict=True,
    )

    if not barcode:
        return {"status": "error", "message": f"Barcode {scan_bar_code} not found."}

    # ✅ If already used → find linked parent record
    if barcode.scanned:
        assigned_record = frappe.db.get_value(
            "Box BarCode Assignment", {"qr_code": barcode.name}, "name"
        )
        msg = f"⚠️ Barcode <b>{scan_bar_code}</b> already used."
        if assigned_record:
            msg += f" It is linked with record <b>{assigned_record}</b>."
        msg += " Cancel that record to reuse this barcode."

        return {"status": "used", "linked_record": assigned_record, "message": msg}

    elif docname and barcode.name == docname.qr_code:
        assigned_record = frappe.db.get_value(
            "Box BarCode Assignment", {"qr_code": barcode.name}, "name"
        )
        msg = f"⚠️ Barcode <b>{scan_bar_code}</b> already used."

        return {"status": "used", "linked_record": assigned_record, "message": msg}

    # ✅ Get conversion factor
    conversion_factor = (
        frappe.db.get_value(
            "UOM Conversion Detail",
            {"parent": barcode.item, "uom": barcode.uom},
            "conversion_factor",
        )
        or 1
    )

    return {
        "status": "success",
        "qr_code": barcode.name,
        "item_code": barcode.item,
        "uom": barcode.uom,
        "qty": conversion_factor,
        "message": f"✅ Parent QR {scan_bar_code} linked successfully.",
    }
