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
        sql_query = """

        SELECT y.plan_type, y.start_date, y.end_date, y.installment_amount,
        y.frequency_in_months, y.is_recurring, y.date_selection, x.name, y.idx
        from `tabPayment Plan Template` x 
        INNER JOIN `tabPayment Plan` y on x.name  = y.parent 
        Where x.name = %s 
        and x.company = %s
        Order by y.idx 
        """
        results = frappe.db.sql(sql_query, (plan_template, company), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.throw(f"Error in get_available_plots: {str(e)}")
        return []

@frappe.whitelist()
def get_previous_document_detail(plot_no):
    try:
        sql_query = """
        WITH plot_detail AS (
            SELECT DISTINCT
                tpt.name,
                tpt.plot_no,
                tpt.project,
                tpt.to_share_percentage as share_percentage,
                tpt.to_customer_type as customer_type,
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
                thb.project,
                thb.share_percentage,
                thb.customer_type,
                'Plot Booking' as Doc_type,
                thb.customer,
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

@frappe.whitelist()
def get_customer_partner(document_number):
    try:
        sql_query = """
        WITH customer_partnership AS (
            SELECT DISTINCT
                tpt.name,
                tpt.plot_no,
                tcp.customer, tcp.share_percentage, tcp.father_name, 
                tcp.id_card_no, tcp.mobile_no, tcp.address
            FROM
                `tabProperty Transfer` tpt
            INNER JOIN 
                `tabCustomer Partnership` tcp on tcp.parent = tpt.name
            WHERE
                tpt.status = 'Active' AND tpt.docstatus = 1
            UNION ALL
            SELECT DISTINCT
                thb.name,
                thb.plot_no,
                tcp.customer, tcp.share_percentage, tcp.father_name, 
                tcp.id_card_no, tcp.mobile_no, tcp.address
            FROM
                `tabPlot Booking` thb
            INNER JOIN 
                `tabCustomer Partnership` tcp on tcp.parent = thb.name
            WHERE
                thb.status = 'Active' AND thb.docstatus = 1)
        SELECT * FROM customer_partnership WHERE name = %s;
        """
        results = frappe.db.sql(sql_query, (document_number), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.throw(f"Error in getting customer_partnership: {str(e)}")
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
