import frappe

def check_plot_booking(doc, method=None):
    if doc.get('custom_document_type') == 'Cancellation Property' and doc.get('custom_document_number'):
        cacellation_propertry = frappe.get_doc('Cancellation Property', doc.get('custom_document_number'))
        if frappe.db.exists('Plot List', {'name': cacellation_propertry.plot_no, 'status': 'Booked'}):
            frappe.throw('Plot Already booked')

def check_document_status(doc, method=None):
    pass
#     if doc.get('custom_document_type') == 'Customer Payment' and doc.get('custom_document_number'):
#         cust_pmt = frappe.get_doc('Customer Payment', doc.get('document_number'))  
#         if frappe.db.exists('Property Transfer', {'name': cust_pmt.document_number, 'status': 'cancel'}):  
#             frappe.throw('The parent document is not Active')


        # doc_type = self.document_type
        # doc_number = self.document_number

        # if doc_type in ['Plot Booking', 'Property Transfer']:
        #     doc_status = frappe.get_value(doc_type, {'name': doc_number}, 'status')
        #     if doc_status != 'Active':
        #         frappe.throw(f'The parent document {doc_type} with name {doc_number} is not Active')
