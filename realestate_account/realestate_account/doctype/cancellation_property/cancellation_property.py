
import frappe
from frappe import _
from frappe.utils import flt
from realestate_account.controllers.real_estate_controller import RealEstateController, validate_accounting_period_open

class CancellationProperty(RealEstateController):  
    def validate(self):
        self.validate_posting_date()
        self.Check_customer_plot_master_data()
        self.validate_deduction_amount()
        validate_accounting_period_open(self)
        
    def on_submit(self):
        self.make_gl_entries()
        self.update_plot_master()
        self.update_booking_document()
    
    def on_cancel(self):
        self.remove_plot()
    
    def validate_deduction_amount(self):
        if flt(self.final_payment) != 0.0:
            total_payment_amount = 0.0
            for payment in self.payment_type:
                total_payment_amount += payment.amount
            if self.final_payment != total_payment_amount:
                frappe.throw('Total deduction amount must be equal to the sum of payment type amounts')

    def make_gl_entries(self):
        if flt(self.received_amount) != 0.0:
            company = frappe.get_doc("Company", self.company)

            default_receivable_account = frappe.get_value(company, self.company, "default_receivable_account")
            deductionAccount = frappe.get_value("Company", self.company, "default_deduction_revenue_account")
            if not deductionAccount:
                frappe.throw('Please set Default deduction Account in Company Settings')
            cost_center = frappe.get_value("Company", self.company, "real_estate_cost_center")
            if not cost_center:
                frappe.throw('Please set Cost Centre in Company Settings')
    
            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "voucher_no": self.name,
                "posting_date": self.posting_date,
                "user_remark": self.remarks,
                "real_estate_inventory_no": self.plot_no,
                "document_number": self.name,
                "document_type": "Cancellation Property"
            })

            for payment in self.payment_type:
                journal_entry.append("accounts", {
                    "account": payment.ledger,
                    "credit_in_account_currency": payment.amount,
                    "against": default_receivable_account,
                    "project": self.project,
                    "real_estate_inventory_no": self.plot_no,
                    "bank_account":payment.bank_account,
                    "cost_center": "",
                    "is_advance": 0,
                    "document_number": self.name,
                    "document_type":"Cancellation Property"
                })

            journal_entry.append("accounts", {
                "account": deductionAccount,
                "credit_in_account_currency": self.deduction,
                "against": self.customer,
                "project": self.project,
                "real_estate_inventory_no": self.plot_no,
                "cost_center": cost_center,
                "is_advance": 0,
                "document_number": self.name,
                "document_type": "Cancellation Property"
            })

            journal_entry.append("accounts", {
                "account": default_receivable_account,
                "debit_in_account_currency": self.received_amount,
                "party_type": "Customer",
                "party": self.customer,
                "project": self.project,
                "real_estate_inventory_no": self.plot_no,
                "cost_center": "",
                "is_advance": 0,
                "document_number": self.name,
                "document_type": "Cancellation Property"
            })

            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()

            frappe.db.commit()
            frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Journal Entry", journal_entry.name)))

    def update_plot_master(self):
        try:
            plot_master = frappe.get_doc("Plot List", self.plot_no)
            plot_master.update({
                    'status'        : "Available", 
                    'customer'      : "", 
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
        if plot_master.status == "Available":
            plot_master.update({
                'status': "Booked", 'customer': self.customer, 'address': self.address,
                'contact_no': self.contact_no, 'sales_agent': self.sales_broker,
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

