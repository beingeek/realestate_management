import frappe
from frappe import _
import re

def check_plot_booking(doc, method=None):
    if doc.get('document_type') == 'Cancellation Property' and doc.get('document_number'):
        cacellation_propertry = frappe.get_doc('Cancellation Property', doc.get('document_number'))
        if frappe.db.exists('Plot List', {'name': cacellation_propertry.plot_no, 'status':  ["in", ["Booked", "Token"]]}):
            frappe.throw('Plot not avaliable for booking')

def check_document_status(doc, method=None):
    if doc.get('document_type') == 'Customer Payment' and doc.get('document_number'):
        cust_pmt = frappe.get_doc('Customer Payment', doc.get('document_number'))
        doctype = cust_pmt.document_type
        if cust_pmt.document_number and not frappe.db.exists(doctype, {'name': cust_pmt.document_number, 'status': 'Active'}):  
            frappe.throw(_('The {0} is not Active').format(frappe.get_desk_link(doctype, cust_pmt.document_number)))

def validate_id_card_number_format(doc, method=None):
    tax_number = doc.id_card_no

    if tax_number:
        pattern = r'^\d{5}-\d{7}-\d{1}$'
        if not re.match(pattern, tax_number):
            frappe.msgprint(_('Invalid CNIC format. Please enter a valid format eg. (44204-1010085-0)'))
            frappe.throw(_('Invalid CNIC format. Please enter a valid format eg. (44204-1010085-0)'))

def validate_check_duplicate_cnic_number(doc, method=None):
        if doc.id_card_no:
            duplicate_id_card_no = frappe.get_value(
                'Customer',
                filters={
                    'id_card_no': doc.id_card_no,
                    'name': ('!=', doc.name),
                    'docstatus': ('!=', 2)
                },
                fieldname='name'
            )
            if duplicate_id_card_no:
                frappe.throw(_('Duplicate CNIC found in {0}').format(frappe.get_desk_link('Customer', duplicate_id_card_no)))
  
