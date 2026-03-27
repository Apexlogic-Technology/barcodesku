// Bulk Barcode Label Print Page
frappe.pages['print-barcode-labels'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Print Barcode Labels',
		single_column: true
	});

	// Load JsBarcode
	frappe.require('https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js', function() {
		render_page(page, wrapper);
	});
};

function render_page(page, wrapper) {
	$(wrapper).find('.layout-main-section').html(`
		<div style="padding: 20px;">
			<div style="margin-bottom: 15px; display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap;">
				<div style="flex: 1; min-width: 200px;">
					<label style="font-weight: 600; display: block; margin-bottom: 4px;">Search & Add Items</label>
					<input id="item-search" class="form-control" placeholder="Type item name or code..." style="width: 100%;">
				</div>
				<div>
					<label style="font-weight: 600; display: block; margin-bottom: 4px;">Copies per label</label>
					<input id="copies" type="number" min="1" max="100" value="1" class="form-control" style="width: 80px;">
				</div>
				<div style="display: flex; gap: 8px;">
					<button class="btn btn-primary" onclick="load_all_items()">Load All Items</button>
					<button class="btn btn-default" onclick="clear_selection()">Clear</button>
					<button class="btn btn-success" onclick="do_print()">🖨 Print / Save PDF</button>
				</div>
			</div>

			<div id="selected-items" style="margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 6px;"></div>

			<div id="label-preview" style="border-top: 2px dashed #ccc; padding-top: 16px; display: flex; flex-wrap: wrap; gap: 8px;"></div>
		</div>

		<style>
			@media print {
				.layout-header, .layout-side-section, .page-head, nav, .no-print { display: none !important; }
				#selected-items, .page-title, [data-page-route] > :not(.layout-main) { display: none !important; }
				#label-preview { border: none; padding: 0; margin: 0; }
				body { background: white !important; }
			}
			.label-card {
				width: 85mm;
				min-height: 52mm;
				border: 1.5px solid #444;
				border-radius: 4px;
				padding: 8px 10px;
				display: inline-flex;
				flex-direction: column;
				align-items: center;
				justify-content: center;
				page-break-inside: avoid;
				background: white;
				font-family: Arial, sans-serif;
			}
			.label-item-name {
				font-size: 10.5px;
				font-weight: bold;
				text-align: center;
				margin-bottom: 3px;
				line-height: 1.3;
			}
			.label-sku {
				font-size: 8.5px;
				color: #555;
				margin-bottom: 5px;
			}
			.label-barcode-num {
				font-size: 7.5px;
				letter-spacing: 1.5px;
				font-family: monospace;
				margin-top: 2px;
			}
			.tag-badge {
				background: #f0f4ff;
				border: 1px solid #c5d5ff;
				border-radius: 20px;
				padding: 3px 10px;
				font-size: 12px;
				display: flex;
				align-items: center;
				gap: 6px;
			}
			.tag-badge .remove {
				cursor: pointer;
				color: #999;
				font-weight: bold;
			}
			.tag-badge .remove:hover { color: red; }
		</style>
	`);

	// Awesomplete-style search using Frappe Link
	var selected = [];
	var search_input = document.getElementById('item-search');

	$(search_input).on('keydown', function(e) {
		if (e.key === 'Enter') {
			var val = $(this).val().trim();
			if (val) add_item_by_name(val);
		}
	});

	frappe.ui.setup_link_field_hover(search_input, {
		doctype: 'Item',
		target: search_input,
		onselect: function(value) { add_item_by_name(value); }
	});
}

var selected_items = [];

function add_item_by_name(name) {
	if (selected_items.find(i => i.name === name)) return;
	frappe.call({
		method: 'barcodesku.barcodesku.page.print_barcode_labels.print_barcode_labels.get_items_for_print',
		args: { item_names: JSON.stringify([name]) },
		callback: function(r) {
			if (r.message && r.message.length) {
				r.message.forEach(item => {
					if (!selected_items.find(i => i.name === item.name)) {
						selected_items.push(item);
					}
				});
				render_labels();
			} else {
				frappe.msgprint('Item not found or has no barcode: ' + name);
			}
		}
	});
	document.getElementById('item-search').value = '';
}

function load_all_items() {
	frappe.call({
		method: 'frappe.client.get_list',
		args: { doctype: 'Item', fields: ['name'], limit_page_length: 500 },
		callback: function(r) {
			if (!r.message || !r.message.length) { frappe.msgprint('No items found.'); return; }
			var names = r.message.map(i => i.name);
			frappe.call({
				method: 'barcodesku.barcodesku.page.print_barcode_labels.print_barcode_labels.get_items_for_print',
				args: { item_names: JSON.stringify(names) },
				callback: function(r2) {
					selected_items = r2.message || [];
					render_labels();
				}
			});
		}
	});
}

