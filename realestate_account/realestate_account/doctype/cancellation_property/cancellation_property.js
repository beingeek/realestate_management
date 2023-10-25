//////// form Validation script/////////

frappe.ui.form.on('Cancellation Property',  'validate',  function(frm) {
    if (frm.doc.doc_date > frappe.datetime.get_today()) {
            frappe.throw(__("Future posting Document date not Allowed."));
            frappe.validated = false;
    }
});


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
					var docDate = r.message[0].DocDate;
					var salesBroker = r.message[0].sales_broker;
					var docTotal = r.message[0].receivable_amount;
					var paidAmount = r.message[0].paid_amount;
				
					cur_frm.set_value('document_type', docType);
					cur_frm.set_value('document_number', name);
					cur_frm.set_value('base_doc_date', docDate);
					cur_frm.set_value('base_doc_total', docTotal);
					cur_frm.set_value("total_paid_amount", paidAmount);
					cur_frm.set_value("final_payment", paidAmount);
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
    var finalAmount = frm.doc.total_paid_amount - frm.doc.deduction;
    frm.set_value("final_payment", finalAmount);
}


/////////////////////////// update Plot master Data //////////

frappe.ui.form.on('Cancellation Property', {
    before_submit: function(frm) {
        if (frm.doc.plot_no) {
            frappe.call({
                method: "realestate_account.realestate_account.doctype.cancellation_property.cancellation_property.plot_master_data_and_document_status_update",
                args: {
                    can_pro:frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        console.log(r);
                        if (r.message === 'Success') {
                            frappe.msgprint(__("Booking Details updated in plot master Data"));
                            frm.reload_doc();
                        } else {
                            frappe.msgprint(__(r.message));
                            frappe.validated = false;
                        }
                    } else {
                        frappe.msgprint(__('Failed to post the document.'));
                        frappe.validated = false; // Prevent document submission
                    }
                }
            });
        } 
    }
});



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
 


//////////////////////// Call for create_journal_entry /////////////////////////

frappe.ui.form.on("Cancellation Property", {
    before_submit: function(frm) {
        let paidAmount = frm.doc.total_paid_amount;
        if (paidAmount !== 0) {
            frappe.call({
                method: "realestate_account.realestate_account.doctype.cancellation_property.cancellation_property.post_journal_entry",
                args: {
                    can_pro:frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        if (r.message && r.message.journal_entry) {
                            frappe.msgprint(__("Journal Entry {0} created successfully", [r.message.journal_entry]), 'Success');
                            frm.reload_doc();
                        } else {
                            frappe.msgprint(__("Error creating Journal Entry: {0}", [r.message || 'Unknown error']), 'Error');
                            frappe.validated = false; 
                        }
                    } else {
                        frappe.msgprint(__("Error creating Journal Entry.."), 'Error');
                        frappe.validated = false; 
                    }
                }
            });
        } else {
            frappe.msgprint(__("Paid amount is 0. Cannot create Journal Entry."), 'Warning');
        }
    }
});


frappe.ui.form.on("Cancellation Property", {
    validate: function(frm) {
        checkAccountingPeriodOpen(frm.doc.doc_date);
    },
    before_submit: function(frm) {
            checkAccountingPeriodOpen(frm.doc.doc_date);
    }
});
function checkAccountingPeriodOpen(postingDate) {
    frappe.call({
        method: 'realestate_account.realestate_account.doctype.cancellation_property.cancellation_property.check_accounting_period',
        args: {
            doc_date: postingDate
        },
        callback: function(response) {
            console.log(response);
            if (response.message && response.message.is_open === 1) {
                frappe.msgprint(__('The accounting period is not open. Please open the accounting period.'));
                frappe.validated = false; 
            }
        }
    });
}
