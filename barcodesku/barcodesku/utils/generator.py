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
		frappe.log_error(title="Barcode SKU: Skipped", message="Auto generation is disabled in settings.")
		return
		
	overwrite = settings.overwrite_existing
	items = frappe.get_all("Item", fields=["name", "item_group", "item_name"])
	
	sku_count = 0
	barcode_count = 0
	skip_count = 0

	for item in items:
		try:
			doc = frappe.get_doc("Item", item.name)
			
			# --- SKU ---
			existing_sku = frappe.db.get_value("Item", item.name, "custom_sku")
			needs_sku = not existing_sku or overwrite
			if needs_sku:
				sku_code, _ = generate_code(doc, target_apply_type="SKU Only")
				if sku_code:
					frappe.db.set_value("Item", item.name, "custom_sku", sku_code, update_modified=False)
					sku_count += 1

			# --- Barcode ---
			existing_barcodes = frappe.get_all("Item Barcode", filters={"parent": item.name})
			needs_barcode = not existing_barcodes or overwrite
			if needs_barcode:
				bar_code, bar_type = generate_code(doc, target_apply_type="Barcode Only")
				if bar_code:
					if overwrite:
						frappe.db.delete("Item Barcode", {"parent": item.name})
					row = frappe.get_doc({
						"doctype": "Item Barcode",
						"parenttype": "Item",
						"parentfield": "barcodes",
						"parent": item.name,
						"barcode": bar_code,
						"barcode_type": bar_type
					})
					row.insert(ignore_permissions=True)
					barcode_count += 1
			else:
				skip_count += 1

		except Exception as e:
			frappe.log_error(title=f"Barcode SKU Error: {item.name}", message=frappe.get_traceback())
			
	frappe.db.commit()
	frappe.log_error(
		title="Barcode SKU: Generation Complete",
		message=f"SKUs written: {sku_count} | Barcodes written: {barcode_count} | Skipped (already had data): {skip_count}"
	)

@frappe.whitelist()
def diagnose():
	"""Returns diagnostic info to help debug generation issues."""
	has_col = frappe.db.has_column("Item", "custom_sku")
	sku_rule = frappe.get_all("Barcode Rule", filters={"apply_to": ["in", ["SKU Only", "Both"]]}, pluck="name")
	bar_rule = frappe.get_all("Barcode Rule", filters={"apply_to": ["in", ["Barcode Only", "Both"]]}, pluck="name")
	sample = frappe.db.get_value("Item", {}, ["name", "custom_sku"], as_dict=True) or {}
	return {
		"custom_sku_column_exists": has_col,
		"sku_rules": sku_rule,
		"barcode_rules": bar_rule,
		"sample_item": sample
	}

@frappe.whitelist()
def undo_mass_generation():
	frappe.enqueue("barcodesku.barcodesku.utils.generator.process_undo_mass_generation", queue="long", timeout=1500)
	return "Enqueued"

def process_undo_mass_generation():
	items = frappe.get_all("Item", pluck="name")
	for item_name in items:
		try:
			frappe.db.set_value("Item", item_name, "custom_sku", "", update_modified=False)
			frappe.db.delete("Item Barcode", {"parent": item_name})
		except Exception:
			pass
	frappe.db.commit()
