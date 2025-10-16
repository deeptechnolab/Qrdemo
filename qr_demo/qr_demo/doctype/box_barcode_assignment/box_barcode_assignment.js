frappe.ui.form.on("Box BarCode Assignment", {

    refresh: function (frm) {
        frm.set_query('serial_no', function () {
            return {
                filters: {
                    'item_code': frm.doc.item
                }
            };
        });
    },
    scan_barcode: function (frm) {
        if (!frm.doc.scan_barcode) return;

        frappe.call({
            method: "qr_demo.qr_demo.doctype.box_barcode_assignment.box_barcode_assignment.process_bar_code",
            args: {
                scan_bar_code: frm.doc.scan_barcode,
                docname: frm.doc.name
            },
            callback: function (r) {
                const msg = r.message;
                if (!msg) return;

                // ❌ Barcode not found
                if (msg.status === "error") {
                    frappe.show_alert({
                        message: msg.message,
                        indicator: "red"
                    });
                    frm.set_value("scan_bar_code", "");
                    return;
                }

                // ✅ If already scanned, show error and stop
                if (msg.status === "used") {
                    frappe.msgprint({
                        title: __("Duplicate Barcode"),
                        message: msg.message,
                        indicator: "red"
                    });
                    frm.set_value("scan_barcode", "");
                    return; // ❌ Stop here — no success logic
                }

                // ✅ Success logic only for new barcodes
                if (msg.status === "success") {
                    // append or update item
                    const added = update_or_add_item(frm, {
                        item_code: msg.item_code,
                        qty: msg.qty || 1,
                        uom: msg.uom,
                        qr_code: msg.qr_code
                    });

                    // ✅ Only show success alert if quantity was actually added
                    if (added) {
                        frappe.show_alert({
                            message: msg.message,
                            indicator: "green"
                        });
                    }
                }

                frm.set_value("scan_barcode", "");
            }
        });
    },
    scan_bar_code: function (frm) {
        if (!frm.doc.scan_bar_code) return;

        frappe.call({
            method: "qr_demo.qr_demo.doctype.box_barcode_assignment.box_barcode_assignment.process_parent_qr",
            args: {
                scan_bar_code: frm.doc.scan_bar_code,
                docname: frm.doc.name
            },
            callback: function (r) {
                const msg = r.message;
                if (!msg) return;

                // ❌ Barcode not found
                if (msg.status === "error") {
                    frappe.show_alert({
                        message: msg.message,
                        indicator: "red"
                    });
                    frm.set_value("scan_bar_code", "");
                    return;
                }

                // ⚠️ Already used barcode
                if (msg.status === "used") {
                    frappe.msgprint({
                        title: __("Duplicate Parent QR"),
                        message: msg.message,
                        indicator: "red"
                    });
                    frm.set_value("scan_bar_code", "");
                    return;
                }

                // ✅ Success
                if (msg.status === "success") {
                    if (frm.doc.qr_code && frm.doc.qr_code !== msg.qr_code) {
                        frappe.confirm(
                            `A QR (<b>${frm.doc.qr_code}</b>) is already assigned.<br><br>
                        Replace it with <b>${msg.qr_code}</b>?`,
                            () => {
                                frm.set_value("qr_code", msg.qr_code);
                                frm.set_value("item", msg.item_code);
                                frm.set_value("uom", msg.uom);
                                frm.set_value("quantity", msg.qty);
                                frappe.show_alert({
                                    message: `✅ Parent QR updated to ${msg.qr_code}`,
                                    indicator: "green"
                                });
                            },
                            () => {
                                frappe.show_alert({
                                    message: "Parent QR replacement cancelled.",
                                    indicator: "orange"
                                });
                            }
                        );
                    } else {
                        frm.set_value("qr_code", msg.qr_code);
                        frm.set_value("item", msg.item_code);
                        frm.set_value("uom", msg.uom);
                        frm.set_value("quantity", msg.qty);
                        frappe.show_alert({
                            message: msg.message,
                            indicator: "green"
                        });
                    }
                }

                frm.set_value("scan_bar_code", "");
            }
        });
    },
});



