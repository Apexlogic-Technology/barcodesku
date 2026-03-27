frappe.ui.form.on('Item', {
	refresh: function(frm) {
		// Lock SKU field once it already has a value
		if (frm.doc.custom_sku) {
			frm.set_df_property('custom_sku', 'read_only', 1);
		} else {
			frm.set_df_property('custom_sku', 'read_only', 0);
		}
	},
	custom_sku: function(frm) {
		// If user manually types a value, lock it on change too
		if (frm.doc.custom_sku) {
			frm.set_df_property('custom_sku', 'read_only', 1);
		}
	}
});
