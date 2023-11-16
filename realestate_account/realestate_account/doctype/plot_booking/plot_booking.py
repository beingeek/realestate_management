import frappe
from frappe import _
from realestate_account.controllers.real_estate_controller import PaymentScheduleController, validate_accounting_period_open
from frappe.utils import flt, cstr, today


class ClosedAccountingPeriod(frappe.ValidationError):
    pass

class PlotBooking(PaymentScheduleController):
    def validate(self):
        self.validate_posting_date()
        validate_accounting_period_open(self)
        self.validate_plot_booking()
        self.validate_amount()
        self.validate_Payment_schedule_Sales_Amount()
        self.validate_Payment_Plan_Sales_Amount()

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

    # def validate_posting_date(self):
    #     if self.posting_date > today():
    #         frappe.throw(_('Future booking date not allowed.'))


    def validate_Payment_schedule_Sales_Amount(self):
        total_payment_schedule_amount = sum(row.amount for row in self.payment_schedule)
        if flt(total_payment_schedule_amount) != flt(self.total_sales_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Schedule amounts'))

    def validate_Payment_Plan_Sales_Amount(self):
        total_payment_plan_amount = sum(row.total_amount for row in self.payment_plan)
        if flt(total_payment_plan_amount) != flt(self.total_sales_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Plan amounts'))

    def create_invoice(self):
        if flt(self.commission_amount) > 0.0:
            company = frappe.get_doc("Company", self.company)
            company_default_cost_center = frappe.db.get_value("Company", self.company, 'cost_center')
            realestate_default_cost_center = frappe.get_value("Company", self.company, "real_estate_cost_center")
            default_cost_center = realestate_default_cost_center or company_default_cost_center
            default_commission_item = frappe.get_value("Company", self.company, "commission_item")
            if not default_commission_item:
                frappe.throw(_('Please set Commission Item in Company Settings'))

            invoice = frappe.get_doc({
                "doctype": "Purchase Invoice",
                "supplier": self.sales_broker,
                "posting_date": self.posting_date,
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
