import frappe

@frappe.whitelist()
def scan_barcode(search_value, *args, **kwargs):
    """Extended barcode scan logic for custom BarCode doctype."""

    # 1️⃣ Check cache manually (optional)
    cached_data = frappe.cache().get_value(f"custom_barcode:{search_value}")
    if cached_data:
        return cached_data

    # 2️⃣ Look up in your custom BarCode doctype
    barcode_data = frappe.db.get_value(
        "BarCode",
        {"name": search_value},
        ["item", "uom", "default_uom", "no_of_boxes"],
        as_dict=True,
    )

    print("Custom barcode scanned: \n\n\n\n\n\n\n\n\n\n", barcode_data)
    if barcode_data:
        result = {
            "item_code": barcode_data.item,
            "uom": barcode_data.default_uom,
            "qty": barcode_data.no_of_boxes,
            "barcode_type": "CustomBarCode",
        }


        # Cache result (avoid repeated DB lookups)
        frappe.cache().set_value(f"custom_barcode:{search_value}", result)
        return result

    # 3️⃣ Fallback to ERPNext’s native scan_barcode
    from erpnext.stock.utils import scan_barcode as erpnext_scan
    return erpnext_scan(search_value, *args, **kwargs)
