import frappe

@frappe.whitelist()
def get_items_for_print(item_names):
	import json
	if isinstance(item_names, str):
		item_names = json.loads(item_names)
	
	results = []
	for name in item_names:
		item = frappe.db.get_value("Item", name,
			["name", "item_name", "custom_sku"], as_dict=True)
		if not item:
			continue
		barcodes = frappe.get_all("Item Barcode",
			filters={"parent": name},
			fields=["barcode", "barcode_type"],
			order_by="idx asc", limit=1)
		item["barcode"] = barcodes[0].barcode if barcodes else ""
		results.append(item)
	return results
