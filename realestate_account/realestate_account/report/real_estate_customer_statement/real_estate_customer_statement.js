// Copyright (c) 2023, CE Construction and contributors
// For license information, please see license.txt

frappe.query_reports["Real Estate Customer Statement"] = {
	"filters": [
		{
			"fieldname":"plot",
			"label": __("Plot"),
			"fieldtype": "Link",
			"options": "Plot List",
			"reqd": 1,
			get_query: () => {
				return {
					filters: {
						'status': "Booked"
					}
				}
			}
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
	]
};
