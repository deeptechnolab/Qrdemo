// Copyright (c) 2025, ALYF GmbH and contributors
// For license information, please see license.txt
const debounceTimers = {};
function debounceValidate(fieldname, callback, delay = 500) {
    if (debounceTimers[fieldname]) clearTimeout(debounceTimers[fieldname]);
    debounceTimers[fieldname] = setTimeout(() => {
        callback();
    }, delay);
}


frappe.ui.form.on("BarCode Generator", {
    refresh: function (frm) {

        if (frm.doc.qr_generated) {

            frm.add_custom_button(__("Print Bora Bar Codes"), function () {
                const print_url = frappe.urllib.get_full_url(
                    `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&trigger_print=1&format=Bora%20BarCode%20Generator&no_letterhead=0&letterhead=Default&_lang=en`
                );

                window.open(print_url, "_blank");
            });

            frm.add_custom_button(__("Print Carton Bar Codes"), function () {
                const print_url = frappe.urllib.get_full_url(
                    `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&trigger_print=1&format=Carton%20BarCode%20Generator&no_letterhead=0&letterhead=Default&_lang=en`
                );

                window.open(print_url, "_blank");
            });
        }
    },
    onload: function (frm) {
    frm.set_query("item", function () {
      return {
        filters: {
          item_group: ["in", get_child_item_groups("Products")],
        },
      };
    });
  },
    generator_barcode(frm) {
        if (!frm.doc.qr_generated) {
            // Create a progress dialog
            let progress = 0;
            const total = frm.doc.number_of_qrcode || 100;
            const progressDialog = frappe.msgprint({
                message: __("Generating Bar Codes..."),
                indicator: "blue",
            });

            const interval = setInterval(() => {
                progress += 5;
                frappe.show_progress("Generating Bar Codes", progress, total, __("Please wait..."));
                if (progress >= total) clearInterval(interval);
            }, 200);

            frappe.call({
                method: "qr_demo.qr_demo.doctype.barcode_generator.barcode_generator.create_bar_code",
                args: {
                    bar_code_genrator_id: frm.doc.name,
                    number_of_qrcode: frm.doc.number_of_qrcode,
                    item: frm.doc.item,
                    uom: frm.doc.uom,
                },
                callback: function (response) {
                    clearInterval(interval);
                    frappe.hide_progress();

                    if (response.message === "success") {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: __(`${frm.doc.number_of_qrcode} Bar Code Generated Successfully!`)
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: __('Something went wrong while generating barcodes.')
                        });
                    }
                },
            });
        } else {
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Bar Codes have already been generated for this record.')
            });
        }
    },
    number_of_qrcode: function (frm) {
        debounceValidate("number_of_qrcode", () => {
            if (frm.doc.number_of_qrcode > 240) {
                frappe.msgprint({
                    title: __("Validation Error"),
                    message: __("You can generate a maximum of 240 QR Codes at a time."),
                    indicator: "red",
                });

                frm.set_value("number_of_qrcode", 240);
            }
        });
    },
});


function get_child_item_groups(parent_group) {
  let groups = [];
  frappe.call({
    method: "frappe.client.get_list",
    async: false,
    args: {
      doctype: "Item Group",
      filters: { parent_item_group: parent_group },
      fields: ["name"],
    },
    callback: function (r) {
      if (r.message) {
        groups = r.message.map((d) => d.name);
        groups.push(parent_group);
      }
    },
  });
  return groups;
}