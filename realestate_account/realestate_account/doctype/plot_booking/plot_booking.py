import frappe
from frappe import _
from realestate_account.controllers.payment_plan_controller import PaymentPlanController
from frappe.utils import flt, cstr, today


class ClosedAccountingPeriod(frappe.ValidationError):
    pass

class PlotBooking(PaymentPlanController):
    def validate(self):
        self.validate_booking_date()
        validate_accounting_period_open(self)
        self.validate_plot_booking()
        self.validate_amount()

    def on_submit(self):
        self.create_invoice()
        self.book_plot()

    def on_cancel(self):
        self.unbook_plot()

    def validate_plot_booking(self):
        if not self.plot_no:
            frappe.throw(_("Error: Plot number not specified in the Plot Booking document."))

        plot_status = frappe.db.get_value('Plot List', self.plot_no, 'status')
        if plot_status == 'Booked':
            frappe.throw(_('The {0} is already booked').format(frappe.get_desk_link('Plot List', self.plot_no)))

    def validate_booking_date(self):
        if self.booking_date > today():
            frappe.throw(_('Future booking date not allowed.'))

    def create_invoice(self):
        if flt(self.commission_amount) > 0.0:
            company = frappe.get_doc("Company", self.company)
            company_default_cost_center = frappe.db.get_value("Company", self.company, 'cost_center')
            realestate_default_cost_center = frappe.db.get_single_value("Real Estate Settings", "cost_center")
            default_cost_center = realestate_default_cost_center or company_default_cost_center
            default_commission_item = frappe.db.get_single_value("Real Estate Settings", "commission_item")
            if not default_commission_item:
                frappe.throw('Please set Commission Item in Real Estate Settings')

            invoice = frappe.get_doc({
                "doctype": "Purchase Invoice",
                "supplier": self.sales_broker,
                "booking_date": self.booking_date,
                "bill_no" : self.plot_no,
                "project" : self.project,
                "cost_centre" : "",
                "custom_booking_number":self.name,
                "company" : company
            })

            invoice.append("items", {
                        "item_code": default_commission_item, "qty": 1,
                        "rate": self.commission_amount,
                        "project" : self.project,
                        "cost_centre" : default_cost_center
                    })

            invoice.insert(ignore_permissions=True)
            invoice.submit()
            frappe.msgprint(_('{0} Broker commission created').format(frappe.get_desk_link('Purchase Invoice', invoice.name)))

    def book_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        if plot_master.status == "Available" and plot_master.hold_for_sale == 0:
            plot_master.update({
                'status': "Booked", 'customer': self.customer, 'address': self.address,
                'contact_no': self.contact_no, 'sales_broker': self.sales_broker,
                'father_name': self.father_name, 'cnic': self.cnic,
            })
            plot_master.save()
            frappe.msgprint(_('{0} booked successfully').format(frappe.get_desk_link('Plot List', plot_master.name)))
        else:
            frappe.throw(_("Error: The selected plot is not available for booking."))

    def unbook_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        plot_master.update({
            'status': "Available", 'customer': '', 'address': '',
            'contact_no': '', 'sales_broker': '',
            'father_name': '',  'cnic': ''
        })

        plot_master.save()
        frappe.msgprint(_('{0} unbooked').format(frappe.get_desk_link('Plot List', plot_master.name)))

    def before_insert(self):
        if self.status != 'Active':
            frappe.throw(_('The booking status should be Active'))


def validate_accounting_period_open(doc, method=None):
    # refactor this to sql to make it backward compatible 
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
            & (doc.booking_date >= ap.start_date)
            & (doc.booking_date <= ap.end_date)
        )
    ).run(as_dict=1)

    if accounting_period:
        frappe.throw(_("You cannot create a {0} within the closed Accounting Period {1}").format(
            doc.doctype, frappe.bold(accounting_period[0]["name"]),
            ClosedAccountingPeriod
        ))
