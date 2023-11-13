frappe.ui.form.on('Property Transfer', {
    refresh: function (frm) {
        frm.add_custom_button(
            __("Generate Installments"),
            function () {
                frm.trigger("generate_installment");
            },
        ).addClass("btn-primary");
    },

    generate_installment: function(frm) {
        frappe.call({
            method:"generate_installment",
            doc:frm.doc,
            callback(r){
                if (r.message) {
                    r.message.sort(function(a, b) {
                        return new Date(a.date) - new Date(b.date);
                    });

                    frm.clear_table('payment_schedule');
                    $.each(r.message || [], function(i, row) {
                        frm.add_child('payment_schedule', row);
                    })
                    set_payment_plan_summary(frm);
                }
            }
        })
    },
    installment_starting_date: function(frm) {
        calculateEndingDate(frm);
    },
    no_of_month_plan: function(frm) {
        calculateEndingDate(frm);
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
            method: "realestate_account.realestate_account.doctype.property_transfer.property_transfer.get_previous_document_detail",
            args: {
                plot_no: doc.plot_no
            },
            callback: function(r) {
                if (!r.exc && r.message && r.message.length > 0) {
                    if (!r.exc && r.message && r.message.length > 0) {
                        var name = r.message[0].name;
                        var customer = r.message[0].customer;
                        var docType = r.message[0].Doc_type;
                        var salesBroker = r.message[0].sales_broker;
                        var salesAmount = r.message[0].sales_amount;
                        var receivedAmount = r.message[0].received_amount;
                        var balanceTransferAmount = salesAmount - receivedAmount
                        
                        cur_frm.set_value('document_type', docType);
                        cur_frm.set_value('document_number', name);
                        cur_frm.set_value('sales_amount', salesAmount);
                        cur_frm.set_value('received_amount', receivedAmount);
                        cur_frm.set_value("balance_transfer", balanceTransferAmount);
                        cur_frm.set_value("total_transfer_amount", balanceTransferAmount);
                        cur_frm.set_value("from_sales_broker", salesBroker);
                        cur_frm.set_value('from_customer', customer);
                        cur_frm.refresh_field('from_customer');              
                }
            }
        }
    });
}

function calculateEndingDate(frm) {
    var startingDate = frm.doc.installment_starting_date;
    var numberOfMonth = frm.doc.no_of_month_plan;

    if (startingDate && numberOfMonth) {
        var endingDate = frappe.datetime.add_months(startingDate, numberOfMonth);

        frm.set_value('installment_ending_date', endingDate);
    }
}

function set_payment_plan_summary(frm) {
    let plan_totals = {}
    let totalPaymentScheduleAmount = 0;

    $.each(frm.doc.payment_schedule || [], function(i, row) {
        if (!plan_totals[row.installment]) {
            plan_totals[row.installment] = flt(row.amount);
        } else {
            plan_totals[row.installment] += flt(row.amount);
        }
        totalPaymentScheduleAmount += flt(row.amount);
    })

    frm.set_value('difference', frm.doc.total_transfer_amount - totalPaymentScheduleAmount);

    $.each(frm.doc.payment_plan || [], function(i, row) {
        if (plan_totals[row.plan_type]) {
            row.total_amount = plan_totals[row.plan_type];
        }
    })
    frm.refresh_fields();
}

frappe.ui.form.on("Installment Payment Plan", {
    amount: function(frm, cdt, cdn) {
        set_payment_plan_summary(frm);
    },

    payment_schedule_remove: function(frm, cdt, cdn) {
        set_payment_plan_summary(frm);
    }
});

frappe.ui.form.on("Payment Plan", {
    payment_plan_add: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.start_date = frm.doc.installment_starting_date;
		row.end_date = frm.doc.installment_ending_date;
        frm.refresh_field("payment_plan");
	}
});





























frappe.ui.form.on("Property Transfer", {
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
 