function update_or_add_item(frm, item) {
    const max_qty = frm.doc.quantity || 0;
    const current_total = (frm.doc.items || []).reduce((sum, row) => sum + (row.qty || 0), 0);
    const new_total = current_total + item.qty;

    // 🚫 Prevent exceeding max allowed
    if (max_qty > 0 && new_total > max_qty) {
        const allowed_qty = Math.max(max_qty - current_total, 0);

        if (allowed_qty <= 0) {
            frappe.msgprint({
                title: __("Error"),
                message: __("Packing Quantity cannot exceed Unit Quantity."),
                indicator: "red"
            });

            frappe.show_alert({
                message: `⚠️ Box limit (${max_qty} ${frm.doc.uom}) reached. Cannot add more.`,
                indicator: "orange"
            });

            return false; // 🚫 nothing added
        }

        // 🟡 Auto-cap quantity
        add_or_update_row(frm, item, allowed_qty);
        frappe.show_alert({
            message: `Only ${allowed_qty} of ${item.item_code} added (auto-capped to box limit).`,
            indicator: "orange"
        });

        frm.refresh_field("items");
        update_packing_qty(frm);
        return true; // ✅ partial add
    }

    // ✅ Safe to add full qty
    add_or_update_row(frm, item, item.qty);
    frm.refresh_field("items");
    update_packing_qty(frm);
    return true; // ✅ added successfully
}



// ✅ Helper function for adding/updating a row
function update_or_add_item(frm, item) {
    const max_qty = frm.doc.quantity || 0;
    const current_total = (frm.doc.items || []).reduce((sum, row) => sum + (row.qty || 0), 0);
    const new_total = current_total + item.qty;

    if (max_qty > 0 && new_total > max_qty) {
        const allowed_qty = Math.max(max_qty - current_total, 0);

        if (allowed_qty <= 0) {
            frappe.msgprint({
                title: __("Error"),
                message: __("Packing Quantity cannot exceed Unit Quantity."),
                indicator: "red"
            });

            frappe.show_alert({
                message: `⚠️ Box limit (${max_qty} ${frm.doc.uom}) reached. Cannot add more.`,
                indicator: "orange"
            });

            // ❌ Don’t update or show total — nothing added
            return false;
        }

        // 🟡 Partially add up to allowed_qty
        add_or_update_row(frm, item, allowed_qty);
        frm.refresh_field("items");
        update_packing_qty(frm);  // ✅ safe, because something was added
        frappe.show_alert({
            message: `Only ${allowed_qty} of ${item.item_code} added (auto-capped to box limit).`,
            indicator: "orange"
        });
        return true;
    }

    // ✅ Add full qty
    add_or_update_row(frm, item, item.qty);
    frm.refresh_field("items");
    update_packing_qty(frm);
    return true;
}


// ✅ Helper function for adding/updating a row
// function add_or_update_row(frm, item, qty_to_add) {
//     let exists = false;

//     (frm.doc.items || []).forEach(row => {
//         if (row.item_code === item.item_code) {
//             row.qty = (row.qty || 0) + qty_to_add;
//             exists = true;

//             frappe.show_alert({
//                 message: `Updated <b>${item.item_code}</b> (Qty: ${row.qty})`,
//                 indicator: "green"
//             });
//         }
//     });

//     if (!exists && qty_to_add > 0) {
//         let child = frm.add_child("items");
//         child.item_code = item.item_code;
//         child.qty = qty_to_add;
//         child.uom = item.uom;
//         child.barcodes = item.qr_code;

//         frappe.show_alert({
//             message: `Added <b>${item.item_code}</b> (Qty: ${qty_to_add})`,
//             indicator: "green"
//         });
//     }
// }

function add_or_update_row(frm, item, qty_to_add) {
    let exists = false;

    // ✅ Add or update item
    (frm.doc.items || []).forEach(row => {
        if (row.item_code === item.item_code) {
            row.qty = (row.qty || 0) + qty_to_add;

            // Append barcode ID
            if (item.qr_code) {
                row.barcodes = row.barcodes
                    ? `${row.barcodes}\n${item.qr_code}`
                    : item.qr_code;
            }

            exists = true;
            frappe.show_alert({
                message: `✅ Barcode ${item.qr_code} linked successfully.`,
                indicator: "green"
            });
        }
    });

    if (!exists && qty_to_add > 0) {
        let child = frm.add_child("items");
        child.item_code = item.item_code;
        child.qty = qty_to_add;
        child.uom = item.uom;
        child.barcodes = item.qr_code;

        frappe.show_alert({
            message: `✅ Barcode ${item.qr_code} linked successfully.`,
            indicator: "green"
        });
    }

    frm.refresh_field("items");
}


function update_packing_qty(frm) {
    const total = (frm.doc.items || []).reduce((sum, row) => sum + (row.qty || 0), 0);
    if (frm.last_total_packing_qty !== total) {
        frappe.show_alert({
            message: `Total Packing Quantity: ${total}`,
            indicator: "green"
        });
        frm.last_total_packing_qty = total;  // store for comparison next time
    }
}
