import frappe

@frappe.whitelist(allow_guest=False)
def scan(barcode):
	# 1. Direct match on custom_sku
	item = frappe.db.get_value("Item", {"custom_sku": barcode}, 
		["name", "item_name", "item_group", "description", "stock_uom", "standard_rate"], as_dict=True)
	
	if not item:
		# 2. Match on native internal Item Code
		item = frappe.db.get_value("Item", {"name": barcode}, 
			["name", "item_name", "item_group", "description", "stock_uom", "standard_rate"], as_dict=True)
		
	if not item:
		# 3. Match on native Barcodes child table lookup
		parent_doc = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
		if parent_doc:
			item = frappe.db.get_value("Item", parent_doc, 
				["name", "item_name", "item_group", "description", "stock_uom", "standard_rate"], as_dict=True)
			
	if item:
		# Optionally attempt to query physical item bounds in price list if not carrying standard rate.
		price = frappe.db.get_value("Item Price", {"item_code": item.name, "selling": 1}, "price_list_rate")
		if price:
			item.standard_rate = price
			
		return {
			"status": "success", 
			"item": item
		}
		
	return {
		"status": "not_found", 
		"message": f"Global Scanner failed: Barcode/SKU '{barcode}' completely unrecognized in the Item database."
	}
