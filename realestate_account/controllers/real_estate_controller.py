import frappe
from frappe import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

class ClosedAccountingPeriod(frappe.ValidationError):
    pass

class RealEstateController(Document):
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

    def validate_posting_date(self):
        if self.posting_date:
            posting_date = getdate(self.posting_date)
            today_date = today()
        if posting_date and posting_date > getdate(today_date):
            frappe.throw("Future Document date not Allowed.")

    def validate_amount(self):
        if flt(self.difference) != 0.0:
            frappe.throw(_('Amount of Total Payment Schedule and Total Sales Amout is not matched'))

    def Check_customer_plot_master_data(self):
        if self.customer:
            customer = frappe.get_value('Plot List', {'name': self.plot_no}, 'customer')
            if customer != self.customer:
                frappe.msgprint('The master data customer does not match the payment customer')
                frappe.throw('Validation Error: Customer mismatch')

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
def get_payment_plan(plan_template, company):

    if not plan_template or not company:
        frappe.throw(_("'Payment plan template' and 'company' are required to get payment plan."))
    try:
        results = frappe.get_all(
            'Payment Plan',
            filters={'parent': plan_template, 'company': company},
            fields=['*'],
            order_by='idx',
            join={
                'table': 'tabPayment Plan Template',
                'condition': 'tabPayment Plan Template.name = tabPayment Plan.parent'
            }
        )
        return results
    except Exception as e:
        frappe.throw(f"'Payment Plan not found': {str(e)}")
        return []
    
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
