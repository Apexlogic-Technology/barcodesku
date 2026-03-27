import frappe
from frappe.model.document import Document

class SKURenamer(Document):
	pass

@frappe.whitelist()
def execute_rename(item_name, new_sku=None, new_item_code=None):
	if not item_name: return
	
	messages = []
	if new_sku:
		frappe.db.set_value("Item", item_name, "custom_sku", new_sku)
		messages.append(f"Custom SKU updated to {new_sku}")
		
	if new_item_code:
		frappe.rename_doc("Item", item_name, new_item_code, ignore_permissions=True)
		messages.append(f"Item globally renamed to {new_item_code}")
		
	return " and ".join(messages)
