
import frappe
from frappe import _
from realestate_account.controllers.real_estate_controller import PaymentScheduleController
from frappe.utils import flt, cstr, today, getdate


class ClosedAccountingPeriod(frappe.ValidationError):
	pass

class PropertyTransfer(PaymentScheduleController):
    def validate(self):
        self.validate_posting_date()
        validate_accounting_period_open(self)
        self.validate_from_customer_and_to_customer()
        self.validate_posting_date()
        self.validate_Check_customer_plot_master_data()
        self.validate_received_amount()
        self.validate_transfer_amount()

    def on_submit(self):
        self.make_gl_entries()
        self.update_plot_master()
        
    def on_cancel(self):
        self.update_plot_master_cancel()

    def validate_from_customer_and_to_customer(self):
        if self.from_customer == self.to_customer:
            frappe.throw('From Customer and To Customer must be different')

    
    def validate_Check_customer_plot_master_data(self):
        if self.from_customer:
            customer = frappe.get_value('Plot List', {'name': self.plot_no}, 'customer')
            if customer != self.from_customer:
                frappe.msgprint('The master data customer does not match the payment customer')
                frappe.throw('Validation Error: Customer mismatch')

    def validate_received_amount(self):
        if self.received_amount != 0 :
            total_payment = 0
            payment_amount = 0
            customer_payment = frappe.get_all('Customer Payment', filters={'document_number': self.document_number}, fields=['total_paid_amount'],)
            for payment in customer_payment:
                payment_amount += payment.total_paid_amount
            
            if self.document_type == "Plot Booking":
                if payment_amount != self.received_amount:
                    frappe.throw(f'Customer payment total {payment_amount} & total in received field {self.received_amount} Refresh the document')
        
            elif self.document_type == "Property Transfer":            
                paid_amount = frappe.get_value("Property Transfer", {'name': self.document_number}, 'received_amount')
                total_payment = payment_amount+paid_amount
                if  total_payment != self.received_amount:
                    frappe.throw(f'Customer payment total {total_payment}  & total in received field {self.received_amount} Refresh the document')

    def validate_transfer_amount(self):
        if self.transfer_charge != 0:
            total_payment_amount = 0
            for payment in self.payment_type:
                total_payment_amount += payment.amount
            if self.transfer_charge != total_payment_amount:
                frappe.throw('Total transfer charge must be equal to the sum of payment type amounts') 

    def make_gl_entries(self):
            if self.received_amount != 0 or self.transfer_charge != 0:

                company = frappe.defaults.get_user_default("Company")
                default_receivable_account = frappe.get_value("Company", company, "default_receivable_account")
                
                transfer_account = frappe.db.get_single_value("Real Estate Settings", "default_transfer_revenue_account")
                if not transfer_account:
                    frappe.throw('Please set Default Transfer Revenue Account in Real Estate Settings')
                cost_center = frappe.db.get_single_value("Real Estate Settings", "cost_center")
                if not cost_center:
                    frappe.throw('Please set Cost Centre in Real Estate Settings')

                journal_entry = frappe.get_doc({
                    "doctype": "Journal Entry",
                    "voucher_type": "Journal Entry",
                    "voucher_no": self.name,
                    "posting_date": self.posting_date,
                    "user_remark": self.remarks,
                    "custom_document_number": self.name,
                    "custom_document_type": "Property Transfer",
                    "custom_plot_no": self.plot_no
                })
                if self.received_amount > 0:
                    journal_entry.append("accounts", {
                        "account": default_receivable_account,
                        "debit_in_account_currency": self.received_amount,
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
                        "credit_in_account_currency": self.received_amount,
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
                frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Journal Entry", journal_entry.name)))
        
    def update_plot_master(self):
            plot_master = frappe.get_doc("Plot List", self.plot_no)    
            plot_master.update({
                        'customer': self.to_customer, 'address': self.to_address,
                        'contact_no': self.to_contact_no, 'sales_broker': self.sales_broker,
                        'father_name': self.to_father_name, 'cnic': self.to_cnic,
                    })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated ').format(frappe.get_desk_link('Plot List', plot_master.name)))                    
            if self.document_type == "Plot Booking":
                booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                booking_doc.update({'status' : "Property Transfer"})
                booking_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot Booking ', booking_doc.name)))
            if self.document_type == "Property Transfer":
                trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                trans_doc.update({'status' : "Further Transferred"})
                trans_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer", trans_doc.name)))
                
    def update_plot_master_cancel(self):
        try:    
            plot_master = frappe.get_doc("Plot List", self.plot_no)
            plot_master.update({
                                'customer': self.from_customer, 'address': self.from_address,
                                'contact_no': self.from_contact_no, 'sales_broker': self.from_sales_broker,
                                'father_name': self.from_father_name, 'cnic': self.from_cnic,
                            })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot List', plot_master.name)))                    
            if self.document_type == "Plot Booking":
                    booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                    booking_doc.update({'status' : "Active"})
                    booking_doc.save()
                    frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot Booking ', booking_doc.name)))
            if self.document_type == "Property Transfer":
                    trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                    trans_doc.update({'status' : "Active"})
                    trans_doc.save()
                    frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer", booking_doc.name)))
        except Exception as e:
            frappe.msgprint(f"Error while making update plot master: {str(e)}")
   
    def before_insert(self):
        if self.status != "Active":
            frappe.throw('The document status should be Active at the time entered in the system')


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


################ Get Plot & Base document data for Property Transfer ############

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
                thb.status = 'Active' AND thb.docstatus = 1 )
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
            ORDER BY x.idx
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
                d.date idx
        ) x
        WHERE 
            x.receivable_amount <> 0
        ORDER BY x.idx
        limit 5;
        """
        data = frappe.db.sql(sql_query, (doc_no), as_dict=True)
        return data
