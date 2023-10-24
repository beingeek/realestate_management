# Copyright (c) 2023, CE Construction and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


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
            'total_unit_value'  :plot.total
        }
        return data
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error in fetch_data"))
        frappe.throw(_("No available plots found: {0}").format(str(e)))

@frappe.whitelist()
def update_after_submit(plot_booking_name):
    try:
        plot_booking = frappe.get_doc("Plot Booking", plot_booking_name)

        if plot_booking.plot_no:
            plot_master = frappe.get_doc("Plot List", plot_booking.plot_no)

            # Check if the plot is available or Hold for Sales
            if plot_master.status == "Available" and plot_master.hold_for_sale == 0: 
                 
                plot_master.status      = "Booked"
                plot_master.client_name = plot_booking.client_name
                plot_master.address     = plot_booking.address
                plot_master.father_name = plot_booking.father_name
                plot_master.cnic        = plot_booking.cnic
                plot_master.mobile_no   = plot_booking.mobile_no
                plot_master.sales_agent = plot_booking.sales_broker

                plot_master.save()
                frappe.db.commit()

                return "Success"          
            else:
                return "Error: The selected plot is not available for booking."

        else:
            return "Error: Plot number not specified in the Plot Booking document."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return frappe.get_traceback()

@frappe.whitelist()
def update_after_cancel(plot_booking_name):
    try:
        plot_booking = frappe.get_doc("Plot Booking", plot_booking_name)
        
        if plot_booking.plot_no:
            plot_master = frappe.get_doc("Plot List", plot_booking.plot_no)
            
            plot_master.status          = "Available"
            plot_master.client_name     = ""
            plot_master.address         = ""
            plot_master.father_name     = ""
            plot_master.cnic            = ""
            plot_master.mobile_no       = ""
            plot_master.sales_agent     = ""
            
            plot_master.save()
            frappe.db.commit()
            
            return "Success"
        else:
            return "Plot number not specified in the Plot Booking document."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to update plot status"))
        return "Failed"

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



class PlotBooking(Document):
    pass