import frappe
from frappe import _
import re


def check_plot_booking(doc, method=None):
    if doc.get('document_type') == 'Cancellation Property' and doc.get('document_number'):
        cacellation_propertry = frappe.get_doc('Cancellation Property', doc.get('document_number'))
        if frappe.db.exists('Plot List', {'name': cacellation_propertry.plot_no, 'status': 'Booked'}):
            frappe.throw('Plot Already booked')

def check_document_status(doc, method=None):
    if doc.get('document_type') == 'Customer Payment' and doc.get('document_number'):
        cust_pmt = frappe.get_doc('Customer Payment', doc.get('document_number'))
        if cust_pmt.document_number and not frappe.db.exists('Plot Booking', {'name': cust_pmt.document_number, 'status': 'Active'}):  
            frappe.throw(_('The {0} is not Active').format(frappe.get_desk_link('Plot Booking', cust_pmt.document_number)))

    elif doc.get('document_type') == 'Property Transfer' and doc.get('document_number'):
        cust_pmt = frappe.get_doc('Customer Payment', doc.get('document_number'))
        if cust_pmt.document_number and not frappe.db.exists('Property Transfer', {'name': cust_pmt.document_number, 'status': 'Active'}):  
            frappe.throw(_('The {0} is not Active').format(frappe.get_desk_link('Property Transfer', cust_pmt.document_number)))


def validate_id_card_number_format(doc, method=None):
    tax_number = doc.id_card_no

    if tax_number:
        pattern = r'^\d{5}-\d{7}-\d{1}$'
        if not re.match(pattern, tax_number):
            frappe.msgprint(_('Invalid CNIC format. Please enter a valid format eg. (44204-1010085-0)'))
            frappe.throw(_('Invalid CNIC format. Please enter a valid format eg. (44204-1010085-0)'))
  