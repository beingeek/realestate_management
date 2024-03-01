
import frappe
from frappe import _
from frappe.utils import flt , cstr
from realestate_account.controllers.real_estate_controller import RealEstateController, validate_accounting_period_open

class PropertyMerge(RealEstateController):
    def validate(self):
        self.validate_row_paid_amount()
        self.validate_posting_date()
        self.remove_unpaid_installments()
        self.validate_project_plot_no()
        self.check_parent_document_status()
        self.validate_net_amount_merge_installment_total()
        validate_accounting_period_open(self)

    def on_submit(self):
        self.make_gl_entries()
        self.make_customer_payment()
        self.update_customer_payment()
        self.update_plot_master_on_submit()
    
    def on_cancel(self):
        self.check_parent_document_status()
        self.update_customer_payment_cancel()
        
    def validate_net_amount_merge_installment_total(self):
        if self.net_amount_merge != self.installment_total:
            frappe.throw('Net Merge Amount is must be equal to Installment Total')
            
    def validate_project_plot_no(self):
        if (self.merge_plot_no == self.plot_no) and (self.project == self.merge_project):
            frappe.throw('Project & Plot no. is different from Merge Project & Plot No.')
            
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
        if flt(self.merge_amount) > 0.0:
            company = frappe.get_doc("Company", self.company)
            default_bank_account = frappe.get_value("Company", company, "default_bank_account")
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
				"document_number": self.name,
				"document_type": "Property Merge",
				"real_estate_inventory_no": self.merge_plot_no,
			})
            
            journal_entry.append("accounts", {
				"account": default_receivable_account,
				"debit_in_account_currency": self.merge_amount,
				"party_type": "Customer",
				"party": self.customer,
				"project": self.merge_project,
				"real_estate_inventory_no": self.merge_plot_no,
				"cost_center": "",
				"is_advance": 0,
				"document_number": self.name,
				"document_type": "Property Merge",
			})
            
            if flt(self.deduction) != 0.0:
                journal_entry.append("accounts", {
					"account": deductionAccount,
					"credit_in_account_currency": self.deduction,
					"against": self.customer,
					"project": self.merge_project,
					"real_estate_inventory_no": self.merge_plot_no,
					"cost_center": cost_center,
					"is_advance": 0,
					"document_number": self.name,
					"document_type": "Property Merge"
				})
                
            if flt(self.net_amount_merge) != 0.0:
                journal_entry.append("accounts", {
					"account": default_bank_account,
					"credit_in_account_currency": self.net_amount_merge,
					"against": self.customer,
					"project": self.merge_project,
					"real_estate_inventory_no": self.merge_plot_no,
					"cost_center": "",
					"is_advance": 0,
					"document_number": self.name,
					"document_type": "Property Merge",
				})
                
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()
            frappe.db.commit()
            frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Journal Entry", journal_entry.name)))
            
    def update_plot_master_on_submit(self):
        try:
            plot_master = frappe.get_doc("Plot List", self.merge_plot_no)
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

    def update_plot_master_on_cancel(self):
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

    def update_document_on_submit(self):
        try:
            if self.document_type == "Plot Booking":
                booking_doc = frappe.get_doc("Plot Booking", self.merge_document_number)
                booking_doc.update({'status' : "Cancel"})
                booking_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Booking", booking_doc.name)))

            if self.document_type == "Property Transfer":
                trans_doc = frappe.get_doc("Property Transfer", self.merge_document_number)
                trans_doc.update({'status' : "Cancel"})
                trans_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer", trans_doc.name)))
        except Exception as e:
            frappe.msgprint(f"Error while updating document master Data: {str(e)}")    

    def remove_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        if plot_master.status == "Available":
            
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
            
    def make_customer_payment(self):
        if flt(self.merge_amount) > 0.0:
            company = frappe.get_doc("Company", self.company)
            default_bank_account = frappe.get_value("Company", company, "default_bank_account")
                
            cust_pmt = frappe.get_doc({
				"doctype": "Customer Payment",
				"posting_date": self.posting_date,
                "project":self.project,
                "plot_no":self.plot_no,
				"user_remark": self.remarks,
				"document_number": self.document_number,
				"document_type": self.document_type,
				"total_paid_amount":self.net_amount_merge,
                "book_number": self.name,
                "customer":self.from_customer,
                "sales_amount": self.sales_amount,
                "received_amount":self.received_amount,
                "remaining_amount":self.balance_amount,
                "company":self.company,
                "payment_type_total_amount":self.net_amount_merge,
                "installment_total":self.net_amount_merge,
                "property_merge":self.name,
			})
            for install in self.installment:
                cust_pmt.append("installment", {
                    "date":install.date,
                	"installment": install.installment,
					"installment_amount":install.installment_amount,
                    "paid_amount":install.paid_amount,
					"receivable_amount":install.receivable_amount,
                    "remaining_amount":install.remaining_amount,
                    "ppr_document_number":install.ppr_document_number,
                    "base_doc_idx":install.base_doc_idx,
                    "ppr_child_table":install.ppr_child_table,
			})

            cust_pmt.append("payment_type", {
                "payment_type": "Cash",
                "ledger": default_bank_account,
				"amount":self.net_amount_merge,
			})
   
            cust_pmt.insert(ignore_permissions=True)
            cust_pmt.submit()
            frappe.db.commit()
            frappe.msgprint(_('Journal Entry {0} created successfully').format(frappe.get_desk_link("Customer Payment", cust_pmt.name)))
            
    def update_customer_payment(self):
        cust = frappe.get_all("Customer Payment", filters={"document_number": self.merge_document_number,
                                                           "docstatus": 1})
        for payment in cust:
            payment_doc = frappe.get_doc("Customer Payment", payment.name)
            payment_doc.update({
            "property_merge" : self.name })
            payment_doc.save()
        frappe.msgprint(_('Merge Document Number successfully updated in Customer Payments'))
        
    def update_customer_payment_cancel(self):
        cust = frappe.get_all("Customer Payment", filters={"document_number": self.merge_document_number ,
                                                           "docstatus": 1})
        for payment in cust:
            payment_doc = frappe.get_doc("Customer Payment", payment.name)
            payment_doc.update({
            "property_merge" : "" })
            payment_doc.save()
        frappe.msgprint(_('Merge Document Number successfully removed from Customer Payments'))