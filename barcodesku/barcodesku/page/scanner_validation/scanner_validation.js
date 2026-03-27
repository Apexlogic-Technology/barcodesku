frappe.pages['scanner-validation'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Scanner Validation',
		single_column: true
	});
	
	$(frappe.render_template("scanner_validation")).appendTo(page.main);
	
	let barcode_input = "";
	let scan_timer = null;
	
	$(document).on('keypress', function(e) {
		if ($('#scanner-output').length === 0) return;
		
		if (e.key === 'Enter') {
			if (barcode_input.length > 0) {
				validate_barcode(barcode_input);
				barcode_input = "";
			}
		} else {
			barcode_input += e.key;
			clearTimeout(scan_timer);
			scan_timer = setTimeout(() => { barcode_input = ""; }, 100);
		}
	});
	
	function validate_barcode(code) {
		frappe.call({
			method: "barcodesku.barcodesku.page.scanner_validation.scanner_validation.validate",
			args: { barcode: code },
			callback: function(r) {
				const container = $('#scanner-output');
				container.empty();
				if (r.message && r.message.status === 'valid') {
					container.html(`<div style="background-color: #d4edda; color: #155724; padding: 20px; border-radius: 5px; border: 1px solid #c3e6cb;">
						<h3>✅ Valid</h3>
						<p style="font-size: 18px; margin-bottom: 5px;">Item: <b>${r.message.item_name}</b></p>
						<p style="font-size: 16px;">SKU: ${r.message.sku}</p>
					</div>`);
				} else {
					container.html(`<div style="background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 5px; border: 1px solid #f5c6cb;">
						<h3>❌ Invalid</h3>
						<p style="font-size: 16px;">Barcode <b>${code}</b> not found in the database.</p>
					</div>`);
				}
			}
		});
	}
};
