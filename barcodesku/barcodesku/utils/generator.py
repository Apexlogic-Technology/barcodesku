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

def get_active_rule(item_doc, apply_type="Both"):
	rule_filters = {"apply_to": ["in", [apply_type, "Both"]]}
	
	f1 = dict(rule_filters)
	f1.update({"company": item_doc.company, "item_group": item_doc.item_group})
	rules = frappe.get_all("Barcode Rule", filters=f1, order_by="modified desc", limit=1)
	
	if not rules:
		f2 = dict(rule_filters)
		f2.update({"company": item_doc.company, "item_group": ["is", "not set"]})
		rules = frappe.get_all("Barcode Rule", filters=f2, order_by="modified desc", limit=1)
		
	if not rules:
		f3 = dict(rule_filters)
		f3.update({"company": ["is", "not set"], "item_group": item_doc.item_group})
		rules = frappe.get_all("Barcode Rule", filters=f3, order_by="modified desc", limit=1)
	
	if not rules:
		f4 = dict(rule_filters)
		f4.update({"company": ["is", "not set"], "item_group": ["is", "not set"]})
		rules = frappe.get_all("Barcode Rule", filters=f4, order_by="modified desc", limit=1)
	
	if rules:
		return frappe.get_doc("Barcode Rule", rules[0].name)
	return None

def generate_code(item_doc, target_apply_type="Both"):
	rule = get_active_rule(item_doc, apply_type=target_apply_type)
	
	if not rule:
		# Fallback to Phase 1 Custom Logic
		ig_part = "".join([c for c in str(item_doc.item_group or "") if c.isalnum()]).upper()[:2]
		in_part = "".join([c for c in str(item_doc.item_name or "") if c.isalnum()]).upper()[:2]
		ig_part = ig_part.ljust(2, 'X')
		in_part = in_part.ljust(2, 'X')
		digits = f"{random.randint(0, 999999):06d}"
		return f"{ig_part}-{in_part}-{digits}", "Code 128"
		
	# Process Rules
	t = rule.rule_type
	if t == "Item Group & Name Abbreviation":
		ig_part = "".join([c for c in str(item_doc.item_group or "") if c.isalnum()]).upper()[:2]
		in_part = "".join([c for c in str(item_doc.item_name or "") if c.isalnum()]).upper()[:2]
		ig_part = ig_part.ljust(2, 'X')
		in_part = in_part.ljust(2, 'X')
		digits = f"{random.randint(0, 999999):06d}"
		return f"{ig_part}-{in_part}-{digits}", "Code 128"
		
	# Increment Sequence
	frappe.db.set_value("Barcode Rule", rule.name, "current_sequence", rule.current_sequence + 1)
	seq = rule.current_sequence + 1
	seq_str = str(seq).zfill(rule.sequence_length or 5)
	
	prefix = rule.prefix or ""
	
	if t == "Category Prefix + Sequence":
		return f"{prefix}{seq_str}", "Code 128"
	
	if t == "Code 128 Sequence":
		return seq_str, "Code 128"
		
	if t == "GS1 EAN-13":
		code12 = f"{prefix}{seq_str}"
		code12 = "".join([c for c in code12 if c.isdigit()]) 
		code12 = code12.rjust(12, '0')[:12] 
		check = calculate_ean13_checksum(code12)
		return f"{code12}{check}", "EAN-13"
		
	return f"SKU-{seq_str}", "Code 128"

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
	items = frappe.get_all("Item", fields=["name", "item_group", "item_name", "custom_sku", "company"])
	
	count = 0
	for item in items:
		try:
			doc = frappe.get_doc("Item", item.name)
			needs_sku = not doc.custom_sku or overwrite
			needs_barcode = not has_barcode(doc) or overwrite
			
			changed = False
			if needs_sku:
				code, _ = generate_code(doc, target_apply_type="SKU Only")
				doc.custom_sku = code
				changed = True
				
			if needs_barcode:
				code, btype = generate_code(doc, target_apply_type="Barcode Only")
				if overwrite:
					doc.set("barcodes", [])
				doc.append("barcodes", {
					"barcode": code,
					"barcode_type": btype 
				})
				changed = True
				
			if changed:
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.save()
				count += 1
		except Exception as e:
			frappe.log_error(title="Barcode Generation Error", message=f"Failed for {item.name}: {str(e)}")
			
	frappe.db.commit()

@frappe.whitelist()
def undo_mass_generation():
	frappe.enqueue("barcodesku.barcodesku.utils.generator.process_undo_mass_generation", queue="long", timeout=1500)
	return "Enqueued"

def process_undo_mass_generation():
	items = frappe.get_all("Item", filters={"custom_sku": ["!=", ""]}, pluck="name")
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
