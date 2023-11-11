import frappe
from frappe import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from frappe.model.document import Document
from frappe.utils import (
    flt, cstr, today
)



class PaymentPlanController(Document):
    @frappe.whitelist()
    def generate_installment(self):
        self.validate_payment_plan()
        payment_schedule = generate_payment_schedule(self.payment_plan)
        return payment_schedule

    def validate_payment_plan(self):
        if not self.payment_plan:
            frappe.throw(_('Please set payment plan'))

    def validate_payment_schedule(self):
        pass

    def validate_amount(self):
        if flt(self.difference) != 0.0:
            frappe.throw(_('Amount of Installment Total and Grand Total is not matched'))

def generate_payment_schedule(payment_plan):
    payment_schedule = []
    for plan in payment_plan:
        start_date = datetime.strptime(plan.get('start_date'), "%Y-%m-%d")
        if plan.get('is_recurring'):
            end_date = datetime.strptime(plan.get('end_date'), "%Y-%m-%d")
            current_date = start_date
            count = 1
            while current_date <= end_date:
                due_date = current_date

                payment_schedule.append({
                    "date": due_date.strftime("%Y-%m-%d"),
                    'amount': plan.get('installment_amount'),
                    'installment': plan.get('plan_type'),
                    "installment_amount": float(plan.get('installment_amount')),
                    'installment_name': '{0} {1}'.format(plan.get('plan_type'), count)
                })

                current_date += relativedelta(months=plan.get('frequency_in_months'))
                count += 1

        else:
            payment_schedule.append({
                "date": start_date.strftime("%Y-%m-%d"),
                'amount': plan.get('installment_amount'),
                'installment': plan.get('plan_type'),
                "installment_amount": float(plan.get('installment_amount')),
                'installment_name': plan.get('plan_type')
            })

    return payment_schedule
