app_name = "barcodesku"
app_title = "Barcode SKU Auto Generator"
app_publisher = "Apexlogic"
app_description = "Barcode and SKU Auto Generator for items in ERPNext"
app_email = "hello@apexlogic.com"
app_license = "mit"

custom_fields = {
	"Item": [
		{
			"fieldname": "custom_sku",
			"label": "SKU",
			"fieldtype": "Data",
			"insert_after": "item_code",
			"read_only": 0,
			"no_copy": 1
		}
	]
}

doc_events = {
	"Item": {
		"before_save": "barcodesku.barcodesku.utils.item_hooks.auto_generate_barcode_and_sku",
		"on_update": "barcodesku.barcodesku.utils.item_hooks.generate_barcode_image",
		"before_insert": "barcodesku.barcodesku.utils.item_hooks.auto_generate_barcode_and_sku"
	}
}

