import frappe

@frappe.whitelist()
def validate(barcode):
	item = frappe.db.get_value("Item", {"custom_sku": barcode}, ["name", "item_name", "custom_sku"], as_dict=True)
	
	if not item:
		parent_doc = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
		if parent_doc:
			item = frappe.db.get_value("Item", parent_doc, ["name", "item_name", "custom_sku"], as_dict=True)
			
	if item:
		return {"status": "valid", "item_name": item.item_name, "sku": item.custom_sku}
	return {"status": "invalid"}
