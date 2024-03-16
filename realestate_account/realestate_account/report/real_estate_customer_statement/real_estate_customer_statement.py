# Copyright (c) 2023, CE Construction and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr, flt, getdate
from realestate_account.controllers.real_estate_controller import get_previous_document_detail, get_customer_partner

def execute(filters=None):
	if not filters.get("plot"):
		frappe.throw(_("Please set Filter"))
	
	plot = filters.get("plot")
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
		frappe.msgprint("No plot found")
		return []

	plot_data = plot_data[0]
	plot_payment_detail = get_previous_document_detail(filters.get("plot"))
	
	if not plot_payment_detail:
		frappe.msgprint("No plot payment found")

	plot_payment_detail = plot_payment_detail[0]

	partners = get_customer_partner(plot_payment_detail.get("name"))
	if partners:
		partners = ", ".join([d.customer for d in partners])

	payment_detail = get_payment_detail(filters.get("to_date"), plot_payment_detail.get("name"))

	installments = [] 
	if plot_payment_detail.get("ppr_active") == 0: 
		if plot_payment_detail.get("Doc_type") == "Plot Booking":
			installments = get_installment_list_from_booking(plot_payment_detail.get("name"))
		elif plot_payment_detail.get("Doc_type") == "Property Transfer":
			installments =  get_installment_list_from_transfer(plot_payment_detail.get("name"))
	elif plot_payment_detail.get("ppr_active") == 1: 
		if plot_payment_detail.get("Doc_type") == "Plot Booking":
			installments = get_installment_list_reschedule_booking(plot_payment_detail.get("name"))
		elif plot_payment_detail.get("Doc_type") == "Property Transfer":
			installments = get_installment_list_reschedule_transfer(plot_payment_detail.get("name"))

	overdue_amt = 0
	outstanding_amt = 0
	if installments:
		for installment in installments:
			outstanding_amt += installment.get("receivable_amount")
			if installment.get("date") < getdate(filters.get("to_date")):
				overdue_amt += installment.get("receivable_amount")

	received_amount_perc = flt((plot_payment_detail.get("received_amount")/plot_payment_detail.get("sales_amount")) * 100, 2)

	data = [
		{
			"ownership_details": 1,
			"col1": "<b>Customer Detail</b>",
			"col2": "",
		},
		{
			"ownership_details": 1,
			"col1": "<b>Member Name :</b>",
			"col2": plot_data.get("customer")
		},
		{
			"ownership_details": 1,
			"col1": "<b>F/O or H/N:</b>",
			"col2": plot_data.get("father_name"),
		},
		{
			"ownership_details": 1,
			"col1": "<b>CNIC No :</b>",
			"col2": plot_data.get("cnic")
		},
		{
			"ownership_details": 1,
			"col1": "<b>Mobile No.</b>",
			"col2": plot_data.get("contact_no")
		},
		{
			"ownership_details": 1,
			"col1": "<b>Registration No:</b>",
			"col2": """<a href="/app/{0}/{1}">{1}</a>""".format(frappe.scrub(plot_payment_detail.get("Doc_type")).replace("_", "-"), plot_payment_detail.get("name")),
		},
		{
			"registration_details": 1,
			"col1": "<b>Property Information:</b>",
		},
		{
			"registration_details": 1,
			"col1": "<b>Project Name</b>",
			"col2": plot_data.get("project")
		},
		{
			"registration_details": 1,
			"col1": "<b>Property Detail:</b>",
			"col2": plot_data.get("plot_detail")
		},
		{
			"registration_details": 1,
			"col1": "<b>Plot Number:</b>",
			"col2": filters.get("plot")
		},
		{
			"registration_details": 1,
			"col1": "<b>Plot Area:</b>",
			"col2": "{0}".format(plot_data.get("land_area"))
		},
		{
			"registration_details": 1,
			"col1": "<b>Plot UOM :</b>",
			"col2": "{0}".format(plot_data.get("uom"))
		},
		{
			"payment_details": 1,
			"col1": '<b>Payment Detail</b>'
		},
		{
			"payment_details": 1,
			"col1": "<b>Sales Amount:</b>",
			"col2": frappe.utils.fmt_money(plot_payment_detail.get("sales_amount"), currency="Rs")
		},
		{
			"payment_details": 1,
			"col1": "<b>Received Amount:</b>",
			"col2": frappe.utils.fmt_money(plot_payment_detail.get("received_amount"), currency="Rs" ),
		},
		{
			"payment_details": 1,
			"col1": "<b>Received %age:</b>",
			"col2": "{0} %".format(received_amount_perc),
		},
		{
			"payment_details": 1,
			"col1": "<b>Outstanding </b>",
			"col2": frappe.utils.fmt_money(outstanding_amt, currency="Rs")
		},
		{
			"payment_details": 1,
			"col1": "<b>Overdue Amount:</b>",
			"col2": frappe.utils.fmt_money(overdue_amt, currency="Rs")
		},
	]

	if payment_detail:
		data.extend([
			{
				"col1": "<b>Payment Receiving Details:</b>",
			},
			{
				"payment_table_head": 1,
				"col1": "<b>Paid Date</b>",
				"col2": "<b>Book No.</b>",
				"col3": "<b>Receipt No.</b>",
				"col4": "<b>Payment Mode</b>",
				"col5": "<b>Paid Amount</b>",
				"col6": "<b>Cheque No & Date:</b>",
			}
		])
		for payment in payment_detail:
			
			data.append({
				"payment_table_row": 1,
				"col1": frappe.utils.formatdate(payment.get("posting_date")),
				"col2": payment.get("book_number"),
				"col3": payment.get("name"), 
				"col4": payment.get("mode_of_payment"),
				"col5": frappe.utils.fmt_money(payment.get("amount"), currency="PKR"),
				"col6": str(payment.get("cheque_no")) + ' ' + frappe.utils.formatdate(payment.get("cheque_date")),
			})

	data.append({
		"col1": "",
		"col2": ""
	})

	if installments:
		data.extend([
			{
				"col1": "<b>Installement Details:</b>",
			},
			{
				"installement_table_head": 1,
				"col1": "<b>Installment Description:</b>",
				"col2": "<b>Due Date:</b>",
				"col3": "<b>Installment Amt:</b>",
				"col4": "<b>Received Amt:</b>",
				"col5": "<b>Outstanding Amt:</b>",
				"col6": "<b>Remarks:</b>",
			}
		])
		for installment in installments:
			received_amount = installment.get("installment_amount") - installment.get("receivable_amount")
			data.append({
				"installement_table_row": 1,
				"col1": installment.get("Installment"),
				"col2": frappe.utils.formatdate(installment.get("date")),
				"col3": frappe.utils.fmt_money(installment.get("installment_amount"), currency="PKR"),
				"col4": frappe.utils.fmt_money(received_amount, currency="PKR"),
				"col5": frappe.utils.fmt_money(installment.get("receivable_amount"), currency="PKR"),
				"col6": installment.get("plan_type")
			})

	return data

