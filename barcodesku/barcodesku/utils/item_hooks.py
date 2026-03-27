import frappe
from io import BytesIO
from barcodesku.barcodesku.utils.generator import generate_code, has_barcode

try:
	import barcode
	from barcode.writer import ImageWriter
except ImportError:
	barcode = None

def validate(doc, method):
	if doc.get("custom_sku"):
		# Ensure unique SKU
		exists = frappe.db.get_value("Item", {"custom_sku": doc.custom_sku, "name": ["!=", doc.name or ""]})
		if exists:
			frappe.throw(f"SKU '{doc.custom_sku}' is already assigned to Item {exists}.", frappe.UniqueValidationError)
			
	if doc.get("barcodes"):
		# Ensure unique Barcodes
		for row in doc.barcodes:
			if row.barcode:
				exists = frappe.db.get_value("Item Barcode", {"barcode": row.barcode, "parent": ["!=", doc.name or ""]})
				if exists:
					frappe.throw(f"Barcode '{row.barcode}' is already assigned to Item {exists}.", frappe.UniqueValidationError)

def auto_generate_barcode_and_sku(doc, method):
	try:
		settings = frappe.get_single("Barcode SKU Settings")
		if not settings.enable_auto_generation:
			return
	except Exception:
		return

	needs_sku = not doc.get("custom_sku")
	needs_barcode = not has_barcode(doc)

	if needs_sku:
		code, btype = generate_code(doc, target_apply_type="SKU Only")
		doc.custom_sku = code
		
	if needs_barcode:
		code, btype = generate_code(doc, target_apply_type="Barcode Only")
		doc.append("barcodes", {
			"barcode": code,
			"barcode_type": btype 
		})

def generate_barcode_image(doc, method):
	if getattr(doc, "flags", {}).get("ignore_barcode_image"):
		return
	
	try:
		settings = frappe.get_single("Barcode SKU Settings")
		if not settings.enable_auto_generation:
			return
	except Exception:
		return

	if not getattr(doc, "barcodes", None):
		return
		
	# Take the first barcode to generate an image for
	first_barcode = doc.barcodes[0].barcode
	btype = doc.barcodes[0].barcode_type
	
	# Check if File already exists
	existing_file = frappe.get_all("File", filters={
		"attached_to_doctype": "Item",
		"attached_to_name": doc.name,
		"file_name": ["like", f"%{first_barcode}.png"]
	})
	
	if existing_file:
		return
		
	if barcode:
		try:
			barcode_class = 'ean13' if btype.lower() == 'ean-13' else 'code128'
			BARCODE = barcode.get_barcode_class(barcode_class)
			bobj = BARCODE(first_barcode, writer=ImageWriter())
			fp = BytesIO()
			bobj.write(fp)
			
			file_doc = frappe.get_doc({
				"doctype": "File",
				"file_name": f"{first_barcode}.png",
				"attached_to_doctype": "Item",
				"attached_to_name": doc.name,
				"content": fp.getvalue(),
				"is_private": 0
			})
			file_doc.save(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(title="Barcode PNG Generation Error", message=str(e))
