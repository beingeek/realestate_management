
frappe.ui.form.on('Cancellation Property', {
    project_name: function(frm) {
        var project_name = frm.doc.project_name;
        if (!frm.doc.project_name) {
            frappe.throw(__("Please select a project."));
            return;
        }
        if (frm.prompt_opened) {
            return;
        }

        frm.cscript.project_name = function(doc) {
            if (doc.project_name !== project_name) {
                frm.prompt_opened = false;
            }
        };
        frm.prompt_opened = true;
        frappe.prompt({
            label: __("Select Available Plot"),
            fieldname: 'selected_plot',
            fieldtype: "Link",
            options: "Plot List",
            get_query: () => ({
                filters: {
                    "status": 'Booked', 'project_name': frm.doc.project_name
                }
            })
        }, (values) => {
            frappe.model.set_value(frm.doctype, frm.docname, 'plot_no', values.selected_plot);
            frm.prompt_opened = false;
        }, __('Select Available Plot'));
    }
});
	cur_frm.cscript.plot_no = function(doc) {
		frappe.call({
			method: "realestate_account.realestate_account.doctype.cancellation_property.cancellation_property.get_previous_document_detail",
			args: {
				plot_no: doc.plot_no
			},
			callback: function(r) {
			console.log(r)
			if (!r.exc && r.message && r.message.length > 0) {
				if (!r.exc && r.message && r.message.length > 0) {
					var name = r.message[0].name;
					var Customer = r.message[0].customer;
					var docType = r.message[0].Doc_type;
					var salesBroker = r.message[0].sales_broker;
					var salesAmount = r.message[0].sales_amount;
					var receivedAmount = r.message[0].received_amount;
				
					cur_frm.set_value('document_type', docType);
					cur_frm.set_value('document_number', name);
					cur_frm.set_value("sales_amount", salesAmount);
					cur_frm.set_value("received_amount", receivedAmount);
					cur_frm.set_value("final_payment", receivedAmount);
					cur_frm.set_value("sales_broker", salesBroker);
					cur_frm.set_value("customer", Customer);			  
				}
			}
		}
	});
}

frappe.ui.form.on('Cancellation Property', {
    deduction: function(frm) {
        calculate_final_amount(frm);
    }
});
function calculate_final_amount(frm) {
    var finalAmount = frm.doc.received_amount - frm.doc.deduction;
    frm.set_value("final_payment", finalAmount);
}


/////////////////////////// Payment Type payment ledger filter  //////////

frappe.ui.form.on('Cancellation Property', {
    refresh: function(frm) {
        frm.fields_dict['payment_type'].grid.get_field('ledger').get_query = function(doc, cdt, cdn) {
            var child = locals[cdt][cdn];
            var filters = {};
            if (child.mode_of_payment === 'Cash') {
                filters = {
                    account_type: 'Cash',
                    is_group: 0 
                    };
            } else if (child.mode_of_payment === 'Cheque' || child.mode_of_payment === 'Bank Transfer') {
                filters = {
                account_type: 'Bank',
                is_group: 0 
                };
            }
            return {
                filters: filters
            };
        };
    }
});
 



