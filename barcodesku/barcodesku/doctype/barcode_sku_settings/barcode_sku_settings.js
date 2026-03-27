// Copyright (c) 2024, Apexlogic and contributors
// For license information, please see license.txt

frappe.ui.form.on('Barcode SKU Settings', {
	refresh: function(frm) {
		
	},
	generate_for_existing_items: function(frm) {
		frappe.confirm('Are you sure you want to mass generate SKUs and Barcodes for existing items?', () => {
			frappe.call({
				method: "barcodesku.barcodesku.utils.generator.generate_for_existing",
				callback: function(r) {
					if(!r.exc) {
						frappe.msgprint('Background job enqueued successfully.');
					}
				}
			});
		});
	}
});
