# Copyright (c) 2023, CE Construction and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr, flt, getdate
from realestate_account.controllers.real_estate_controller import get_previous_document_detail


def execute(filters=None):
	if not filters.get('plot'):
		frappe.throw(_('Please set Filter'))
	
	plot = filters.get('plot')
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Col1"),
			"fieldname": "col1",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Col2"),
			"fieldname": "col2",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Col3"),
			"fieldname": "col3",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Col4"),
			"fieldname": "col4",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Col5"),
			"fieldname": "col5",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Col6"),
			"fieldname": "col6",
			"fieldtype": "Data",
			"width": 250
		}
	]

	return columns


def get_data(filters):

	plot_data = frappe.db.sql("""select * from `tabPlot List` where name=%(plot)s """, filters, as_dict=1)
	
	if not plot_data:
		frappe.msgprint('No plot found')
		return []

	plot_data = plot_data[0]
	plot_payment_detail = get_previous_document_detail(filters.get('plot'))

	if not plot_payment_detail:
		frappe.msgprint('No plot payment found')

	plot_payment_detail = plot_payment_detail[0]

	payment_detail = get_payment_detail(filters.get('to_date'), plot_payment_detail.get('name'))

	installments = []
	if plot_payment_detail.get('Doc_type') == 'Plot Booking':
		installments = get_installment_list_from_booking(plot_payment_detail.get('name'))
	elif plot_payment_detail.get('Doc_type') == 'Property Transfer':
		installments = get_installment_list_from_transfer(plot_payment_detail.get('name'))

	overdue_amt = 0
	if installments:
		for installment in installments:
			if installment.get('date') < getdate(filters.get('to_date')):
				overdue_amt += installment.get('receivable_amount')

	received_amount_perc = flt((plot_payment_detail.get('received_amount')/plot_payment_detail.get('sales_amount')) * 100, 2)

	data = [
		{
			"col1": "<b>Current Ownership Detail :</b>"
		},
		{
			'col1': "<b>Member Name :</b>",
			"col2": plot_data.get('customer')
		},
		{
			'col1': "<b>F/O:</b>",
			"col2": plot_data.get('father_name')
		},
		{
			'col1': "<b>CNIC No :</b>",
			"col2": plot_data.get('cnic')
		},
		{
			'col1': "<b>Mobile ,Ph,Off/res:</b>",
			"col2": plot_data.get('contact_no')
		},
		{
			'col1': "<b>Address:</b>",
			"col2": plot_data.get('address')
		},
		{
			'col1': "",
			"col2": ""
		},
		{
			"col1": "<b>Property Information:</b>"
		},
		{
			'col1': "<b>Project Name</b>",
			"col2": plot_data.get('project')
		},
		{
			'col1': "<b>Property Detail:</b>",
			"col2": plot_data.get('plot_detail')
		},
		{
			'col1': "<b>Plot Area/UOM :</b>",
			"col2": "{0}/{1}".format(plot_data.get('land_area'), plot_data.get('uom'))
		},
		{
			'col1': "",
			"col2": ""
		},
		{
			"col1": "<b>Payment Details:</b>"
		},
		{
			'col1': "<b>Registration No:</b>",
			"col2": plot_payment_detail.get('name'),
			'col3': "<b>Received Amount:</b>",
			"col4": plot_payment_detail.get('received_amount'),
		},
		{
			'col1': "<b>Sales Amount:</b>",
			"col2": plot_payment_detail.get('sales_amount'),
			'col3': "<b>Received %age:</b>",
			"col4": "{0} %".format(received_amount_perc),
		},
		{
			'col1': "<b>Overdue Amount:</b>",
			"col2": overdue_amt,
		},
		{
			'col1': "",
			"col2": ""
		},
	]

	if installments:
		data.extend([
			{
				'col1': "<b>Installement Details:</b>",
			},
			{
				'col1': "<b>Payment Desc:</b>",
				'col2': "<b>Due Date:</b>",
				'col3': "<b>Installment Amt:</b>",
				'col4': "<b>Received Amt:</b>",
				'col5': "<b>Outstanding Amt:</b>",
			}
		])
		for installment in installments:
			received_amount = installment.get('installment_amount') - installment.get('receivable_amount')
			data.append({
				'col1': installment.get('Installment'),
				'col2': installment.get('date'),
				'col3': installment.get('installment_amount'),
				'col4': received_amount,
				'col5': installment.get('receivable_amount'),
			})

	if payment_detail:
		data.extend([
			{
				'col1': "",
				"col2": ""
			},
			{
				'col1': "<b>Payment Receiving Details:</b>",
			},
			{
				'col1': "<b>Receipt No:</b>",
				'col2': "<b>Payment Mode:</b>",
				'col3': "<b>Paid Date:</b>",
				'col4': "<b>Paid Amt:</b>",
				'col5': "<b>Cheque No:</b>",
				'col6': "<b>Cheque Date:</b>",
			}
		])
		for payment in payment_detail:
			data.append({
				'col1': payment.get('name'),
				'col2': payment.get('mode_of_payment'),
				'col3': payment.get('posting_date'),
				'col4': payment.get('amount'),
				'col5': payment.get('cheque_no'),
				'col6': payment.get('cheque_date')
			})
	
	return data



