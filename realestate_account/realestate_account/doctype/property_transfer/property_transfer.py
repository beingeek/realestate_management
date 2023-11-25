
import frappe
from frappe import _
from realestate_account.controllers.real_estate_controller import RealEstateController, validate_accounting_period_open
from frappe.utils import flt

class PropertyTransfer(RealEstateController):
    def validate(self):
        self.validate_posting_date()
        validate_accounting_period_open(self)
        self.validate_from_customer_and_to_customer()
        self.validate_check_customer_master_data_transfer()
        self.validate_received_amount()
        self.validate_transfer_amount()
        self.validate_payment_plan_transfer_amount()
        self.validate_payment_schedule_transfer_amount()
        self.validate_duplicates_customer_in_partnership()
        self.validate_share_percentage()
        
    def on_submit(self):
        self.make_gl_entries()
        self.update_plot_master()
        
    def on_cancel(self):
        self.update_plot_master_cancel()

    def validate_from_customer_and_to_customer(self):
        to_customer = [row.customer for row in self.to_customer_partnership]
        from_customer = {row.customer for row in self.from_customer_partnership}
        if self.from_customer == self.to_customer:
            frappe.throw('From Customer and To Customer must be different')
        if self.from_customer in to_customer:
            frappe.throw(_('From Customer and To Customer must be different'))
        for row in self.to_customer_partnership:
            if row.customer in from_customer:
                frappe.throw(_("Duplicate customer found in from customer and to Customer: {0}").format(row.customer))

    def validate_payment_schedule_transfer_amount(self):
        total_payment_schedule_amount = sum(row.amount for row in self.payment_schedule)
        if flt(total_payment_schedule_amount) != flt(self.total_transfer_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Schedule amounts'))

    def validate_payment_plan_transfer_amount(self):
        total_payment_plan_amount = sum(row.total_amount for row in self.payment_plan)
        if flt(total_payment_plan_amount) != flt(self.total_transfer_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Plan amounts'))

    def validate_check_customer_master_data_transfer(self):
        if self.from_customer:
            customer = frappe.get_value('Plot List', {'name': self.plot_no}, 'customer')
            if customer != self.from_customer:
                frappe.throw('The master data customer does not match the payment customer')
                
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

    def validate_share_percentage(self):
        if self.to_customer_type == "Individual":
            if flt(self.to_share_percentage) != 100.0:
                frappe.throw(_('The Individual customer share percentage must be equal to 100. Current total: {0:.2f}').format(self.to_share_percentage))
            rows = len([row.customer for row in self.to_customer_partnership])
            if rows > 0:
                frappe.throw(_('Remove the rows in the customer partnership table.'))
        
        elif self.to_customer_type == "Partnership":
            share_percentage = flt(self.to_share_percentage) + flt(sum(row.share_percentage for row in self.to_customer_partnership))
            
            if flt(share_percentage) != 100.0:
                frappe.throw(_('The Partnership customers share percentage must be equal to 100. Current total: {0:.2f}').format(share_percentage))
            if any(row.share_percentage == 0.0 for row in self.to_customer_partnership):
                frappe.throw(_('Share percentage for Partnership customers cannot be 0.0'))
            if flt(self.to_share_percentage) == 0.0:
                frappe.throw(_('Share percentage for Main customers cannot be 0.0'))

    def validate_duplicates_customer_in_partnership(self):
        partnership_customer = [row.customer for row in self.to_customer_partnership]
        duplicates_in_partnership = [x for x in partnership_customer if partnership_customer.count(x) > 1]
        
        if duplicates_in_partnership:
            duplicate_customers = ', '.join(set(duplicates_in_partnership))
            frappe.throw(_('Duplicate customers found in the to customer partnership table: {0}').format(duplicate_customers))
        
        if self.to_customer and self.to_customer in partnership_customer:
            frappe.throw(_('Duplicate customer found in the to customer partnership table: {0}').format(self.to_customer))

    def make_gl_entries(self):
            if self.received_amount != 0 or self.transfer_charge != 0:
                company = frappe.get_doc("Company", self.company)
                default_receivable_account = frappe.get_value("Company", company, "default_receivable_account")
                transfer_account = frappe.get_value("Company", self.company, "default_transfer_revenue_account")
               
                if not default_receivable_account:
                    frappe.throw('Please set Default Receivable Account in Company Settings')
                if not transfer_account:
                    frappe.throw('Please set Default Transfer Revenue Account in Company Settings')
                cost_center = frappe.get_value("Company", self.company, "real_estate_cost_center")
                if not cost_center:
                    frappe.throw('Please set Cost Centre in Company Settings')

                journal_entry = frappe.get_doc({
                    "doctype": "Journal Entry",
                    "voucher_type": "Journal Entry",
                    "voucher_no": self.name,
                    "posting_date": self.posting_date,
                    "user_remark": self.remarks,
                    "document_number": self.name,
                    "document_type": "Property Transfer",
                    "real_estate_inventory_no": self.plot_no
                })
                if self.received_amount > 0:
                    journal_entry.append("accounts", {
                        "account": default_receivable_account,
                        "debit_in_account_currency": self.received_amount,
                        "party_type": "Customer",
                        "party": self.from_customer,
                        "against": self.to_customer,
                        "project": self.project,
                        "real_estate_inventory_no": self.plot_no,
                        "cost_center": "",
                        "is_advance": 0,
                        "document_number": self.name,
                        "document_type": "Property Transfer"
                    })
                    journal_entry.append("accounts", {
                        "account": default_receivable_account,
                        "credit_in_account_currency": self.received_amount,
                        "party_type": "Customer",
                        "party": self.to_customer,
                        "against": self.from_customer,
                        "project": self.project,
                        "real_estate_inventory_no": self.plot_no,
                        "cost_center": "",
                        "is_advance": 0,
                        "document_number": self.name,
                        "document_type": "Property Transfer"
                    })
                if self.transfer_charge > 0:
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
                            "document_type": "Property Transfer"
                        })
                    journal_entry.append("accounts", {
                        "account": transfer_account,
                        "credit_in_account_currency": self.transfer_charge,
                        "against": self.from_customer,
                        "project": self.project,
                        "real_estate_inventory_no": self.plot_no,
                        "cost_center": cost_center,
                        "is_advance": 0,
                        "document_number": self.name,
                        "document_type": "Property Transfer"
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
                        'customer_type': self.to_customer_type,'share_percentage': self.to_share_percentage,
                    })
        
            if self.to_customer_type == "Individual":
                plot_master.set("customer_partnership", [])
            
            elif self.to_customer_type == "Partnership":
                for customer in self.to_customer_partnership:
                    plot_master.append("customer_partnership", {
                    'customer': customer.customer,
                    'address': customer.address,
                    'mobile_no': customer.mobile_no,
                    'father_name': customer.father_name,
                    'id_card_no': customer.id_card_no,
                    'share_percentage': customer.share_percentage,
            })
            plot_master.save()
            frappe.msgprint(_('{0} successfully updated ').format(frappe.get_desk_link('Plot List', plot_master.name)))                    
            if self.document_type == "Plot Booking":
                booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                booking_doc.update({'status' : "Property Transfer"})
                booking_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Booking", booking_doc.name)))
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
                                 'customer_type': self.from_customer_type,'share_percentage': self.from_share_percentage,
                            })
            
            if self.from_customer_type == "Individual":
                plot_master.set("customer_partnership", [])

            elif self.from_customer_type == "Partnership":
                for customer in self.from_customer_partnership:
                    plot_master.append("customer_partnership", {
                    'customer': customer.customer,
                    'address': customer.address,
                    'mobile_no': customer.mobile_no,
                    'father_name': customer.father_name,
                    'id_card_no': customer.id_card_no,
                    'share_percentage': customer.share_percentage,
            })

            plot_master.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link('Plot List', plot_master.name)))                    
            if self.document_type == "Plot Booking":
                    booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                    booking_doc.update({'status' : "Active"})
                    booking_doc.save()
                    frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Booking", booking_doc.name)))
            if self.document_type == "Property Transfer":
                    trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                    trans_doc.update({'status' : "Active"})
                    trans_doc.save()
                    frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer", booking_doc.name)))
        except Exception as e:
            frappe.msgprint(f"Error while making update plot master: {str(e)}")


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
                            AND a.a.document_number = c.name
                            AND b.base_doc_idx = d.idx
                            AND a.real_estate_inventory_no = c.plot_no
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
                            AND a.document_number = c.name
                            AND b.base_doc_idx = d.idx
                            AND a.real_estate_inventory_no = c.plot_no
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
