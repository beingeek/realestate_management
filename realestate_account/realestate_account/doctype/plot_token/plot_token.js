frappe.ui.form.on("Plot Token", {
	setup(frm) {
		frm.trigger("set_queries");
	},

	set_queries(frm) {
		frm.set_query("sales_broker", function(frm) {
            return {
                filters: {
                    'supplier_group': 'Sales Broker'
                }
            };
		});
        frm.set_query("return_token_number", function(frm) {
            return {
                filters: {
                    'status': 'Active',
                    'is_return': 0,
                    "docstatus":1,
                }
            };
		});
	},
    deduction: function(frm) {
        calculate_final_amount(frm);
    },
    return_token_number: function(frm) {
        if (frm.doc.return_token_number) {
            frappe.call({
                method: 'realestate_account.realestate_account.doctype.plot_token.plot_token.get_token_detail',
                args: {
                    return_token_number: frm.doc.return_token_number,
                },
                callback: function(data) {
                    if (data.message) {
                        frm.set_value('customer', data.message.customer);
                        frm.set_value('project', data.message.project);
                        frm.set_value('plot_no', data.message.plot_no);
                        frm.set_value('token_amount', data.message.token_amount);
                        frm.set_value('paid_to_customer', data.message.token_amount);
                        frm.set_value('sales_broker', data.message.sales_broker);
                        frm.set_value('term_and_conditions', data.message.term_and_conditions);
                    } else {
                        frappe.msgprint(__('Error: ') + data.exc);
                    }
                }
            });
        }
    },
    project: function(frm) {
        var project = frm.doc.project;
        if (frm.doc.is_return === 0) {
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
                        "status": 'Available', 'hold_for_sale': 0, 'project': frm.doc.project
                    }
                })
            }, (values) => {
                frappe.model.set_value(frm.doctype, frm.docname, 'plot_no', values.selected_plot);
                frm.prompt_opened = false;
            }, __('Select Available Plot'));
        }
    }    
});

function calculate_final_amount(frm) {
    var finalAmount = frm.doc.token_amount - frm.doc.deduction;
    frm.set_value("paid_to_customer", finalAmount);
}

