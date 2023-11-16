
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate
from realestate_account.controllers.real_estate_controller import validate_accounting_period_open

class CustomerPayment(Document):
    def validate(self):
        self.validate_check_duplicate_book_number()
        self.validate_row_paid_amount()
        self.validate_check_paid_amount_installment_amount()
        self.validate_posting_date()
        self.validate_check_total_amount()
        self.remove_unpaid_installments()
        self.check_parent_document_status()
        validate_accounting_period_open(self)

    def on_submit(self):
        self.make_gl_entries()
    
    def on_cancel(self):
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
            total_paid_amount = self.check_total_paid_amount(installment.base_doc_idx)
            if total_paid_amount is not None:
                previous_paid_amount = total_paid_amount + installment.paid_amount
                if previous_paid_amount > installment.installment_amount:
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

    def validate_check_paid_amount_installment_amount(self):
        if self.installment_total != self.payment_type_total_amount:
            frappe.throw('Installment Total and Payment Type Total Amount must be equal')
 
    def validate_check_total_amount(self):
        if not self.total_paid_amount:
            frappe.throw('Total paid amount should be set.')
        if self.total_paid_amount <= 0:
            frappe.throw('Total paid amount is less than or equal to zero')
    
    def validate_posting_date(self):
        if self.posting_date:
            posting_date = getdate(self.posting_date)
            today_date = today()
        if posting_date and posting_date > getdate(today_date):
            frappe.throw("Future document date not Allowed.")

    def Check_customer_plot_master_data(self):
        if self.customer:
            customer = frappe.get_value('Plot List', {'name': self.plot_no}, 'customer')
            if customer != self.customer:
                frappe.msgprint('The master data customer does not match the payment customer')
                frappe.throw('Validation Error: Customer mismatch')

    def check_parent_document_status(self):
        doc_type = self.document_type
        doc_number = self.document_number

        if doc_type in ['Plot Booking', 'Property Transfer']:
            doc_status = frappe.get_value(doc_type, {'name': doc_number}, 'status')
            if doc_status != 'Active':
                frappe.throw(f'The parent document {doc_type} with name {doc_number} is not Active')

    def remove_unpaid_installments(self):
        for i in reversed(range(len(self.installment))):
            installment = self.installment[i]
            if installment.paid_amount == 0:
                self.installment.pop(i)
        
    def make_gl_entries(self):
        if self.total_paid_amount > 0:
            default_company = frappe.defaults.get_user_default("Company")
            default_receivable_account = frappe.get_value("Company", default_company, "default_receivable_account")

            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "voucher_no": self.name,
                "posting_date": self.posting_date,  
                "user_remark": self.remarks,
                "custom_document_number": self.name,
                "custom_document_type": "Customer Payment",
                "custom_plot_no": self.plot_no,
            })

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
                    "custom_document_type": "Customer Payment"
                })

            journal_entry.append("accounts", {
                "account": default_receivable_account,
                "credit_in_account_currency": self.total_paid_amount,
                "party_type": "Customer",
                "party": self.customer,
                "project": self.project,
                "custom_plot_no": self.plot_no,
                "cost_center": "",
                "is_advance": 0,
                "custom_document_number": self.name,
                "custom_document_type": "Customer Payment"
            })
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()

            frappe.db.commit()
            frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Journal Entry", journal_entry.name)))


@frappe.whitelist()
def get_plot_detail(plot_no):
    try:
        sql_query = """
            SELECT 
                x.name, 
                x.plot_no, 
                x.project, 
                x.doc_type, 
                x.customer, 
                x.sales_amount, 
                x.DocDate, 
                x.sales_broker,
                x.address,
                IFNULL((SELECT  
                    SUM(tcp.total_paid_amount) 
                    FROM `tabCustomer Payment` tcp
                    where tcp.document_number = x.name and tcp.docstatus = 1), 0) +
                IFNULL((SELECT  
                    SUM(COALESCE(tpt.received_amount, 0)) 
                    FROM `tabProperty Transfer` tpt
                WHERE tpt.name = x.name AND docstatus = 1),0) as received_amount
                FROM (
                SELECT  
                    DISTINCT name, 
                    plot_no, 
                    project as project, 
                    'Plot Booking' as Doc_type, 
                    customer as customer, 
                    sales_broker, 
                    total_sales_amount as sales_amount, 
                    posting_date as DocDate,
                    address AS address
                FROM `tabPlot Booking`
                WHERE status = 'Active' AND docstatus = 1
                UNION ALL
                SELECT  
                    DISTINCT name, 
                    plot_no, 
                    project as project, 
                    'Property Transfer' as Doc_type, 
                    to_customer as customer, 
                    sales_broker, 
                    sales_amount as sales_amount,
                    posting_date as DocDate,
                    to_address AS address 
                FROM `tabProperty Transfer`
                WHERE status = 'Active' AND docstatus = 1) x               
                WHERE x.plot_no = %s
        """
        results = frappe.db.sql(sql_query, (plot_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.throw(f"Error in get_available_plots: {str(e)}")
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
                x.installment_amount,
                x.receivable_amount
            FROM (
                SELECT
                    c.name,
                    d.installment_name as Installment,
                    d.date,
                    d.remarks,
                    d.idx,
                    d.amount as installment_amount,
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
            ORDER BY x.idx
            limit 5;
        """
        results = frappe.db.sql(sql_query, (doc_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.throw(f"Error in get_available_plots: {str(e)}")
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
                x.name,
                x.installment_amount
            FROM (
                SELECT
                    c.name,
                    d.installment_name as Installment,
                    d.date,
                    d.remarks,
                    d.idx,
                    d.amount as installment_amount,
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
            ORDER BY x.idx
            limit 5;
        """
        results = frappe.db.sql(sql_query, (doc_no), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.throw(f"Error in get_available_plots: {str(e)}")
        return []
  

