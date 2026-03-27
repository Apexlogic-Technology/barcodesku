import frappe
import random

def calculate_ean13_checksum(code12):
	code12 = str(code12)
	if len(code12) != 12:
		return '0'
	sum1 = sum(int(code12[i]) for i in range(1, 12, 2)) * 3
	sum2 = sum(int(code12[i]) for i in range(0, 12, 2))
	check_digit = (10 - ((sum1 + sum2) % 10)) % 10
	return str(check_digit)

def _build_code_from_rule(rule, item_doc):
	"""Build a code string from a given rule. Returns (code, barcode_type)."""
	t = rule.rule_type
	
	if t == "Item Group & Name Abbreviation":
		ig_part = "".join([c for c in str(item_doc.get("item_group") or "") if c.isalnum()]).upper()[:2]
		in_part = "".join([c for c in str(item_doc.get("item_name") or "") if c.isalnum()]).upper()[:2]
		ig_part = ig_part.ljust(2, 'X')
		in_part = in_part.ljust(2, 'X')
		digits = f"{random.randint(0, 999999):06d}"
		return f"{ig_part}-{in_part}-{digits}", "Code-128"
	
	# Sequence-based rules - increment counter
	new_seq = rule.current_sequence + 1
	frappe.db.set_value("Barcode Rule", rule.name, "current_sequence", new_seq)
	seq_str = str(new_seq).zfill(rule.sequence_length or 5)
	prefix = rule.prefix or ""
	
	if t == "Category Prefix + Sequence":
		return f"{prefix}{seq_str}", "Code-128"
	
	if t == "Code 128 Sequence":
		return seq_str, "Code-128"
		
	if t == "GS1 EAN-13":
		code12 = f"{prefix}{seq_str}"
		code12 = "".join([c for c in code12 if c.isdigit()])
		code12 = code12.rjust(12, '0')[:12]
		check = calculate_ean13_checksum(code12)
		return f"{code12}{check}", "EAN-13"
		
	return f"SKU-{seq_str}", "Code-128"

def get_active_rule(item_doc, apply_type="Both"):
	"""Find the most specific applicable rule for this item."""
	rule_filters = {"apply_to": ["in", [apply_type, "Both"]]}
	
	company = item_doc.get("company")
	item_group = item_doc.get("item_group")
	
	specs = [
		{"company": company, "item_group": item_group},
		{"company": company, "item_group": ["is", "not set"]},
		{"company": ["is", "not set"], "item_group": item_group},
		{"company": ["is", "not set"], "item_group": ["is", "not set"]},
	]
	
	for extra in specs:
		f = dict(rule_filters)
		f.update(extra)
		rules = frappe.get_all("Barcode Rule", filters=f, order_by="modified desc", limit=1)
		if rules:
			return frappe.get_doc("Barcode Rule", rules[0].name)
	
	return None

def generate_code(item_doc, target_apply_type="Both"):
	"""Generate a code for the given target. Returns (code, barcode_type) or (None, None) if no rule."""
	rule = get_active_rule(item_doc, apply_type=target_apply_type)
	if not rule:
		return None, None
	return _build_code_from_rule(rule, item_doc)

def has_barcode(doc):
	if getattr(doc, "barcodes", None):
		return len(doc.barcodes) > 0
	return False

@frappe.whitelist()
def generate_for_existing():
	frappe.enqueue(
		"barcodesku.barcodesku.utils.generator.process_existing_items",
		queue="long",
		timeout=1500
	)
	return "Enqueued"

def process_existing_items():
	settings = frappe.get_single("Barcode SKU Settings")
	if not settings.enable_auto_generation:
		return
		
	overwrite = settings.overwrite_existing
	items = frappe.get_all("Item", fields=["name", "item_group", "item_name"])
	
	for item in items:
		try:
			doc = frappe.get_doc("Item", item.name)
			needs_sku = not doc.get("custom_sku") or overwrite
			needs_barcode = not has_barcode(doc) or overwrite
			changed = False

			if needs_sku:
				sku_code, _ = generate_code(doc, target_apply_type="SKU Only")
				if sku_code:
					doc.custom_sku = sku_code
					changed = True

			if needs_barcode:
				bar_code, bar_type = generate_code(doc, target_apply_type="Barcode Only")
				if bar_code:
					if overwrite:
						doc.set("barcodes", [])
					doc.append("barcodes", {
						"barcode": bar_code,
						"barcode_type": bar_type
					})
					changed = True
				
			if changed:
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.save()
		except Exception as e:
			frappe.log_error(title="Barcode Generation Error", message=f"Failed for {item.name}: {str(e)}")
			
	frappe.db.commit()

@frappe.whitelist()
def undo_mass_generation():
	frappe.enqueue("barcodesku.barcodesku.utils.generator.process_undo_mass_generation", queue="long", timeout=1500)
	return "Enqueued"

def process_undo_mass_generation():
	items = frappe.get_all("Item", pluck="name")
	for item_name in items:
		try:
			doc = frappe.get_doc("Item", item_name)
			doc.custom_sku = ""
			doc.set("barcodes", [])
			doc.flags.ignore_permissions = True
			doc.flags.ignore_mandatory = True
			doc.save()
		except Exception:
			pass
	frappe.db.commit()
