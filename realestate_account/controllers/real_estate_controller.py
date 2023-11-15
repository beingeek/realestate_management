import frappe
from frappe import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from frappe.model.document import Document
from frappe.utils import flt, cstr , getdate, today


class PaymentScheduleController(Document):
    @frappe.whitelist()
    def generate_installment(self):
        self.validate_payment_plan()
        payment_schedule = generate_payment_schedule(self.payment_plan)
        return payment_schedule

    def validate_payment_plan(self):
        if not self.payment_plan:
            frappe.throw(_('Please set payment plan'))
        for plan in self.payment_plan:
            if not plan.get('plan_type'):
                frappe.throw(_('Plan type is required for each installment'))
            if not plan.get('start_date'):
                frappe.throw(_('Start date is required for each installment'))
            if not plan.get('end_date'):
                frappe.throw(_('End date is required for each installment'))
            if not plan.get('installment_amount') or flt(plan.get('installment_amount')) <= 0:
                frappe.throw(_('Valid installment amount is required for each installment'))

    def validate_payment_schedule(self):
        pass
    
    def validate_posting_date(self):
        if self.posting_date:
            posting_date = getdate(self.posting_date)
            today_date = today()
        if posting_date and posting_date > getdate(today_date):
            frappe.throw("Future Document date not Allowed.")

    def validate_amount(self):
        if flt(self.difference) != 0.0:
            frappe.throw(_('Amount of Total Payment Schedule and Total Sales Amout is not matched'))

def generate_payment_schedule(payment_plan):
    payment_schedule = []
    for plan in payment_plan:
        start_date = datetime.strptime(plan.get('start_date'), "%Y-%m-%d")
        if plan.get('is_recurring'):
            end_date = datetime.strptime(plan.get('end_date'), "%Y-%m-%d")
            current_date = start_date
            count = 0
            current_date += relativedelta(months=plan.get('frequency_in_months'))
            count += 1
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
            if plan.get('date_selection') == 'Start Date':
                installment_date = datetime.strptime(plan.get('start_date'), "%Y-%m-%d")
            else:
                installment_date = datetime.strptime(plan.get('end_date'), "%Y-%m-%d")
            payment_schedule.append({
                "date": installment_date.strftime("%Y-%m-%d"),
                'amount': plan.get('installment_amount'),
                'installment': plan.get('plan_type'),
                "installment_amount": float(plan.get('installment_amount')),
                'installment_name': plan.get('plan_type')
            })
    return payment_schedule


@frappe.whitelist()
def get_payment_plan(plan_template):
    try:
        results = frappe.get_all(
            'Payment Plan Template - Child',
            filters={'parent': plan_template},
            fields=['*'],
            order_by='idx'
        )
        return results
    except Exception as e:
        frappe.throw(f"'Payment Plan not found': {str(e)}")
        return []


