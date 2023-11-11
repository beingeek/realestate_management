import frappe

def check_plot_booking(doc, method=None):
    if doc.get('custom_document_type') == 'Cancellation Property' and doc.get('custom_document_number'):
        cacellation_propertry = frappe.get_doc('Cancellation Property', doc.get('custom_document_number'))
        if frappe.db.exists('Plot List', {'name': cacellation_propertry.plot_no, 'status': 'Booked'}):
            frappe.throw('Plot Already booked')
