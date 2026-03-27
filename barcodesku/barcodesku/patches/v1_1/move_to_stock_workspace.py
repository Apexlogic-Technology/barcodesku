import frappe
import json

def execute():
	# 1. Delete the custom Barcode SKU workspace
	if frappe.db.exists("Workspace", "Barcode SKU"):
		frappe.delete_doc("Workspace", "Barcode SKU", ignore_permissions=True)
		frappe.db.commit()

	# 2. Add shortcuts directly to the Stock Workspace
	if frappe.db.exists("Workspace", "Stock"):
		doc = frappe.get_doc("Workspace", "Stock")
		links_to_add = [
			{"type": "Link", "label": "Barcode Rules", "link_type": "DocType", "link_to": "Barcode Rule"},
			{"type": "Link", "label": "Barcode SKU Settings", "link_type": "DocType", "link_to": "Barcode SKU Settings"},
			{"type": "Link", "label": "SKU Renamer", "link_type": "DocType", "link_to": "SKU Renamer"},
			{"type": "Link", "label": "Scanner Validation", "link_type": "Page", "link_to": "scanner-validation"}
		]
		
		changed = False
		for l in links_to_add:
			exists = False
			for row in doc.links:
				if row.link_to == l["link_to"]:
					exists = True
					break
			if not exists:
				doc.append("links", l)
				changed = True
				
		if changed:
			doc.flags.ignore_permissions = True
			doc.save()
