
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate

class ClosedAccountingPeriod(frappe.ValidationError):
	pass

class PropertyTransfer(Document):
    
    def validate(self):
        self.validate_from_customer_and_to_customer()
        self.validate_transfer_charge_and_payment_type_total()
        self.validate_difference_field()
        self.validate_doc_date()
        self.validate_Check_customer_plot_master_data()
        self.validate_transfer_amount()
        self.validate_accounting_period()

    def on_submit(self):
        try:
            self.make_gl_entries()
        except Exception as e:
            frappe.msgprint(f"Error while making GL entries: {str(e)}")


    def validate_doc_date(self):
        if self.doc_date:
            doc_date = getdate(self.doc_date)
            today_date = today()
        if doc_date and doc_date > getdate(today_date):
            frappe.throw("Future Document date not Allowed.")
    
    def validate_from_customer_and_to_customer(self):
        if self.from_customer == self.to_customer:
            frappe.throw('From Customer and To Customer must be different')

    def validate_transfer_charge_and_payment_type_total(self):
        if self.transfer_charge != self.payment_type_total_amount:
            frappe.throw('Transfer Charge & Payment type total Should be equal')

    def validate_difference_field(self):
        if self.difference != 0:
            frappe.throw('Difference field should be zero')
    
    def validate_Check_customer_plot_master_data(self):
        if self.from_customer:
            client_name = frappe.get_value('Plot List', {'name': self.plot_no}, 'client_name')
            if client_name != self.from_customer:
                frappe.msgprint('The master data customer does not match the payment customer')
                frappe.throw('Validation Error: Customer mismatch')
    
    def validate_transfer_amount(self):
        if self.total_transfer_amount == 0:
            frappe.throw('The Transfer amount should not zero')


    def validate_accounting_period(doc, method=None):
        ap = frappe.qb.DocType("Accounting Period")
        cd = frappe.qb.DocType("Closed Document")
        accounting_period = (
            frappe.qb.from_(ap)
            .from_(cd)
            .select(ap.name)
            .where(
                (ap.name == cd.parent)
                & (ap.company == doc.company)
                & (cd.closed == 1)
                & (cd.document_type == doc.doctype)
                & (doc.doc_date >= ap.start_date)
                & (doc.doc_date <= ap.end_date)
            )
        ).run(as_dict=1)
        if accounting_period:
            frappe.throw(_("You cannot create a {0} within the closed Accounting Period {1}").format(
                doc.doctype, frappe.bold(accounting_period[0]["name"]),
            ClosedAccountingPeriod
        ))

    def make_gl_entries(self):
        if self.paid_amount != 0 or self.transfer_charge != 0:

            company = frappe.defaults.get_user_default("Company")
            transfer_account = company.custom_default_transfer_revenue_account
            default_receivable_account = company.default_receivable_account
            cost_center = company.cost_center
            
        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "voucher_no": self,
            "posting_date": self.doc_date,
            "user_remark": self.remarks,
            "custom_document_number": self.name,
            "custom_document_type": "Property Transfer",
            "custom_plot_no": self.plot_no
        })

        if self.paid_amount > 0:
            journal_entry.append("accounts", {
                "account": default_receivable_account,
                "debit_in_account_currency": self.paid_amount,
                "party_type": "Customer",
                "party": self.from_customer,
                "against": self.to_customer,
                "project": self.project,
                "custom_plot_no": self.plot_no,
                "cost_center": "",
                "is_advance": 0,
                "custom_document_number": self.name,
                "custom_document_type": "Property Transfer"
            })
            journal_entry.append("accounts", {
                "account": default_receivable_account,
                "credit_in_account_currency": self.paid_amount,
                "party_type": "Customer",
                "party": self.to_customer,
                "against": self.from_customer,
                "project": self.project,
                "custom_plot_no": self.plot_no,
                "cost_center": "",
                "is_advance": 0,
                "custom_document_number": self.name,
                "custom_document_type": "Property Transfer"
            })

        # Transfer Charges

        if self.transfer_charge > 0:
            for payment in self.payment_type:
                journal_entry.append("accounts", {
                    "account": payment.ledger,
                    "debit_in_account_currency": payment.amount,
                    "against": default_receivable_account,
                    "project": self.project,
                    "custom_plot_no": self.plot_no,
                    "cost_center": "",
                    "is_advance": 0,
                    "custom_document_number": self.name,
                    "custom_document_type": "Property Transfer"
                })

            # Credit entry for transfer charge
            journal_entry.append("accounts", {
                "account": transfer_account,
                "credit_in_account_currency": self.transfer_charge,
                "against": self.from_customer,
                "project": self.project,
                "custom_plot_no": self.plot_no,
                "cost_center": cost_center,
                "is_advance": 0,
                "custom_document_number": self.name,
                "custom_document_type": "Property Transfer"
            })

        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()

        frappe.db.commit()

        return {"message": f"Journal Entry {journal_entry.name} created successfully", "journal_entry": journal_entry.name}



################ plot_master_data_booking_document_ststus_update #####################

##on_submit

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

##on_cencel_event

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


################ update the status of Property Transfer Document #####################

##On_submit

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

##On_Cancel

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

##On_submit

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

##On_Cancel

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




################ Get Plot & Base document data for Property Transfer ############

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
