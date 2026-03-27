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

def get_active_rule(item_doc):
	# Try to find specific rule by company and item group
	rules = frappe.get_all("Barcode Rule", filters={
		"company": item_doc.company,
		"item_group": item_doc.item_group
	}, order_by="modified desc", limit=1)
	
	if not rules:
		# Try company only
		rules = frappe.get_all("Barcode Rule", filters={
			"company": item_doc.company,
			"item_group": ["is", "not set"]
		}, order_by="modified desc", limit=1)
		
	if not rules:
		# Try item group only
		rules = frappe.get_all("Barcode Rule", filters={
			"company": ["is", "not set"],
			"item_group": item_doc.item_group
		}, order_by="modified desc", limit=1)
	
	if not rules:
		# Generic rule
		rules = frappe.get_all("Barcode Rule", filters={
			"company": ["is", "not set"],
			"item_group": ["is", "not set"]
		}, order_by="modified desc", limit=1)
	
	if rules:
		return frappe.get_doc("Barcode Rule", rules[0].name)
	return None

def generate_code(item_doc):
	rule = get_active_rule(item_doc)
	
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
		# EAN 13 is 13 digits: Prefix + Sequence + Checksum. Total must be 12 before checksum.
		code12 = f"{prefix}{seq_str}"
		code12 = "".join([c for c in code12 if c.isdigit()]) # strip letters just in case
		code12 = code12.rjust(12, '0')[:12] # ensure exactly 12 digits
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
			
			if needs_sku or needs_barcode:
				code, btype = generate_code(doc)
				
				changed = False
				if needs_sku:
					doc.custom_sku = code
					changed = True
					
				if needs_barcode:
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
