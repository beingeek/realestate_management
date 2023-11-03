
import frappe
from frappe import _
from frappe.model.document import Document


#################### Get Plot & Base document data for Property Transfer #############


def validate(doc, method):
    if doc.get('doctype') == 'Re-Purchase or Cancel' and doc.is_new():
        if not doc.get('plot_no') and doc.get('docstatus') == 0:
            frappe.throw("Please enter a plot number before saving the document.")

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

#################### Get installment paid Amount for Payment Entry Docuemnt #############

@frappe.whitelist()
def get_payment_list_from_booking_document(doc_no):
        sql_query = """
SELECT 
    x.Installment,
    x.date,
    x.remarks,
    x.idx,
    x.receivable_amount
FROM (
    SELECT
        d.Installment,
        d.date,
        d.remarks,
        d.idx,
        d.amount - IFNULL(
            (
                SELECT SUM(b.paid_amount) AS paid_amount
                FROM `tabPayment Entry` AS a
                INNER JOIN `tabCustomer Payment Installment` AS b
                ON a.name = b.parent
                WHERE a.docstatus = 1
                AND a.a.custom_document_number = c.name
                AND b.base_doc_idx = d.idx
                AND a.custom_plot_no = c.plot_no
            ),
            0
        ) AS receivable_amount
    FROM
        `tabPlot Booking` AS c
    INNER JOIN
        `tabInstallment Payment Plan` AS d
    ON
        c.name = d.parent
    WHERE
        c.name = %s
    ORDER BY 
        d.date ASC
) x
WHERE 
    x.receivable_amount <> 0
ORDER BY x.date
limit 5;
"""
        data = frappe.db.sql(sql_query, (doc_no), as_dict=True)
        return data
 
@frappe.whitelist()
def get_payment_list_from_transfer_document(doc_no):
        sql_query = """
        SELECT 
            x.Installment,
            x.date,
            x.remarks,
            x.idx,
            x.receivable_amount
        FROM (
            SELECT
                d.Installment,
                d.date,
                d.remarks,
                d.idx,
                d.updated_receivable_amount - IFNULL((
                    SELECT SUM(b.paid_amount) AS paid_amount
                    FROM `tabPayment Entry` AS a
                    INNER JOIN `tabCustomer Payment Installment` AS b
                    ON a.name = b.parent
                    WHERE a.docstatus = 1
                    AND a.custom_document_number = c.name
                    AND b.base_doc_idx = d.idx
                    AND a.custom_plot_no = c.plot_no
                    ),
                    0
                ) AS receivable_amount
            FROM
        `tabProperty Transfer` AS c
    INNER JOIN
        `tabProperty Transfer installment` AS d
    ON
        c.name = d.parent
    WHERE
        c.name = %s
    ORDER BY 
        d.date ASC
) x
WHERE 
    x.receivable_amount <> 0
ORDER BY x.date
limit 5;
"""
        data = frappe.db.sql(sql_query, (doc_no), as_dict=True)
        return data

################ plot_master_data_booking_document_ststus_update #####################

@frappe.whitelist()
def plot_master_data_booking_document_status_update(transfer):
    try:
        propertyTransfer = frappe.get_doc("Property Transfer", transfer)
        
        if propertyTransfer.plot_no:
            plot_master = frappe.get_doc("Plot List", propertyTransfer.plot_no)
            
            plot_master.client_name     = propertyTransfer.to_customer
            plot_master.address         = propertyTransfer.to_address
            plot_master.father_name     = propertyTransfer.to_father_name
            plot_master.cnic            = propertyTransfer.to_cnic
            plot_master.mobile_no       = propertyTransfer.to_mobile_no
            plot_master.sales_agent     = propertyTransfer.sales_broker

        if propertyTransfer.document_number:
            Plot_booking = frappe.get_doc("Plot Booking", propertyTransfer.document_number)
            Plot_booking.status = "Property Transfer"   
            
            plot_master.save()
            Plot_booking.save()
            frappe.db.commit()
            
            return "Success"
        else:
            return "Plot number not specified in the Plot Booking document."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return "Failed"


