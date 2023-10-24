# Copyright (c) 2023, CE Construction and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document



#################### Get Plot #############

@frappe.whitelist()
def get_plot_no(project):
    try:
        sql_query = """
                SELECT DISTINCT  x.plot_no, x.project FROM (
                SELECT DISTINCT name, plot_no, project  FROM `tabProperty Transfer`
                WHERE status = 'Active' and docstatus = 1
                UNION ALL
                SELECT DISTINCT name, plot_no, project_name as project FROM `tabPlot Booking`
                WHERE status = 'Active'and docstatus = 1) x
                Where x.project = %s
                Order by x.plot_no
        """
        results = frappe.db.sql(sql_query, (project), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.log_error(f"Error in get_available_plots: {str(e)}")
        return []

@frappe.whitelist()
def get_previous_document_detail(plot_no):
    try:
        sql_query = """
            WITH plot_detail AS (
    SELECT DISTINCT
        tpt.name,
        tpt.plot_no,
        tpt.project,
        'Property Transfer' as Doc_type,
        tpt.to_customer as customer,
        tpt.sales_broker,
        tpt.total_transfer_amount as receivable_amount,
        tpt.doc_date as DocDate,
        tpt.paid_amount + IFNULL((
            SELECT SUM(total_paid_amount)
            FROM `tabCustomer Payment` tcpr
            WHERE tcpr.docstatus = 1
              AND tcpr.plot_no = tpt.plot_no
              AND tcpr.document_number = tpt.name
        ), 0) AS paid_amount
    FROM
        `tabProperty Transfer` tpt
    WHERE
        tpt.status = 'Active' AND tpt.docstatus = 1
    UNION ALL
    SELECT DISTINCT
        thb.name,
        thb.plot_no,
        thb.project_name as project,
        'Plot Booking' as Doc_type,
        thb.client_name as customer,
        thb.sales_broker,
        thb.total_sales_amount as receivable_amount,
        thb.booking_date as DocDate,
        IFNULL((
            SELECT SUM(total_paid_amount)
            FROM `tabCustomer Payment` tcpr
            WHERE tcpr.docstatus = 1
              AND tcpr.plot_no = thb.plot_no
              AND tcpr.document_number = thb.name
        ), 0) AS paid_amount
    FROM
        `tabPlot Booking` thb
    WHERE
        thb.status = 'Active' AND thb.docstatus = 1
)
SELECT * FROM plot_detail WHERE plot_no = %s
        """
        results = frappe.db.sql(sql_query, (plot_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.log_error(f"Error in get_available_plots: {str(e)}")
        return []

@frappe.whitelist()
def post_journal_entry(can_pro):
    cp_doc = frappe.get_doc("Cancellation Property", can_pro)

    company = frappe.get_doc("Company", cp_doc.company)
    
    deductionAccount = company.custom_default_deduction_revenue_account
    default_receivable_account = company.default_receivable_account
    cost_center = company.cost_center
	
    journal_entry = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "voucher_no": can_pro,
        "posting_date": cp_doc.doc_date,
        "user_remark": cp_doc.remarks,
        "bill_no": cp_doc.plot_no,
        "custom_document_number": cp_doc.name,
        "custom_document_type": "Cancellation Property"
    })

	# Credit entry (Cash/Bank)
    for payment in cp_doc.payment_type:
        journal_entry.append("accounts", {
            "account": payment.ledger,
            "credit_in_account_currency": payment.amount,
            "against": default_receivable_account,
            "project": cp_doc.project,
            "custom_plot_no": cp_doc.plot_no,
            "bank_account":payment.bank_account,
            "cost_center": "",
            "is_advance": 0,
            "custom_document_number": cp_doc.name,
            "custom_document_type":"Cancellation Property"
        })

	#Credit Entry (Income)
    journal_entry.append("accounts", {
        "account": deductionAccount,
        "credit_in_account_currency": cp_doc.deduction,
        "against": cp_doc.customer,
        "project": cp_doc.project,
        "custom_plot_no": cp_doc.plot_no,
        "cost_center": cost_center,
        "is_advance": 0,
        "custom_document_number": cp_doc.name,
        "custom_document_type": "Cancellation Property"
    })

	#Debit Entry (Customer)
    journal_entry.append("accounts", {
        "account": default_receivable_account,
        "debit_in_account_currency": cp_doc.total_paid_amount,
        "party_type": "Customer",
        "party": cp_doc.customer,
        "project": cp_doc.project,
        "custom_plot_no": cp_doc.plot_no,
        "cost_center": "",
        "is_advance": 0,
        "custom_document_number": cp_doc.name,
        "custom_document_type": "Cancellation Property"
    })

    journal_entry.insert(ignore_permissions=True)
    journal_entry.submit()

    frappe.db.commit()

    return {"message": f"Journal Entry {journal_entry.name} created successfully", "journal_entry": journal_entry.name}

################ plot_master_data_update_&_document_ststus_update #####################

@frappe.whitelist()
def plot_master_data_and_document_status_update(can_pro):
    try:
        propertyTransfer = frappe.get_doc("Cancellation Property", can_pro)
        
        if propertyTransfer.plot_no:
            plot_master = frappe.get_doc("Plot List", propertyTransfer.plot_no)
            
            plot_master.status          = "Available"
            plot_master.client_name     = ""
            plot_master.address         = ""
            plot_master.father_name     = ""
            plot_master.cnic            = ""
            plot_master.mobile_no       = ""
            plot_master.sales_agent     = ""
            plot_master.save()

        if propertyTransfer.document_type == "Plot Booking" and propertyTransfer.document_number:
            booking_doc = frappe.get_doc("Plot Booking", propertyTransfer.document_number)
            booking_doc.status = "Cancel"
            booking_doc.save()

        elif propertyTransfer.document_type == "Property Transfer" and propertyTransfer.document_number:
            transfer_doc = frappe.get_doc("Property Transfer", propertyTransfer.document_number)
            transfer_doc.status = "Cancel"
            transfer_doc.save()

            frappe.db.commit()
        return "Success"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return "Failed"


@frappe.whitelist()
def plot_master_data_and_document_status_update_reversal(can_pro):
    try:
        cancelProperty = frappe.get_doc("Cancellation Property", can_pro)
        
        if cancelProperty.plot_no:
            plot_master = frappe.get_doc("Plot List", cancelProperty.plot_no)
            
            if plot_master.status == "Booked" and plot_master.hold_for_sale == 0:
                frappe.throw(_("Cannot proceed. The plot is Booked or hold for sale."))

            plot_master.status          = "Booked"
            plot_master.client_name     = cancelProperty.customer 
            plot_master.address         = cancelProperty.address
            plot_master.father_name     = cancelProperty.father_name
            plot_master.cnic            = cancelProperty.cnic
            plot_master.mobile_no       = cancelProperty.contact_no
            plot_master.sales_agent     = cancelProperty.sales_broker

            plot_master.save()

            if cancelProperty.document_type == "Plot Booking" and cancelProperty.document_number:
                booking_doc = frappe.get_doc("Plot Booking", cancelProperty.document_number)
                booking_doc.status = "Active"
                booking_doc.save()

            elif cancelProperty.document_type == "Property Transfer" and cancelProperty.document_number:
                transfer_doc = frappe.get_doc("Property Transfer", cancelProperty.document_number)
                transfer_doc.status = "Active"
                transfer_doc.save()

            frappe.db.commit()
        return "Success"

    except frappe.ValidationError as e:
        return str(e)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return "Failed"


@frappe.whitelist()
def check_plot_status(plot_no):
    plot_status = frappe.get_value("Plot List", plot_no, "status")
    return plot_status


class CancellationProperty(Document):
	pass
