import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    flt, cstr, today
)

class ClosedAccountingPeriod(frappe.ValidationError):
	pass

class PlotBooking(Document):
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

    def validate_amount(self):
        if flt(self.difference) != 0.0:
            frappe.throw(_('Amount of Installment Total and Grand Total is not matched'))


    def create_invoice(self):
        company = frappe.get_doc("Company", self.company)
        company_default_cost_center = frappe.db.get_value("Company", self.company, 'cost_center')
        realestate_default_cost_center = frappe.db.get_single_value("Real Estate Setting", "cost_center")
        default_commission_item = frappe.db.get_single_value("Real Estate Setting", "commission_item")
        default_cost_center = realestate_default_cost_center or company_default_cost_center

        invoice = frappe.get_doc({
                    "doctype": "Purchase Invoice",
                    "supplier": self.sales_broker,
                    "posting_date": self.booking_date,
                    "bill_no" : self.plot_no,
                    "project" : self.project_name,
                    "cost_centre" : "",
                    "custom_booking_number":self.name,
                    "company" : company
                })

        invoice.append("items", {
                    "item_code": default_commission_item,
                    "qty": 1,
                    "rate": self.commission_amount,
                    "amount": self.commission_amount,
                    "project" : self.project_name,
                    "cost_centre" : default_cost_center
                })

        invoice.insert(ignore_permissions=True)
        invoice.submit()
        frappe.msgprint(_('{0} Broker commission created').format(frappe.get_desk_link('Purchase Invoice', invoice.name)))

    def book_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)

        # Check if the plot is available or Hold for Sales
        if plot_master.status == "Available" and plot_master.hold_for_sale == 0:
            plot_master.update({
                'status': "Booked", 'client_name': self.client_name, 'address': self.address,
                'mobile_no': self.mobile_no, 'sales_agent': self.sales_broker,
                'father_name': self.father_name, 'cnic': self.cnic,
            })
            plot_master.save()
            frappe.msgprint(_('{0} booked successfully').format(frappe.get_desk_link('Plot List', plot_master.name)))
        else:
            frappe.throw(_("Error: The selected plot is not available for booking."))

    def unbook_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        plot_master.update({
            'status': "Available", 'client_name': '', 'address': '',
            'mobile_no': '', 'sales_agent': '',
            'father_name': '',  'cnic': ''
        })

        plot_master.save()
        frappe.msgprint(_('{0} unbooked').format(frappe.get_desk_link('Plot List', plot_master.name)))

@frappe.whitelist()
def get_available_plots(project_name):
    try:
        sql_query = """
            SELECT DISTINCT plot_name as plot_no, land_price, plot_feature FROM `tabPlot List`
            WHERE `status` = 'Available' AND hold_for_sale = 0 AND `project_name` = %s
        """
        results = frappe.db.sql(sql_query, (project_name), as_dict=True)
        if not results:
            return []
        return results
    except Exception as e:
        frappe.log_error(f"Error in get_available_plots: {str(e)}")
        return []

@frappe.whitelist()
def get_plot_detail(plot_no):
    try:
        plot = frappe.get_doc("Plot List", plot_no)
        data = {
            'plot_feature'      : plot.plot_feature,
            'land_price'        : plot.land_price,
            'land_area'         : plot.land_area,
            'uom'               : plot.uom,
            'total_unit_value'  : plot.total
        }
        return data
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error in fetch_data"))
        frappe.throw(_("No available plots found: {0}").format(str(e)))


@frappe.whitelist()
def create_invoice(plot_booking):
    hb_doc = frappe.get_doc("Plot Booking", plot_booking)
    company = frappe.get_doc("Company", hb_doc.company)
    default_item = company.custom_default_commission_item
    default_cost_center = company.cost_center
    
    invoice = frappe.get_doc({
                "doctype": "Purchase Invoice",
                "supplier": hb_doc.sales_broker,
                "posting_date": hb_doc.booking_date,  
                "bill_no" : hb_doc.plot_no,
                "project" : hb_doc.project_name,
                "cost_centre" : "",
                "custom_booking_number":hb_doc.name,
                "company" : company
            })

    invoice.append("items", {
                "item_code": default_item,  
                "qty": 1,  
                "rate": hb_doc.commission_amount,  
                "amount": hb_doc.commission_amount,
                "project" : hb_doc.project_name,
                "cost_centre" : default_cost_center
            })
    try:
        invoice.insert(ignore_permissions=True)
        invoice.submit()
        frappe.db.commit()
        return {"message": f"Broker Commission Invoice {invoice.name} created successfully", "invoice": invoice.name}
    except frappe.exceptions.ValidationError as e:
        frappe.msgprint(f"Error creating invoice: {str(e)}")
    except Exception as ex:
        frappe.msgprint(f"Unexpected error: {str(ex)}")

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
            & (doc.booking_date >= ap.start_date)
            & (doc.booking_date <= ap.end_date)
        )
    ).run(as_dict=1)

    if accounting_period:
        frappe.throw(_("You cannot create a {0} within the closed Accounting Period {1}").format(
            doc.doctype, frappe.bold(accounting_period[0]["name"]),
            ClosedAccountingPeriod
        ))