function clear_selection() {
	selected_items = [];
	render_labels();
}

function render_labels() {
	var copies = parseInt(document.getElementById('copies').value) || 1;
	var badge_html = selected_items.map(i => `
		<span class="tag-badge">
			${frappe.utils.escape_html(i.item_name || i.name)}
			<span class="remove" onclick="remove_item('${i.name}')">✕</span>
		</span>
	`).join('');
	document.getElementById('selected-items').innerHTML = badge_html;

	var preview = document.getElementById('label-preview');
	preview.innerHTML = '';

	selected_items.forEach(function(item) {
		for (var c = 0; c < copies; c++) {
			var uid = 'bc_' + item.name.replace(/[^a-zA-Z0-9]/g, '_') + '_' + c;
			var card = document.createElement('div');
			card.className = 'label-card';
			card.innerHTML = `
				<div class="label-item-name">${frappe.utils.escape_html(item.item_name || item.name)}</div>
				${item.custom_sku ? `<div class="label-sku">SKU: ${frappe.utils.escape_html(item.custom_sku)}</div>` : ''}
				${item.barcode ? `
					<svg id="${uid}"></svg>
					<div class="label-barcode-num">${frappe.utils.escape_html(item.barcode)}</div>
				` : '<div style="color:#bbb;font-size:10px;margin-top:10px;">No barcode</div>'}
			`;
			preview.appendChild(card);

			if (item.barcode && typeof JsBarcode !== 'undefined') {
				try {
					JsBarcode('#' + uid, item.barcode, {
						format: 'CODE128',
						width: 1.4,
						height: 42,
						displayValue: false,
						margin: 0
					});
				} catch(e) {}
			}
		}
	});
}

function remove_item(name) {
	selected_items = selected_items.filter(i => i.name !== name);
	render_labels();
}

function do_print() {
	if (!selected_items.length) {
		frappe.msgprint('No items selected. Load items first.');
		return;
	}
	var copies = parseInt(document.getElementById('copies').value) || 1;

	// Build self-contained label HTML cards
	var cards_html = '';
	selected_items.forEach(function(item) {
		for (var c = 0; c < copies; c++) {
			var uid = 'pbc_' + Math.random().toString(36).substr(2, 8);
			cards_html += `
				<div class="label-card" style="width:85mm;min-height:52mm;border:1.5px solid #444;border-radius:4px;padding:8px 10px;display:inline-flex;flex-direction:column;align-items:center;justify-content:center;page-break-inside:avoid;background:white;font-family:Arial,sans-serif;margin:4px;vertical-align:top;">
					<div style="font-size:10.5px;font-weight:bold;text-align:center;margin-bottom:3px;line-height:1.3;">${frappe.utils.escape_html(item.item_name || item.name)}</div>
					${item.custom_sku ? `<div style="font-size:8.5px;color:#555;margin-bottom:5px;">SKU: ${frappe.utils.escape_html(item.custom_sku)}</div>` : ''}
					${item.barcode ? `
						<svg id="${uid}" data-barcode="${frappe.utils.escape_html(item.barcode)}"></svg>
						<div style="font-size:7.5px;letter-spacing:1.5px;font-family:monospace;margin-top:2px;">${frappe.utils.escape_html(item.barcode)}</div>
					` : '<div style="color:#bbb;font-size:10px;margin-top:10px;">No barcode</div>'}
				</div>`;
		}
	});

	var print_html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Barcode Labels</title>
<style>
	body { margin: 8mm; background: white; }
	@media print { body { margin: 5mm; } @page { margin: 5mm; } }
</style>
</head>
<body>
<div style="display:flex;flex-wrap:wrap;gap:6px;">
${cards_html}
</div>
<script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"><\/script>
<script>
window.onload = function() {
	document.querySelectorAll('svg[data-barcode]').forEach(function(el) {
		try {
			JsBarcode(el, el.getAttribute('data-barcode'), {
				format: 'CODE128', width: 1.4, height: 42, displayValue: false, margin: 0
			});
		} catch(e) {}
	});
	setTimeout(function() { window.print(); }, 800);
};
<\/script>
</body>
</html>`;

	var win = window.open('', '_blank');
	win.document.write(print_html);
	win.document.close();
}
