frappe.ui.form.on('Cancellation Property', {
    deduction: function(frm) {
        calculate_final_amount(frm);
    },
    document_number : function(frm) {
        if(frm.doc.document_number) {
            frappe.call({
                method: 'realestate_account.controllers.real_estate_controller.get_customer_partner',
                args: {
                    document_number: frm.doc.document_number,
                },
                callback: function(data) {
                    if (data.message) {
                        frm.clear_table('customer_partnership');
                        for (let i = 0; i < data.message.length; i++) {
                            var row = frm.add_child('customer_partnership');
                            row.customer = data.message[i].customer;
                            row.father_name = data.message[i].father_name;
                            row.id_card_no = data.message[i].id_card_no;
                            row.mobile_no = data.message[i].mobile_no;
                            row.address = data.message[i].address;
                            row.share_percentage = data.message[i].share_percentage;
                        }
                        frm.refresh_fields('customer_partnership');        
                    } else {
                        frappe.msgprint(__('Error: ') + data.exc);
                    }
                }
            });
        
        }
    },   
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
    },
    project: function(frm) {
        var project = frm.doc.project;
        if (!frm.doc.project) {
            frappe.throw(__("Please select a project."));
            return;
        }
        if (frm.prompt_opened) {
            return;
        }

        frm.cscript.project = function(doc) {
            if (doc.project !== project) {
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
                    "status": 'Booked', 'project': frm.doc.project
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
			method: "realestate_account.controllers.real_estate_controller.get_previous_document_detail",
			args: {
				plot_no: doc.plot_no
			},
			callback: function(r) {
                console.log(r);
			if (!r.exc && r.message && r.message.length > 0) {
				if (!r.exc && r.message && r.message.length > 0) {
					var name = r.message[0].name;
					var Customer = r.message[0].customer;
					var docType = r.message[0].Doc_type;
					var salesBroker = r.message[0].sales_broker;
					var salesAmount = r.message[0].sales_amount;
                    var sharePercentage = r.message[0].share_percentage;
                    var customerType = r.message[0].customer_type;
					var receivedAmount = r.message[0].received_amount;
				
					cur_frm.set_value('document_type', docType);
					cur_frm.set_value('document_number', name);
					cur_frm.set_value("sales_amount", salesAmount);
					cur_frm.set_value("received_amount", receivedAmount);
					cur_frm.set_value("final_payment", receivedAmount);
					cur_frm.set_value("sales_broker", salesBroker);
                    cur_frm.set_value("share_percentage", sharePercentage);
                    cur_frm.set_value("customer_type", customerType);
					cur_frm.set_value("customer", Customer);			  
				}
			}
		}
	});
}

function calculate_final_amount(frm) {
    var finalAmount = frm.doc.received_amount - frm.doc.deduction;
    frm.set_value("final_payment", finalAmount);
}
