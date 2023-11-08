
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate

class ClosedAccountingPeriod(frappe.ValidationError):
	pass

class CancellationProperty(Document):
   
    def validate(self):
        self.validate_posting_date()
        self.validate_Check_customer_plot_master_data()
        self.validate_accounting_period_open()
        self.validate_deduction_amount()
        
    def on_submit(self):
        self.make_gl_entries()
        self.update_plot_master()
        self.update_booking_document()
    
    def on_cancel(self):
        self.remove_plot()

    def validate_posting_date(self):
        if self.posting_date:
            posting_date = getdate(self.posting_date)
            today_date = today()
        if posting_date and posting_date > getdate(today_date):
            frappe.throw("Future Document date not Allowed.")
    
    def validate_Check_customer_plot_master_data(self):
        if self.customer:
            customer = frappe.get_value('Plot List', {'name': self.plot_no}, 'customer')
            if customer != self.customer:
                frappe.msgprint('The master data customer does not match the payment customer')
                frappe.throw('Validation Error: Customer mismatch')
    
    def validate_deduction_amount(self):
        if self.deduction != 0:
            total_payment_amount = 0
            for payment in self.payment_type:
                total_payment_amount += payment.amount
            if self.deduction != total_payment_amount:
                frappe.throw('Total deduction amount must be equal to the sum of payment type amounts')

    # def validate_acounting_period(self):
    #     sql_query = """
    #         SELECT closed
    #         FROM `tabAccounting Period` AS tap
    #         LEFT JOIN `tabClosed Document` AS tcd ON tcd.parent = tap.name
    #         WHERE tcd.document_type = 'Journal Entry' 
    #         AND MONTH(tap.end_date) = MONTH(%s) 
    #         AND YEAR(tap.end_date) = YEAR(%s)
    #         LIMIT 1;
    #     """
    #     result = frappe.db.sql(sql_query, (self.posting_date, self.posting_date), as_dict=True)
    #     if not result:
    #         return {'is_open': None}
    #     if result[0]['closed'] == 1:
    #         frappe.throw('The accounting period is not open. Please open the accounting period.')
    #     return {'is_open': 1}

    def validate_accounting_period_open(doc, method=None):
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
                & (doc.posting_date >= ap.start_date)
                & (doc.posting_date <= ap.end_date)
            )
        ).run(as_dict=1)

        if accounting_period:
            frappe.throw(_("You cannot create a {0} within the closed Accounting Period {1}").format(
                doc.doctype, frappe.bold(accounting_period[0]["name"]),
                ClosedAccountingPeriod
            ))

    def make_gl_entries(self):
        try:
            if self.received_amount != 0:
                company = frappe.defaults.get_user_default("Company")
                default_receivable_account = frappe.get_value("Company", company, "default_receivable_account")
                
                deductionAccount = frappe.db.get_single_value("Real Estate Settings", "default_transfer_revenue_account")
                if not deductionAccount:
                    frappe.throw('Please set Default deduction Account in Real Estate Settings')
                cost_center = frappe.db.get_single_value("Real Estate Settings", "cost_center")
                if not cost_center:
                    frappe.throw('Please set Cost Centre in Real Estate Settings')
        
                journal_entry = frappe.get_doc({
                    "doctype": "Journal Entry",
                    "voucher_type": "Journal Entry",
                    "voucher_no": self.name,
                    "posting_date": self.posting_date,
                    "user_remark": self.remarks,
                    "custom_plot_no": self.plot_no,
                    "custom_document_number": self.name,
                    "custom_document_type": "Cancellation Property"
                })

                for payment in self.payment_type:
                    journal_entry.append("accounts", {
                        "account": payment.ledger,
                        "credit_in_account_currency": payment.amount,
                        "against": default_receivable_account,
                        "project": self.project,
                        "custom_plot_no": self.plot_no,
                        "bank_account":payment.bank_account,
                        "cost_center": "",
                        "is_advance": 0,
                        "custom_document_number": self.name,
                        "custom_document_type":"Cancellation Property"
                    })

                journal_entry.append("accounts", {
                    "account": deductionAccount,
                    "credit_in_account_currency": self.final_payment,
                    "against": self.customer,
                    "project": self.project,
                    "custom_plot_no": self.plot_no,
                    "cost_center": cost_center,
                    "is_advance": 0,
                    "custom_document_number": self.name,
                    "custom_document_type": "Cancellation Property"
                })

                journal_entry.append("accounts", {
                    "account": default_receivable_account,
                    "debit_in_account_currency": self.received_amount,
                    "party_type": "Customer",
                    "party": self.customer,
                    "project": self.project,
                    "custom_plot_no": self.plot_no,
                    "cost_center": "",
                    "is_advance": 0,
                    "custom_document_number": self.name,
                    "custom_document_type": "Cancellation Property"
                })

                journal_entry.insert(ignore_permissions=True)
                journal_entry.submit()

                frappe.db.commit()
                frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Journal Entry", journal_entry.name)))
        except Exception as e:
            frappe.msgprint(f"Error while making GL entries: {str(e)}")

    def update_plot_master(self):
        try:
            plot_master = frappe.get_doc("Plot List", self.plot_no)
            plot_master.update({
                    'status'        : "Available", 
                    'customer'   : "", 
                    'address'       : "",
                    'contact_no'    : "", 
                    'sales_broker'  : "",
                    'father_name'   : "", 
                    'cnic'          : "",
                })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot List', plot_master.name)))
        except Exception as e:
            frappe.msgprint(f"Error while updating plot master Data: {str(e)}")

    def update_booking_document(self):
        try:
            if self.document_type == "Plot Booking":
                booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                booking_doc.update({'status' : "Cancel"})
                booking_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot Booking ', booking_doc.name)))

            if self.document_type == "Property Transfer":
                trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                trans_doc.update({'status' : "Cancel"})
                trans_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer ", trans_doc.name)))
        except Exception as e:
            frappe.msgprint(f"Error while updating document master Data: {str(e)}")    

    def remove_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        if plot_master.status == "Available" and plot_master.hold_for_sale == 0:
            
            plot_master.update({
                'status': "Booked", 'customer': self.customer, 'address': self.address,
                'contact_no': self.contact_no, 'sales_broker': self.sales_broker,
                'father_name': self.father_name, 'cnic': self.cnic,
            })
            plot_master.save()
            frappe.msgprint(_('{0} booked successfully').format(frappe.get_desk_link('Plot List', plot_master.name)))
            
            if self.document_type == "Property Transfer":
                trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                trans_doc.update({'status' : "Active"})
                trans_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer ", trans_doc.name)))
            
            if self.document_type == "Plot Booking":
                booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                booking_doc.update({'status' : "Active"})
                booking_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot Booking ', booking_doc.name)))
        else:
            frappe.throw(_("Error: The selected plot is not available for booking.")) 

    def before_insert(self):
        if self.status != "Active":
            frappe.throw('The document status should be Active at the time entered in the system')



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
                tpt.sales_amount as sales_amount,
                tpt.received_amount + IFNULL((
                    SELECT SUM(total_paid_amount)
                    FROM `tabCustomer Payment` tcpr
                    WHERE tcpr.docstatus = 1
                    AND tcpr.plot_no = tpt.plot_no
                    AND tcpr.document_number = tpt.name
                ), 0) AS received_amount
            FROM
                `tabProperty Transfer` tpt
            WHERE
                tpt.status = 'Active' AND tpt.docstatus = 1
            UNION ALL
            SELECT DISTINCT
                thb.name,
                thb.plot_no,
                thb.project as project,
                'Plot Booking' as Doc_type,
                thb.customer as customer,
                thb.sales_broker,
                thb.total_sales_amount as sales_amount,
                IFNULL((
                    SELECT SUM(total_paid_amount)
                    FROM `tabCustomer Payment` tcpr
                    WHERE tcpr.docstatus = 1
                    AND tcpr.plot_no = thb.plot_no
                    AND tcpr.document_number = thb.name
                ), 0) AS received_amount
            FROM
                `tabPlot Booking` thb
            WHERE
                thb.status = 'Active' AND thb.docstatus = 1)
            SELECT * FROM plot_detail WHERE plot_no = %s
        """
        results = frappe.db.sql(sql_query, (plot_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.log_error(f"Error in get_available_plots: {str(e)}")
        return []

