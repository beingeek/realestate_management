import frappe
from frappe import _
from frappe.utils import flt
from realestate_account.controllers.real_estate_controller import RealEstateController, validate_accounting_period_open

class PlotToken(RealEstateController):
    def validate(self):
        self.validate_payment_plan_and_token_amount()
        self.validate_posting_date()
        validate_accounting_period_open(self)
        self.validate_plot_booking()
        self.validate_token_amount()
        self.validate_valid_till_date()
    
    def on_submit(self):
        self.make_gl_entries()
        self.plot_token_update()
    
    def on_cancel(self):
        self.plot_token_update_on_cancel()
    
    def validate_plot_booking(self):
        if not self.plot_no:
            frappe.throw(_("Error: Plot number not specified in the Token document."))
        plot_status = frappe.db.get_value('Plot List', self.plot_no, 'status')
        if self.is_return == 1 :
            if plot_status != 'Token':
                frappe.throw(_('The {0} not in Token stage').format(frappe.get_desk_link('Plot List', self.plot_no)))

    def validate_token_amount(self):
        if flt(self.token_amount) == 0.0:
            frappe.throw(_('Token Amount does not equal to zero'))

    def validate_valid_till_date(self):
        if self.is_return == 0 :
            if self.valid_till_date  < self.posting_date:
                frappe.throw("Valid till date not back form Posting Date.")

    def validate_payment_plan_and_token_amount(self):
        if self.is_return == 0 :
            total_payment_type_amount = sum(row.amount for row in self.payment_type)
            if flt(total_payment_type_amount) != flt(self.token_amount):
                frappe.throw(_('Total Token Amount does not match the sum of Payment Paid amounts'))

        if self.is_return == 1 :
            total_payment_type_amount = sum(row.amount for row in self.payment_type)
            if flt(total_payment_type_amount) != flt(self.paid_to_customer):
                frappe.throw(_('Total Paid to Customer Amount does not match the sum of Payment type amount'))

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

        if self.is_return == 0:
            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "voucher_no": self.name,
                "posting_date": self.posting_date,
                "user_remark": self.remarks,
                "document_number": self.name,
                "document_type": "Plot Token",
                "project": self.project,
                "real_estate_inventory_no": self.plot_no
            })
            for payment in self.payment_type:        
                journal_entry.append("accounts", {
                    "account": payment.ledger, 
                    "debit_in_account_currency": payment.amount,
                    "against": default_receivable_account,
                    "project": self.project,
                    "real_estate_inventory_no": self.plot_no,
                    "bank_account":payment.bank_account,
                    "cost_center": "",
                    "is_advance": 0,
                    "document_number": self.name,
                    "document_type":"Plot Token",
                })
            journal_entry.append("accounts", {
                "account": default_receivable_account,
                "credit_in_account_currency": self.token_amount,
                "party_type": "Customer",
                "party": self.customer,
                "project": self.project,
                "real_estate_inventory_no": self.plot_no,
                "cost_center": "",
                "is_advance": 0,
                "document_number": self.name,
                "document_type": "Plot Token",
            })
        if self.is_return == 1:
            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "voucher_no": self.name,
                "posting_date": self.posting_date,
                "user_remark": self.remarks,
                "document_number": self.name,
                "document_type": "Plot Token",
                "project": self.project,
                "real_estate_inventory_no": self.plot_no
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
                    "document_type": "Plot Token",
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
                        "document_type":"Plot Token",
                    })
                journal_entry.append("accounts", {
                    "account": default_receivable_account,
                    "debit_in_account_currency": self.token_amount,
                    "party_type": "Customer",
                    "party": self.customer,
                    "project": self.project,
                    "real_estate_inventory_no": self.plot_no,
                    "cost_center": "",
                    "is_advance": 0,
                    "document_number": self.name,
                    "document_type": "Plot Token",
                    })
       
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()

        frappe.db.commit()
        frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Journal Entry", journal_entry.name)))
    
    def plot_token_update(self):
        if self.is_return == 0:
            plot_master = frappe.get_doc("Plot List", self.plot_no)    
            plot_master.update({
                            'customer'      : self.customer, 
                            'address'       : self.address,
                            'contact_no'    : self.contact_no, 
                            'sales_broker'  : self.sales_broker,
                            'father_name'   : self.father_name, 
                            'cnic'          : self.cnic,
                            'status'        : "Token", 
                            'document_type' : "Plot Token", 
                            'document_number': self.name,
                        })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated ').format(frappe.get_desk_link('Plot List', plot_master.name)))                    
        
        if self.is_return == 1:
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
                            'document_type'     : "",
                            'document_number'   : "",
                            'share_percentage'  : "",
                        })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot List', plot_master.name)))
        
        if self.is_return == 1:
            trans_doc = frappe.get_doc("Plot Token", self.return_token_number)
            trans_doc.update({'status' : "Return"})
            trans_doc.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Token", trans_doc.name)))
        
    def plot_token_update_on_cancel(self):
        if self.is_return == 0:
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
                            'document_type'     : "",
                            'document_number'   : "",
                            'share_percentage'  : "",
                        })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot List', plot_master.name)))

        if self.is_return == 1:
            plot_master = frappe.get_doc("Plot List", self.plot_no)    
            plot_master.update({
                            'customer'      : self.customer, 
                            'address'       : self.address,
                            'contact_no'    : self.contact_no, 
                            'sales_broker'  : self.sales_broker,
                            'father_name'   : self.father_name, 
                            'cnic'          : self.cnic,
                            'status'        : "Token", 
                            'document_type' : "Plot Token", 
                            'document_number': self.return_token_number,
                        })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated ').format(frappe.get_desk_link('Plot List', plot_master.name)))                    

        if self.is_return == 1:
            trans_doc = frappe.get_doc("Plot Token", self.return_token_number)
            trans_doc.update({'status' : "Active"})
            trans_doc.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Token", trans_doc.name)))

@frappe.whitelist()
def get_token_detail(return_token_number):
    doc = frappe.get_doc('Plot Token',{},  return_token_number)
    return doc.as_dict()