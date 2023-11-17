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
            "fieldtype": "data",
            "insert_after": "territory",
        }
    ]

    return {
        "Company": custom_fields_company,
        "Customer": custom_fields_customer
    }
