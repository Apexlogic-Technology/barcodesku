import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_migrate():
	custom_fields = {
		"Item": [
			{
				"fieldname": "custom_sku",
				"label": "SKU",
				"fieldtype": "Data",
				"insert_after": "item_code",
				"in_global_search": 1,
				"in_standard_filter": 1,
				"in_list_view": 1,
				"search_index": 1,
				"read_only": 1,
				"no_copy": 1
			}
		],
		"Item Barcode": [
			{
				"fieldname": "custom_warehouse",
				"label": "Warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"insert_after": "barcode_type"
			}
		]
	}
	create_custom_fields(custom_fields, ignore_validate=True)
	frappe.db.commit()
