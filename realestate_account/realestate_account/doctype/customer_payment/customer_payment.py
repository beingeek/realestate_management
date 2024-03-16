
import frappe
from frappe import _
from frappe.utils import flt , cstr
from realestate_account.controllers.real_estate_controller import RealEstateController, validate_accounting_period_open

class CustomerPayment(RealEstateController):
    def validate(self):
        self.validate_check_duplicate_book_number()
        self.validate_row_paid_amount()
        self.validate_check_paid_amount_installment_amount()
        self.validate_posting_date()
        self.validate_check_total_amount()
        self.remove_unpaid_installments()
        self.check_parent_document_status()
        self.Check_customer_plot_master_data()
        self.validate_payment_reschedule_status()
        validate_accounting_period_open(self)

    def on_submit(self):
        self.make_gl_entries()
    
    def before_cancel(self):
        self.check_parent_document_status()
       
    def validate_check_duplicate_book_number(self):
        if self.book_number and self.project:
            duplicate_payment = frappe.get_value(
                'Customer Payment',
                filters={
                    'book_number': self.book_number,
                    'project': self.project,
                    'name': ('!=', self.name),
                    'docstatus': ('!=', 2)
                },
                fieldname='name'
            )
            if duplicate_payment:
                frappe.throw(f'Duplicate book number found for the project. Another Customer Payment: {duplicate_payment}')

    def validate_row_paid_amount(self):
        for installment in self.installment:
            if self.ppr_active == 0:
                total_paid_amount = self.check_total_paid_amount(installment.base_doc_idx)
                if total_paid_amount is not None and total_paid_amount + installment.paid_amount > installment.installment_amount:
                    frappe.throw(f'Total paid amount cannot exceed the installment amount. Check row: {installment.idx}')
            else:
                total_amount = self.check_paid_amount_payment_reschedule(installment.ppr_child_table)
                if total_amount is not None and total_amount + installment.paid_amount > installment.installment_amount:
                    frappe.throw(f'Total paid amount cannot exceed the installment amount. Check row: {installment.idx}')


    def check_total_paid_amount(self, doc_child_idx):
        sql_query = """
            SELECT Sum(b.paid_amount) as total_paid_amount
                FROM `tabCustomer Payment` AS a
                INNER JOIN `tabCustomer Payment Installment` AS b
                ON a.name = b.parent
                WHERE a.docstatus = 1
                AND a.document_number = %s 
                AND b.base_doc_idx = %s
        """
        result = frappe.db.sql(sql_query, (self.document_number, doc_child_idx), as_dict=True)
        return result[0]['total_paid_amount'] if result else 0

    def check_paid_amount_payment_reschedule(self, doc_child_idx):
        sql_query = """
            SELECT Sum(b.paid_amount) as total_paid_amount
                FROM `tabCustomer Payment` AS a
                INNER JOIN `tabCustomer Payment Installment` AS b
                ON a.name = b.parent
                WHERE a.docstatus = 1
                AND a.payment_plan_reschedule = %s 
                AND b.ppr_child_table = %s
        """
        result = frappe.db.sql(sql_query, (self.document_number, doc_child_idx), as_dict=True)
        return result[0]['total_paid_amount'] if result else 0


    def validate_check_paid_amount_installment_amount(self):
        if self.installment_total != self.payment_type_total_amount:
            frappe.throw('Installment Total and Payment Type Total Amount must be equal')
 
    def validate_check_total_amount(self):
        if not self.total_paid_amount:
            frappe.throw('Total paid amount should be set.')
        if flt(self.total_paid_amount) <= 0.0:
            frappe.throw('Total paid amount is less than or equal to zero')
    
    def check_parent_document_status(self):
        doc_type = self.document_type
        doc_number = self.document_number

        if doc_type in ['Plot Booking', 'Property Transfer']:
            doc_status = frappe.get_value(doc_type, {'name': doc_number}, 'status')
            if doc_status != 'Active':
                frappe.throw(f'The parent document {doc_type} with name {doc_number} is not Active')
        if doc_type == 'Property Merge':
            doc_status = frappe.get_value(doc_type, {'name': doc_number}, 'docstatus')
            if doc_status == 1 :
                frappe.throw(f'The parent document {doc_type} with name {doc_number} is Active, Cancel the parent document first')


    def validate_payment_reschedule_status(self):
        if self.ppr_active == 1:
            pmt_reschedule = frappe.get_value("Payment Plan Reschedule", self.payment_plan_reschedule, "docstatus")
            if pmt_reschedule != 1:
                frappe.throw(_('The Payment schedule {0} is Cancelled').format(frappe.get_desk_link("Payment Plan Reschedule", self.payment_plan_reschedule.name)))

    def remove_unpaid_installments(self):
        for i in reversed(range(len(self.installment))):
            installment = self.installment[i]
            if installment.paid_amount == 0:
                self.installment.pop(i)
        
    def make_gl_entries(self):
        if flt(self.total_paid_amount) > 0.0:
            company = frappe.get_doc("Company", self.company)
            default_receivable_account = frappe.get_value("Company", company, "default_receivable_account")

            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "voucher_no": self.name,
                "posting_date": self.posting_date,  
                "user_remark": self.remarks,
                "document_number": self.name,
                "document_type": "Customer Payment",
                "real_estate_inventory_no": self.plot_no,
            })

            for payment in self.payment_type:
                journal_entry.append("accounts", {
                    "account": payment.ledger,
                    "debit_in_account_currency": payment.amount,
                    "against": default_receivable_account,
                    "project": self.project,
                    "real_estate_inventory_no": self.plot_no,
                    "cost_center": "",
                    "is_advance": 0,
                    "document_number": self.name,
                    "document_type": "Customer Payment"
                })

            journal_entry.append("accounts", {
                "account": default_receivable_account,
                "credit_in_account_currency": self.total_paid_amount,
                "party_type": "Customer",
                "party": self.customer,
                "project": self.project,
                "real_estate_inventory_no": self.plot_no,
                "cost_center": "",
                "is_advance": 0,
                "document_number": self.name,
                "document_type": "Customer Payment"
            })
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()
            frappe.db.commit()
            frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Journal Entry", journal_entry.name)))

  