@frappe.whitelist()
def plot_master_data_booking_document_status_update_reversal(transfer):
    try:
        propertyTransfer = frappe.get_doc("Property Transfer", transfer)
        
        if propertyTransfer.plot_no:
            plot_master = frappe.get_doc("Plot List", propertyTransfer.plot_no)
            
            plot_master.client_name     = propertyTransfer.from_customer
            plot_master.address         = propertyTransfer.from_address
            plot_master.father_name     = propertyTransfer.from_father_name
            plot_master.cnic            = propertyTransfer.from_cnic
            plot_master.mobile_no       = propertyTransfer.from_mobile_no
            plot_master.sales_agent     = propertyTransfer.from_sales_broker
        
        if propertyTransfer.document_number:
            Plot_booking = frappe.get_doc("Plot Booking", propertyTransfer.document_number)
            Plot_booking.status = "Active"
            
            plot_master.save()
            Plot_booking.save()

            frappe.db.commit()
            
            return "Success"
        else:
            return "Plot number not specified in the Plot Booking document."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return "Failed"


#################### Create Journal Entry Docuemnt #############

@frappe.whitelist()
def create_journal_entry(property_transfer):
    pt_doc = frappe.get_doc("Property Transfer", property_transfer)

    company = frappe.get_doc("Company", pt_doc.company)
    transfer_account = company.custom_default_transfer_revenue_account
    default_receivable_account = company.default_receivable_account
    cost_center = company.cost_center
    
    journal_entry = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "voucher_no": property_transfer,
        "posting_date": pt_doc.doc_date,
        "user_remark": pt_doc.remarks,
        "custom_document_number": pt_doc.name,
        "custom_document_type": "Property Transfer",
        "custom_plot_no": pt_doc.plot_no
    })

    # Customer Account 
    # Debit entry 
    if pt_doc.paid_amount > 0:
        journal_entry.append("accounts", {
            "account": default_receivable_account,
            "debit_in_account_currency": pt_doc.paid_amount,
            "party_type": "Customer",
            "party": pt_doc.from_customer,
            "against": pt_doc.to_customer,
            "project": pt_doc.project,
            "custom_plot_no": pt_doc.plot_no,
            "cost_center": "",
            "is_advance": 0,
            "custom_document_number": pt_doc.name,
            "custom_document_type": "Property Transfer"
        })
    # Credit entry
        journal_entry.append("accounts", {
            "account": default_receivable_account,
            "credit_in_account_currency": pt_doc.paid_amount,
            "party_type": "Customer",
            "party": pt_doc.to_customer,
            "against": pt_doc.from_customer,
            "project": pt_doc.project,
            "custom_plot_no": pt_doc.plot_no,
            "cost_center": "",
            "is_advance": 0,
            "custom_document_number": pt_doc.name,
            "custom_document_type": "Property Transfer"
        })

    # Transfer Charges

    if pt_doc.transfer_charge > 0:
        # Debit entry for transfer charge
        for payment in pt_doc.payment_type:
            journal_entry.append("accounts", {
                "account": payment.ledger,
                "debit_in_account_currency": payment.amount,
                "against": default_receivable_account,
                "project": pt_doc.project,
                "custom_plot_no": pt_doc.plot_no,
                "cost_center": "",
                "is_advance": 0,
                "custom_document_number": pt_doc.name,
                "custom_document_type": "Property Transfer"
            })

        # Credit entry for transfer charge
        journal_entry.append("accounts", {
            "account": transfer_account,
            "credit_in_account_currency": pt_doc.transfer_charge,
            "against": pt_doc.from_customer,
            "project": pt_doc.project,
            "custom_plot_no": pt_doc.plot_no,
            "cost_center": cost_center,
            "is_advance": 0,
            "custom_document_number": pt_doc.name,
            "custom_document_type": "Property Transfer"
        })

    journal_entry.insert(ignore_permissions=True)
    journal_entry.submit()

    frappe.db.commit()

    return {"message": f"Journal Entry {journal_entry.name} created successfully", "journal_entry": journal_entry.name}


