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
	},
	undo_mass_generation: function(frm) {
		frappe.confirm('DANGER: This will universally wipe all Custom SKUs and Barcode child records across all items so you can start completely fresh. Are you perfectly sure?', () => {
			frappe.call({
				method: "barcodesku.barcodesku.utils.generator.undo_mass_generation",
				callback: function(r) {
					if(!r.exc) {
						frappe.msgprint('Background Undo job enqueued successfully. Wait a few moments.');
					}
				}
			});
		});
	}
});
