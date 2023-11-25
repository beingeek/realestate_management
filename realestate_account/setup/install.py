import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
	create_custom_fields(get_custom_fields())


def before_uninstall():
	delete_custom_fields(get_custom_fields())


def delete_custom_fields(custom_fields):
	for doctype, fields in custom_fields.items():
		for field in fields:
			custom_field_name = frappe.db.get_value(
				"Custom Field", dict(dt=doctype, fieldname=field.get("fieldname"))
			)
			if custom_field_name:
				frappe.delete_doc("Custom Field", custom_field_name)

		frappe.clear_cache(doctype=doctype)


def get_custom_fields():
    custom_fields_company = [
        {
            "label": "Real Estate Settings",
            "fieldname": "real_estate_settings",
            "fieldtype": "Tab Break",
            "insert_after": "expenses_included_in_valuation"
        },
        {
            "label": "Default Deduction Revenue Account",
            "fieldname": "default_deduction_revenue_account",
            "fieldtype": "Link",
            "options": "Account",
            "insert_after": "real_estate_settings",
        },
        {
            "label": "Default Transfer Revenue Account",
            "fieldname": "default_transfer_revenue_account",
            "fieldtype": "Link",
            "options": "Account",
            "insert_after": "default_deduction_revenue_account",
        },
        {
            "fieldname": "col_break_real_estate",
            "fieldtype": "Column Break",
            "insert_after": "default_transfer_revenue_account",
        },
        {
            "label": "Default Real Estate Cost Center",
            "fieldname": "real_estate_cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "insert_after": "col_break_real_estate",
        },
        {
            "label": "Commission Item",
            "fieldname": "commission_item",
            "fieldtype": "Link",
            "options": "Item",
            "insert_after": "real_estate_cost_center",
        }
    ]

    custom_fields_customer = [
        {
            "label": "Father Name",
            "fieldname": "father_name",
            "fieldtype": "Data",
            "insert_after": "territory",
			"allow_in_quick_entry":1,
			"reqd":1,
			"no_copy":1,
        },
		{
            "label": "ID Card No",
            "fieldname": "id_card_no",
            "fieldtype": "Data",
            "allow_in_quick_entry":1,
            "insert_after": "father_name",
			"reqd":1,
			"no_copy":1,
        },
		{
            "label": "Next of Kin",
            "fieldname": "next_of_kin",
            "fieldtype": "Data",
            "allow_in_quick_entry":1,
            "insert_after": "id_card_no",
			"reqd":1,
			"no_copy":1,
        }
    ]

    custom_fields_Journal_Entry = [
        {
            "label": "Document Type",
            "fieldname": "document_type",
            "fieldtype": "Link",
			"options": "DocType",
			"read_only":1,
			"no_copy":1,
            "insert_after": "cheque_date",
        },
		{
            "label": "Document Number",
            "fieldname": "document_number",
            "fieldtype": "Dynamic Link",
			"options": "document_type",
			"read_only":1,
			"no_copy":1,
            "insert_after": "document_type",
        },
		{
            "label": "Real Estate Inventory No.",
            "fieldname": "real_estate_inventory_no",
            "fieldtype": "Link",
			"options": "Plot List",
			"read_only":1,
			"no_copy":1,
            "insert_after": "document_number",
        }
    ]

    custom_fields_Journal_Entry_account = [
        {
            "label": "Document Type",
            "fieldname": "document_type",
            "fieldtype": "Link",
			"options": "DocType",
			"read_only":1,
			"no_copy":1,
            "insert_after": "cheque_date",
        },
		{
            "label": "Document Number",
            "fieldname": "document_number",
            "fieldtype": "Dynamic Link",
			"options": "document_type",
			"read_only":1,
			"no_copy":1,
            "insert_after": "document_type",
        },
		{
            "label": "Real Estate Inventory No.",
            "fieldname": "real_estate_inventory_no",
            "fieldtype": "Link",
			"options": "Plot List",
			"read_only":1,
			"no_copy":1,
            "insert_after": "document_number",
        }
    ]

    custom_fields_purchase_invoice = [
        {
            "label": "Document Number",
            "fieldname": "document_number",
            "fieldtype": "Link",
			"options": "Plot Booking",
			"read_only":1,
			"no_copy":1,
            "insert_after": "project",
        }
    ]

    # records = [
	# 		# Department
	# 		{
	# 			"doctype": "Department",
	# 			"department_name": _("All Departments"),
	# 			"is_group": 1,
	# 			"parent_department": "",
	# 			"__condition": lambda: not frappe.db.exists("Department", _("All Departments")),
	# 		},
	# 		{
	# 			"doctype": "Department",
	# 			"department_name": _("Accounts"),
	# 			"parent_department": _("All Departments"),
	# 			"company": name,
	# 		}
	# ]

    return {
        "Company": custom_fields_company,
        "Customer": custom_fields_customer,
		"Journal Entry": custom_fields_Journal_Entry,
		"Journal Entry Account" : custom_fields_Journal_Entry_account,
		"Purchase Invoice": custom_fields_purchase_invoice,
        # "": records
    }
