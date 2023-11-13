# Copyright (c) 2023, CE Construction and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PaymentPlanType(Document):
    def validate(self):
        self.validate_is_recurring()
        
    def validate_is_recurring(self):
        if self.is_recurring and self.frequency_in_months == 0:
            frappe.throw('In recurring plans, the frequency in months cannot be zero')
