import frappe
from frappe import _
from frappe.utils import flt
from realestate_account.controllers.real_estate_controller import RealEstateController, validate_accounting_period_open

class PlotBooking(RealEstateController):
    def validate(self):
        self.validate_posting_date()
        validate_accounting_period_open(self)
        self.validate_plot_booking()
        self.validate_amount()
        self.validate_payment_schedule_sales_amount()
        self.validate_payment_plan_sales_amount()
        self.validate_duplicates_customer_in_partnership()
        self.validate_share_percentage()

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
            frappe.throw(_('The {0} is not avaliable for booked').format(frappe.get_desk_link('Plot List', self.plot_no)))

    def validate_payment_schedule_sales_amount(self):
        total_payment_schedule_amount = sum(row.amount for row in self.payment_schedule)
        if flt(total_payment_schedule_amount) != flt(self.total_sales_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Schedule amounts'))

    def validate_payment_plan_sales_amount(self):
        total_payment_plan_amount = sum(row.total_amount for row in self.payment_plan)
        if flt(total_payment_plan_amount) != flt(self.total_sales_amount):
            frappe.throw(_('Total Sales Amount does not match the sum of Payment Plan amounts'))

    def validate_share_percentage(self):
        if self.customer_type == "Individual":
            if flt(self.share_percentage) != 100.0:
                frappe.throw(_('The Individual customer share percentage must be equal to 100. Current total: {0:.2f}').format(self.share_percentage))
            rows = len([row.customer for row in self.customer_partnership])
            if rows > 0:
                frappe.throw(_('Remove the rows in the customer partnership table.'))
        
        elif self.customer_type == "Partnership":
            share_percentage = flt(self.share_percentage) + flt(sum(row.share_percentage for row in self.customer_partnership))
            
            if flt(share_percentage) != 100.0:
                frappe.throw(_('The Partnership customers share percentage must be equal to 100. Current total: {0:.2f}').format(share_percentage))
            if any(row.share_percentage == 0.0 for row in self.customer_partnership):
                frappe.throw(_('Share percentage for Partnership customers cannot be 0.0'))
            if flt(self.share_percentage) == 0.0:
                frappe.throw(_('Share percentage for Main customers cannot be 0.0'))

    def validate_duplicates_customer_in_partnership(self):
        partnership_customer = [row.customer for row in self.customer_partnership]
        duplicates_in_partnership = set(x for x in partnership_customer if partnership_customer.count(x) > 1)
        
        if duplicates_in_partnership:
            frappe.throw(_('Duplicate customer found in the customer partnership table: {0}').format(', '.join(duplicates_in_partnership)))
        
        if self.customer in partnership_customer:
            frappe.throw(_('Duplicate customer found in the customer partnership table.'))

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
                "doctype"           : "Purchase Invoice",
                "supplier"          : self.sales_broker,
                "posting_date"      : self.posting_date,
                "bill_no"           : self.plot_no,
                "project"           : self.project,
                "cost_centre"       : "",
                "document_number"   :self.name,
                "company"           : company
            })

            invoice.append("items", {
                    "item_code"     : default_commission_item, 
                    "qty"           : 1,
                    "rate"          : self.commission_amount,
                    "project"       : self.project,
                    "cost_centre"   : default_cost_center
            })

            invoice.insert(ignore_permissions=True)
            invoice.submit()
            frappe.msgprint(_('{0} Broker commission created').format(frappe.get_desk_link('Purchase Invoice', invoice.name)))

    def book_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        
        if (plot_master.status == "Available" or plot_master.status == "Token") and plot_master.hold_for_sale == 0:
            plot_master.update({      
                'status'            : "Booked",
                'customer'          : self.customer,
                'address'           : self.address,
                'contact_no'        : self.contact_no,
                'sales_broker'      : self.sales_broker,
                'father_name'       : self.father_name,
                'cnic'              : self.cnic,
                'customer_type'     : self.customer_type,
                'share_percentage'  : self.share_percentage,
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
        else:
            frappe.throw(_("Error: The selected plot is not available for booking."))
        
        if self.token_number :
            plot_token = frappe.get_doc("Plot Token", self.token_number)
            plot_token.update({'status' : "Transfer to Booking"})
            plot_token.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Token", plot_token.name)))

    def unbook_plot(self):
        plot_master = frappe.get_doc("Plot List", self.plot_no)
        if not self.token_number :
            plot_master.update({
                'status'            : "Available",
                'customer'          : '',
                'address'           : '',
                'contact_no'        : '',
                'sales_broker'      : '',
                'father_name'       : '',
                'cnic'              : '',
                'customer_type'     : '',
                'share_percentage'  : '',
            })

        if self.customer_type == "Partnership":
            plot_master.set("customer_partnership", [])

        if self.token_number :
            plot_master.update({
                'status'            : "Token",
                'customer'          : self.customer,
                'address'           : self.address,
                'contact_no'        : self.contact_no,
                'sales_broker'      : self.sales_broker,
                'father_name'       : self.father_name,
                'cnic'              : self.cnic,
                'customer_type'     : '',
                'share_percentage'  : '',
            })

            if self.customer_type == "Partnership":
                plot_master.set("customer_partnership", [])

        plot_master.save()
        frappe.msgprint(_('{0} unbooked').format(frappe.get_desk_link('Plot List', plot_master.name)))
        
        if self.token_number :
            plot_token = frappe.get_doc("Plot Token", self.token_number)
            plot_token.update({'status' : "Active"})
            plot_token.save()
            frappe.msgprint(_('{0} successfully updated').format(frappe.get_desk_link("Plot Token", plot_token.name)))

    def before_insert(self):
        if self.status != 'Active':
            frappe.throw(_('The booking status should be Active'))