# Copyright (c) 2023, CE Construction and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document



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
def get_plot_detail(plot_no):
    try:
        sql_query = """
			    SELECT x.name, x.plot_no, x.project , x.doc_type, x.customer, x.receivable_amount, x.DocDate, x.sales_broker From (
				SELECT  DISTINCT name, plot_no, project_name as project, 
                'Plot Booking' as Doc_type, client_name as customer, sales_broker, 
                total_sales_amount as receivable_amount, booking_date as DocDate 
                FROM `tabPlot Booking`
                WHERE status = 'Active'and docstatus = 1
                UNION ALL
                SELECT  DISTINCT name, plot_no, project as project, 
                'Property Transfer' as Doc_type, to_customer as customer, sales_broker, 
                total_transfer_amount as receivable_amount, doc_date as DocDate 
                FROM `tabProperty Transfer`
                WHERE status = 'Active'and docstatus = 1) x
                WHERE x.plot_no = %s
        """
        results = frappe.db.sql(sql_query, (plot_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.log_error(f"Error in get_available_plots: {str(e)}")
        return []

@frappe.whitelist()
def get_installment_list_from_booking(doc_no):
    try:
        sql_query = """
SELECT 
    x.Installment,
    x.date,
    x.remarks,
    x.idx,
    x.name,
    x.receivable_amount
FROM (
    SELECT
        c.name,
        d.Installment,
        d.date,
        d.remarks,
        d.idx,
        d.amount - IFNULL((
                SELECT SUM(b.paid_amount) AS paid_amount
                FROM `tabCustomer Payment` AS a
                INNER JOIN `tabCustomer Payment Installment` AS b
                ON a.name = b.parent
                WHERE a.docstatus = 1
                AND a.document_number = c.name
                AND b.base_doc_idx = d.idx
                AND a.plot_no = c.plot_no), 0 ) AS receivable_amount
    FROM
        `tabPlot Booking` AS c
    INNER JOIN
        `tabInstallment Payment Plan` AS d
    ON
        c.name = d.parent
    WHERE
        c.name = %s
    ORDER BY 
        d.date ASC ) x
WHERE 
    x.receivable_amount <> 0
ORDER BY x.date
limit 5;

        """
        results = frappe.db.sql(sql_query, (doc_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.log_error(f"Error in get_available_plots: {str(e)}")
        return []

@frappe.whitelist()
def get_installment_list_from_transfer(doc_no):
    try:
        sql_query = """
SELECT 
    x.Installment,
    x.date,
    x.remarks,
    x.idx,
    x.receivable_amount,
    x.name
FROM (
    SELECT
        c.name,
        d.Installment,
        d.date,
        d.remarks,
        d.idx,
        d.amount - IFNULL((
                SELECT SUM(b.paid_amount) AS paid_amount
                FROM `tabCustomer Payment` AS a
                INNER JOIN `tabCustomer Payment Installment` AS b
                ON a.name = b.parent
                WHERE a.docstatus = 1
                AND a.document_number = c.name
                AND b.base_doc_idx = d.idx
                AND a.plot_no = c.plot_no), 0 ) AS receivable_amount
    FROM
        `tabProperty Transfer` AS c
    INNER JOIN
        `tabInstallment Payment Plan - Transfer` AS d
    ON
        c.name = d.parent
    WHERE
        c.name = %s
    ORDER BY 
        d.date ASC ) x
WHERE 
    x.receivable_amount <> 0
ORDER BY x.date
limit 5;

        """
        results = frappe.db.sql(sql_query, (doc_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.log_error(f"Error in get_available_plots: {str(e)}")
        return []

@frappe.whitelist()
def create_journal_entry(cust_pmt):
    cpr_doc = frappe.get_doc("Customer Payment", cust_pmt)

    default_company = frappe.defaults.get_user_default("Company")
    default_receivable_account = frappe.get_value("Company", default_company, "default_receivable_account")

    journal_entry = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "voucher_no": cust_pmt,
        "posting_date": cpr_doc.payment_date,
	"naming_series": "ACC-PCOM-.YYYY.-",  
        "user_remark": cpr_doc.remarks,
        "custom_document_number": cpr_doc.name,
        "custom_document_type": "Customer Payment"
    })

    for payment in cpr_doc.payment_type:
        journal_entry.append("accounts", {
            "account": payment.ledger,
            "debit_in_account_currency": payment.amount,
            "against": default_receivable_account,
            "project": cpr_doc.project_name,
            "custom_plot_no": cpr_doc.plot_no,
            "cost_center": "",
            "is_advance": 0,
            "custom_document_number": cpr_doc.name,
            "custom_document_type": "Customer Payment"
        })

    # Credit entry
    journal_entry.append("accounts", {
        "account": default_receivable_account,
        "credit_in_account_currency": cpr_doc.total_paid_amount,
        "party_type": "Customer",
        "party": cpr_doc.customer_name,
        "project": cpr_doc.project_name,
        "custom_plot_no": cpr_doc.plot_no,
        "cost_center": "",
        "is_advance": 0,
        "custom_document_number": cpr_doc.name,
        "custom_document_type": "Customer Payment"
    })

    journal_entry.insert(ignore_permissions=True)
    journal_entry.submit()

    frappe.db.commit()

    return {"message": f"Journal Entry {journal_entry.name} created successfully", "journal_entry": journal_entry.name}

@frappe.whitelist()
def check_accounting_period(payment_date):
    try:
        sql_query = """
            SELECT closed
            FROM `tabAccounting Period` AS tap
            LEFT JOIN `tabClosed Document` AS tcd ON tcd.parent = tap.name
            WHERE tcd.document_type = 'Journal Entry' 
                AND MONTH(tap.end_date) = MONTH(%s) 
                AND YEAR(tap.end_date) = YEAR(%s)
                LIMIT 1;
        """
        result = frappe.db.sql(sql_query, (payment_date, payment_date), as_dict=True)

        if not result:
            return {'is_open': None}

        return {'is_open': result[0]['closed']}
    except Exception as e:
        frappe.log_error(f"Error getting in period: {str(e)}")
        return {'is_open': None}





class CustomerPayment(Document):
    pass