def get_payment_detail(date, doc_no):
	condition = {"date": date, "doc_no": doc_no}
	payment_detail = frappe.db.sql("""
		SELECT tcp.posting_date , tcp.book_number, tcp.name , tpt.mode_of_payment , tpt.amount , tpt.cheque_no , tpt.cheque_date 
		FROM `tabCustomer Payment` tcp INNER JOIN `tabPayment Type` tpt on tcp.name = tpt.parent 
		WHERE tcp.posting_date <= %(date)s and tcp.docstatus  = 1 and document_number = %(doc_no)s
		Order by tcp.posting_date ASC
	""", condition, as_dict=1)

	return payment_detail if payment_detail else []

def get_installment_list_from_booking(doc_no):
	sql_query = """
		SELECT
				c.name,
				d.remarks as plan_type,
				d.installment_name as Installment,
				d.date,
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
			d.date ASC , d.idx
	"""
	results = frappe.db.sql(sql_query, (doc_no), as_dict=True) or []
	return results

def get_installment_list_from_transfer(doc_no):
	sql_query = """
			SELECT
				c.name,
				d.remarks as plan_type,
				d.installment_name as Installment,
				d.date,
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
				`tabPayment Plan Reschedule Installment` AS d
			ON
				c.name = d.parent
			WHERE
				c.name = %s
			ORDER BY 
				d.date ASC , d.idx
	"""
	return frappe.db.sql(sql_query, (doc_no), as_dict=True) or []