################ update the status of Property Transfer Document #####################

@frappe.whitelist()
def update_transfer_status(transfer):
    try:
        property_transfer = frappe.get_doc("Property Transfer", transfer)       
        if property_transfer:
            property_transfer.status = "Further Transferred"
            property_transfer.save(ignore_permissions=True)
            frappe.db.commit()
            return "Success"
        else:
            return "Error: Property Transfer document not found."
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update status"))
        return "Failed"


@frappe.whitelist()
def update_transfer_cancel_status(transfer):
    try:
        property_transfer = frappe.get_doc("Property Transfer", transfer)
        if property_transfer:
            property_transfer.status = "Active"
            property_transfer.save(ignore_permissions=True)
            frappe.db.commit()
            
            return "Success"
        else:
            return "Error: Property Transfer document not found."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update status"))
        return "Failed"

# ################# Update & cancel booking Document #############################

@frappe.whitelist()
def plot_master_data_transfer_document_status_update(transfer):
    try:
        propertyTransfer = frappe.get_doc("Property Transfer", transfer)
        
        if propertyTransfer.plot_no:
            plot_master = frappe.get_doc("Plot List", propertyTransfer.plot_no)
            
            plot_master.client_name     = propertyTransfer.to_customer
            plot_master.address         = propertyTransfer.to_address
            plot_master.father_name     = propertyTransfer.to_father_name
            plot_master.cnic            = propertyTransfer.to_cnic
            plot_master.mobile_no       = propertyTransfer.to_mobile_no
            plot_master.sales_agent     = propertyTransfer.sales_broker

        if propertyTransfer.document_number:
            Plot_booking = frappe.get_doc("Property Transfer", propertyTransfer.document_number)
            Plot_booking.status = "Further Transferred"   
            
            plot_master.save()
            Plot_booking.save()
            frappe.db.commit()
            
            return "Success"
        else:
            return "Plot number not specified in the Plot Booking document."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return "Failed"


@frappe.whitelist()
def plot_master_data_transfer_document_status_update_reversal(transfer):
    try:
        propertyTransfer = frappe.get_doc("Property Transfer", transfer)
        
        if propertyTransfer.plot_no:
            plot_master = frappe.get_doc("Plot List", propertyTransfer.plot_no)
            
            plot_master.client_name     = propertyTransfer.from_customer
            plot_master.address         = propertyTransfer.from_address
            plot_master.father_name     = propertyTransfer.from_father_name
            plot_master.cnic            = propertyTransfer.from_cnic
            plot_master.mobile_no       = propertyTransfer.from_mobile_no
            plot_master.sales_agent     = propertyTransfer.from_sales_broker
        
        if propertyTransfer.document_number:
            Plot_booking = frappe.get_doc("Property Transfer", propertyTransfer.document_number)
            Plot_booking.status = "Active"
            
            plot_master.save()
            Plot_booking.save()

            frappe.db.commit()
            
            return "Success"
        else:
            return "Plot number not specified in the Plot Booking document."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return "Failed"

@frappe.whitelist()
def check_accounting_period(doc_date):
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
        result = frappe.db.sql(sql_query, doc_date, as_dict=True)

        if not result:
            return {'is_open': None}

        return {'is_open': result[0]['closed']}
    except Exception as e:
        frappe.log_error(f"Error getting in period: {str(e)}")
        return {'is_open': None}




# from frappe import _

class PropertyTransfer(Document):
    pass

#     def before_insert(self):
#         self.validate_plot_no()

#     def validate_plot_no(self):
#         if not self.plot_no and self.docstatus == 0:
#             frappe.throw(_("Please enter a plot number before saving the document."))

#         # Use Frappe's ORM to check if any other document with the same plot_no is in draft state
#         existing_draft_doc = frappe.get_all(
#             "Re-Purchase or Cancel",
#             filters={"plot_no": self.plot_no, "docstatus": 0},
#             limit=1,
#         )

#         if existing_draft_doc:
#             frappe.throw(_("Another document with the same plot number is in draft state."))




    
