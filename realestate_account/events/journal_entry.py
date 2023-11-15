import frappe
from frappe import _

def check_plot_booking(doc, method=None):
    if doc.get('custom_document_type') == 'Cancellation Property' and doc.get('custom_document_number'):
        cacellation_propertry = frappe.get_doc('Cancellation Property', doc.get('custom_document_number'))
        if frappe.db.exists('Plot List', {'name': cacellation_propertry.plot_no, 'status': 'Booked'}):
            frappe.throw('Plot Already booked')

def check_document_status(doc, method=None):
    if doc.get('custom_document_type') == 'Customer Payment' and doc.get('custom_document_number'):
        cust_pmt = frappe.get_doc('Customer Payment', doc.get('custom_document_number'))
        if cust_pmt.document_number and not frappe.db.exists('Plot Booking', {'name': cust_pmt.document_number, 'status': 'Active'}):  
            frappe.throw(_('The {0} is not Active').format(frappe.get_desk_link('Plot Booking', cust_pmt.document_number)))

    elif doc.get('custom_document_type') == 'Property Transfer' and doc.get('custom_document_number'):
        cust_pmt = frappe.get_doc('Customer Payment', doc.get('custom_document_number'))
        if cust_pmt.document_number and not frappe.db.exists('Property Transfer', {'name': cust_pmt.document_number, 'status': 'Active'}):  
            frappe.throw(_('The {0} is not Active').format(frappe.get_desk_link('Property Transfer', cust_pmt.document_number)))
