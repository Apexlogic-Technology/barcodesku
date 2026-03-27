app_name = "barcodesku"
app_title = "Barcode SKU Auto Generator"
app_publisher = "Apexlogic"
app_description = "Barcode and SKU Auto Generator for items in ERPNext"
app_email = "hello@apexlogic.com"
app_license = "mit"

doctype_js = {
	"Item": "public/js/item_form.js"
}

custom_fields = {
	"Item": [
		{
			"fieldname": "custom_sku",
			"label": "SKU",
			"fieldtype": "Data",
			"insert_after": "item_code",
			"in_global_search": 1,
			"in_standard_filter": 1,
			"in_list_view": 1,
			"search_index": 1,
			"read_only": 1,
			"no_copy": 1
		}
	],
	"Item Barcode": [
		{
			"fieldname": "custom_warehouse",
			"label": "Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"insert_after": "barcode_type"
		}
	]
}

after_migrate = "barcodesku.barcodesku.setup.after_migrate"

doc_events = {
	"Item": {
		"validate": "barcodesku.barcodesku.utils.item_hooks.validate",
		"before_save": "barcodesku.barcodesku.utils.item_hooks.auto_generate_barcode_and_sku",
		"on_update": "barcodesku.barcodesku.utils.item_hooks.generate_barcode_image",
		"before_insert": "barcodesku.barcodesku.utils.item_hooks.auto_generate_barcode_and_sku"
	}
}

