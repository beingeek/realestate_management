
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
            company = frappe.get_doc("Company", self.company)
            default_receivable_account = frappe.get_value("Company", company, "default_receivable_account")
            deductionAccount = frappe.get_value("Company", company, "default_deduction_revenue_account")

            if not default_receivable_account:
                frappe.throw('Please set Default Receivable Account in Company Settings')
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
            if flt(self.deduction) != 0.0:
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
                    'status'            : "Available", 
                    'customer'          : "", 
                    'address'           : "",
                    'contact_no'        : "", 
                    'sales_broker'      : "",
                    'father_name'       : "", 
                    'cnic'              : "",
                    'customer_type'     : "",
                    'share_percentage'  : "",
                })
            
            if self.customer_type == "Partnership":
                plot_master.set("customer_partnership", [])

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
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Booking", booking_doc.name)))

            if self.document_type == "Property Transfer":
                trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                trans_doc.update({'status' : "Cancel"})
                trans_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer", trans_doc.name)))
        except Exception as e:
            frappe.msgprint(f"Error while updating document master Data: {str(e)}")    

    def remove_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        if plot_master.status == "Available":
            plot_master.update({
                'status': "Booked", 'customer': self.customer, 'address': self.address,
                'contact_no': self.contact_no, 'sales_agent': self.sales_broker,
                'father_name': self.father_name, 'cnic': self.cnic,
                'customer_type': self.customer_type, 'share_percentage': self.share_percentage,
            })

            if self.customer_type == "Partnership":
                for customer in self.customer_partnership:
                    plot_master.append("customer_partnership", {
                    'customer': customer.customer,
                    'address': customer.address,
                    'mobile_no': customer.mobile_no,
                    'father_name': customer.father_name,
                    'id_card_no': customer.id_card_no,
                    'share_percentage': customer.share_percentage,
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



