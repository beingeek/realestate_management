# Copyright (c) 2024, CE Construction and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from realestate_account.controllers.real_estate_controller import RealEstateController, validate_accounting_period_open
from frappe.utils import flt

class PaymentPlanReschedule(RealEstateController):
    def validate(self):
        self.validate_posting_date()
        validate_accounting_period_open(self)
        self.validate_check_customer_master_data_transfer()
        self.validate_received_amount()
        self.validate_payment_plan_transfer_amount()
        self.validate_payment_schedule_transfer_amount()
        
    def on_submit(self):
        self.update_document()
        
    def on_cancel(self):
        self.update_document_cancel()

    def validate_payment_schedule_transfer_amount(self):
        total_payment_schedule_amount = sum(row.amount for row in self.payment_schedule)
        if flt(total_payment_schedule_amount) != flt(self.reshedule_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Schedule amounts'))

    def validate_payment_plan_transfer_amount(self):
        total_payment_plan_amount = sum(row.total_amount for row in self.payment_plan)
        if flt(total_payment_plan_amount) != flt(self.reshedule_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Plan amounts'))

    def validate_check_customer_master_data_transfer(self):
        if self.customer:
            customer = frappe.get_value('Plot List', {'name': self.plot_no}, 'customer')
            if customer != self.customer:
                frappe.throw('The master data customer does not match the payment customer')
                
    def validate_received_amount(self):
        if self.received_amount != 0 :
            total_payment = 0
            payment_amount = 0
            customer_payment = frappe.get_all('Customer Payment', 
                                              filters={'document_number': self.document_number ,
                                                       'docstatus':1}, 
                                              fields=['total_paid_amount'],)
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
        
    def update_document(self):              
            if self.document_type == "Plot Booking":
                booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                booking_doc.update({'payment_plan_reschedule' : self.name , 'ppr_active': 1 })
                booking_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Booking", booking_doc.name)))

            if self.document_type == "Property Transfer":
                trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                trans_doc.update({'payment_plan_reschedule' : self.name ,'ppr_active': 1 })
                trans_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer", trans_doc.name)))
                
    def update_document_cancel(self):              
            if self.document_type == "Plot Booking":
                booking_doc = frappe.get_doc("Plot Booking", self.document_number)
                booking_doc.update({'payment_plan_reschedule' : "", 'ppr_active': 0  })
                booking_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Booking", booking_doc.name)))

            if self.document_type == "Property Transfer":
                trans_doc = frappe.get_doc("Property Transfer", self.document_number)
                booking_doc.update({'payment_plan_reschedule' : "", 'ppr_active': 0 })
                trans_doc.save()
                frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Property Transfer", booking_doc.name)))