def get_payment_detail(date, doc_no):
	condition = {'date': date, 'doc_no': doc_no}
	payment_detail = frappe.db.sql("""
		SELECT tcp.posting_date , tcp.name , tpt.mode_of_payment , tpt.amount , tpt.cheque_no , tpt.cheque_date 
		FROM `tabCustomer Payment` tcp INNER JOIN `tabPayment Type` tpt on tcp.name = tpt.parent 
		WHERE tcp.posting_date <= %(date)s and tcp.docstatus  = 1 and document_number = %(doc_no)s
	""", condition, as_dict=1)

	return payment_detail if payment_detail else []
	

def get_installment_list_from_booking(doc_no):
	sql_query = """
		SELECT 
			x.Installment,
			x.date,
			x.remarks,
			x.idx,
			x.name,
			x.installment_amount,
			x.receivable_amount
		FROM (
			SELECT
				c.name,
				d.installment_name as Installment,
				d.date,
				d.remarks,
				d.idx,
				d.amount as installment_amount,
				d.amount - IFNULL((
						SELECT SUM(b.paid_amount) AS paid_amount
						FROM `tabCustomer Payment` AS a
						INNER JOIN `tabCustomer Payment Installment` AS b
						ON a.name = b.parent
						WHERE a.docstatus = 1
						AND a.document_number = c.name
						AND b.base_doc_idx = d.idx
						AND a.plot_no = c.plot_no), 0 ) AS receivable_amount
		FROM
			`tabPlot Booking` AS c
		INNER JOIN
			`tabInstallment Payment Plan` AS d
		ON
			c.name = d.parent
		WHERE
			c.name = %s
		ORDER BY 
			d.date ASC ) x

		ORDER BY x.idx
	"""
	results = frappe.db.sql(sql_query, (doc_no), as_dict=True) or []
	return results


def get_installment_list_from_transfer(doc_no):
	sql_query = """
		SELECT 
			x.Installment,
			x.date,
			x.remarks,
			x.idx,
			x.receivable_amount,
			x.name,
			x.installment_amount
		FROM (
			SELECT
				c.name,
				d.installment_name as Installment,
				d.date,
				d.remarks,
				d.idx,
				d.amount as installment_amount,
				d.amount - IFNULL((
						SELECT SUM(b.paid_amount) AS paid_amount
						FROM `tabCustomer Payment` AS a
						INNER JOIN `tabCustomer Payment Installment` AS b
						ON a.name = b.parent
						WHERE a.docstatus = 1
						AND a.document_number = c.name
						AND b.base_doc_idx = d.idx
						AND a.plot_no = c.plot_no), 0 ) AS receivable_amount
			FROM
				`tabProperty Transfer` AS c
			INNER JOIN
				`tabInstallment Payment Plan - Transfer` AS d
			ON
				c.name = d.parent
			WHERE
				c.name = %s
			ORDER BY 
				d.date ASC ) x 
		ORDER BY x.idx
	"""
	return frappe.db.sql(sql_query, (doc_no), as_dict=True) or []
