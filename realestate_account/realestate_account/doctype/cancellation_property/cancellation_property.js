
frappe.ui.form.on('Cancellation Property', {
	project: function(frm) {
		var project = frm.doc.project;
		if (!project) {
			frappe.msgprint(__("Please select a project."));
			return;
		}

		if (frm.dialog_opened) {
			return;
		}
		frm.dialog_opened = true;
		frm.cscript.project = function(doc) {
			if (doc.project !== project) {
				frm.dialog_opened = false;
			}
		};   
		frappe.call({
			method: "realestate_account.realestate_account.doctype.cancellation_property.cancellation_property.get_plot_no",
			args: {
				project: project,
			},
			callback: function(response) {
				if (response.message) {
					console.log(response);
					var plots_with_details = response.message;

					if (plots_with_details.length === 0) {
						frm.set_value("plot_no", "");
						frappe.msgprint(__("No available plots found."));
					} else {
						var selectedPlotValue = null;
						var dialog = new frappe.ui.Dialog({
							title: __("Select Available Plot"),
							fields: [
								{
									label: __("Available Plots"),
									fieldname: "selected_plot",
									fieldtype: "Autocomplete",
									options: getAllPlotOptions(), // Initially load all plot options
									depends_on: 'eval:1',
									onchange: function () {
										selectedPlotValue = dialog.fields_dict.selected_plot.value;
									},
								},
							],
							primary_action: function () {
								if (selectedPlotValue) {
									frappe.model.set_value(frm.doctype, frm.docname, 'plot_no', selectedPlotValue);
								}
								dialog.hide();
								frm.dialog_opened = false;
							},
							primary_action_label: __("Select the Plot"),
						});
						function getAllPlotOptions() {
							return plots_with_details.map(function (plot) {
								return {
									value: plot.plot_no,
									label: `${plot.plot_no}`,
								};
							});
						}
						dialog.show();

					}
				}
			},
		});
	},
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
 



