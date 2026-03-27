frappe.ui.form.on('SKU Renamer', {
	execute_rename: function(frm) {
		if (!frm.doc.item_link) {
			frappe.msgprint("Please select an item first.");
			return;
		}
		
		let args = { item_name: frm.doc.item_link };
		if (frm.doc.rename_custom_sku && frm.doc.new_custom_sku) {
			args.new_sku = frm.doc.new_custom_sku;
		}
		if (frm.doc.rename_item_code && frm.doc.new_item_code) {
			args.new_item_code = frm.doc.new_item_code;
		}
		
		frappe.confirm('Are you sure you want to execute these renaming operations? Global ID renames cannot be easily undone.', () => {
			frappe.call({
				method: "barcodesku.barcodesku.doctype.sku_renamer.sku_renamer.execute_rename",
				args: args,
				callback: function(r) {
					if (!r.exc) {
						frappe.msgprint("Success: " + (r.message || "No changes specified."));
						// clear fields
						frm.set_value("new_custom_sku", "");
						frm.set_value("new_item_code", "");
						frm.set_value("item_link", "");
					}
				}
			});
		});
	}
});
