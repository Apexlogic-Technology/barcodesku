import frappe

@frappe.whitelist()
def get_barcode_chart_data(*args, **kwargs):
	total_items = frappe.db.count("Item") or 1
	items_with_sku = frappe.db.count("Item", {"custom_sku": ["!=", ""]})
	return {
		"labels": ["Has Barcode/SKU", "Missing Barcode"],
		"datasets": [
			{"name": "Items", "values": [items_with_sku, total_items - items_with_sku]}
		]
	}