def get_installment_list_reschedule_booking(doc_no):
	sql_query = """
		WITH paid_installment AS (
		SELECT
			b.date, 
			b.base_doc_idx, 
			b.installment, 
			SUM(b.paid_amount) AS paid_amount, 
			b.ppr_child_table, 
			a.document_number,
			IFNULL(
				(
					CASE 
						WHEN a.document_type = 'Plot Booking' THEN c.payment_plan_reschedule 
						ELSE d.payment_plan_reschedule 
					END
				),
				0
			) AS payment_schedule
		FROM 
			`tabCustomer Payment` a
			INNER JOIN `tabCustomer Payment Installment` AS b ON a.name = b.parent 
			LEFT OUTER JOIN `tabPlot Booking` AS c ON a.payment_plan_reschedule = c.payment_plan_reschedule 
			LEFT OUTER JOIN `tabProperty Transfer` AS d ON a.payment_plan_reschedule = d.payment_plan_reschedule 
		WHERE 
			a.docstatus = 1 AND a.document_number = %s
		GROUP BY 
			b.date, b.base_doc_idx, b.installment, b.ppr_child_table, c.payment_plan_reschedule
	),
	unpaid_installment AS (
		SELECT 
			x.document_number, 
			'Initial Plan' as plan_type,
			x.installment AS Installment,  
			x.date, 
			x.paid_amount AS installment_amount, 
			0 AS receivable_amount
		FROM 
			paid_installment AS x 
		WHERE 
			payment_schedule = '0' 
		UNION ALL   
		SELECT 
			c.name,
			'Plan Reschedule' as plan_type,
			e.installment_name AS Installment,
			e.date,
			e.amount AS installment_amount,
			e.amount - IFNULL(
				(
					SELECT SUM(b.paid_amount) AS paid_amount
					FROM `tabCustomer Payment` AS a
					INNER JOIN `tabCustomer Payment Installment` AS b ON a.name = b.parent
					WHERE a.docstatus = 1
					AND a.document_number = c.name
					AND b.ppr_child_table = e.name
					AND a.plot_no = c.plot_no
				), 
				0
			) AS receivable_amount
		FROM
			`tabPlot Booking` AS c
			INNER JOIN `tabPayment Plan Reschedule` AS d ON d.name = c.payment_plan_reschedule
			INNER JOIN `tabPayment Plan Reschedule Installment` AS e ON d.name = e.parent
		WHERE
			c.name = %s 
			AND c.ppr_active = 1)
	SELECT * FROM unpaid_installment as x Order by x.date ;
	"""
	return frappe.db.sql(sql_query, (doc_no, doc_no), as_dict=True) or []

def get_installment_list_reschedule_transfer(doc_no):
	sql_query = """
		WITH paid_installment AS (
		SELECT 
			b.date, 
			b.base_doc_idx, 
			b.installment, 
			SUM(b.paid_amount) AS paid_amount, 
			b.ppr_child_table, 
			a.document_number,
			IFNULL(( d.payment_plan_reschedule ),0 ) AS payment_schedule
		FROM 
			`tabCustomer Payment` a
			INNER JOIN `tabCustomer Payment Installment` AS b ON a.name = b.parent 
			LEFT OUTER JOIN `tabProperty Transfer` AS d ON a.payment_plan_reschedule = d.payment_plan_reschedule 
		WHERE 
			a.docstatus = 1 AND a.document_number = %s 
		GROUP BY 
			b.date, b.base_doc_idx, b.installment, b.ppr_child_table, d.payment_plan_reschedule
	),
	unpaid_installment AS (
		SELECT 
			x.document_number, 
			'Initial Plan' as plan_type,
			x.installment AS Installment,  
			x.date,
			0 as idx,
			x.paid_amount AS installment_amount, 
			0 AS receivable_amount
		FROM 
			paid_installment AS x 
		WHERE 
			payment_schedule = '0' 
		UNION ALL   
		SELECT 
			c.name,
			'Plan Reschedule' as plan_type,
			e.installment_name AS Installment,
			e.date,
			e.idx,
			e.amount AS installment_amount,
			e.amount - IFNULL(
				(
					SELECT SUM(b.paid_amount) AS paid_amount
					FROM `tabCustomer Payment` AS a
					INNER JOIN `tabCustomer Payment Installment` AS b ON a.name = b.parent
					WHERE a.docstatus = 1
					AND a.document_number = c.name
					AND b.ppr_child_table = e.name
					AND a.plot_no = c.plot_no
				), 
				0
			) AS receivable_amount
		FROM
			`tabProperty Transfer` AS c
			INNER JOIN `tabPayment Plan Reschedule` AS d ON d.name = c.payment_plan_reschedule
			INNER JOIN `tabPayment Plan Reschedule Installment` AS e ON d.name = e.parent
		WHERE
			c.name = %s 
			AND c.ppr_active = 1)
	SELECT * FROM unpaid_installment as x Order by x.date, x.idx ;
	"""
	return frappe.db.sql(sql_query, (doc_no, doc_no), as_dict=True) or []
