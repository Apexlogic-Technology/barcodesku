import frappe
import json

def execute():
	if frappe.db.exists("Workspace", "Stock"):
		doc = frappe.get_doc("Workspace", "Stock")
		
		# A. Strip out any old injections to start clean
		links_to_keep = []
		for l in doc.links:
			if l.label not in ["Barcode & SKU Tools", "Barcode Rules", "Barcode SKU Settings", "SKU Renamer", "Scanner Validation"]:
				links_to_keep.append(l)
		doc.links = links_to_keep

		# B. Inject Native Card Structure into the links table
		new_links = [
			{"type": "Card Break", "label": "Barcode & SKU Tools"},
			{"type": "Link", "label": "Barcode Rules", "link_type": "DocType", "link_to": "Barcode Rule"},
			{"type": "Link", "label": "Barcode SKU Settings", "link_type": "DocType", "link_to": "Barcode SKU Settings"},
			{"type": "Link", "label": "SKU Renamer", "link_type": "DocType", "link_to": "SKU Renamer"},
			{"type": "Link", "label": "Scanner Validation", "link_type": "Page", "link_to": "scanner-validation"}
		]
		for l in new_links:
			doc.append("links", l)
				
		# C. Inject the visual card block into the content layout
		try:
			content = json.loads(doc.content or "[]")
			# Sanitize old injections from JSON content array
			content = [c for c in content if not (c.get("data", {}).get("text") == "Barcode & SKU Tools") and not (c.get("data", {}).get("card_name") == "Barcode & SKU Tools")]
			
			# Append the native Card layout block
			content.append({"id": frappe.generate_hash(length=8), "type": "card", "data": {"card_name": "Barcode & SKU Tools"}})
			
			doc.content = json.dumps(content)
		except Exception:
			pass
				
		doc.flags.ignore_permissions = True
		doc.save()
