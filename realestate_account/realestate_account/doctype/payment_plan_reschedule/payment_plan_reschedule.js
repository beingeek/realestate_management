
frappe.ui.form.on("Payment Plan Reschedule", {
    refresh: function (frm) {
        if (frm.doc.docstatus == 0) {
           frm.add_custom_button(
                   __("Generate Installments"),
                   function () {
                       frm.trigger("generate_installment");
                   },
               ).addClass("btn-primary");
        }
       },
});

frappe.ui.form.on("Payment Plan Reschedule", { 
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
                    
                        frm.set_value('difference', frm.doc.reshedule_amount - totalPaymentScheduleAmount);
                    
                        $.each(frm.doc.payment_plan || [], function(i, row) {
                            if (plan_totals[row.plan_type]) {
                                row.total_amount = plan_totals[row.plan_type];
                            }
                        })
                        frm.refresh_fields();
                    
                }
            }
        })
    },
    
    payment_plan_template: function(frm) {
        if (!frm.doc.payment_plan_template) {
            frappe.throw(__("Please select payment plan template."));
        }
        if (!frm.doc.company) {
            frappe.throw(__("Please select company."));
        }
        frappe.call({
            method: 'realestate_account.controllers.real_estate_controller.get_payment_plan',
            args: {
                plan_template: frm.doc.payment_plan_template,
                company: frm.doc.company
            },
            callback: function(data) {
                if (data.message) {
                    frm.clear_table('payment_plan');
                    for (let i = 0; i < data.message.length; i++) {
                        var row = frm.add_child('payment_plan');
                        row.plan_type = data.message[i].plan_type;
                        row.installment_amount = data.message[i].installment_amount;
                        row.start_date = data.message[i].start_date;
                        row.end_date = data.message[i].end_date;
                        row.is_recurring = data.message[i].is_recurring;
                        row.frequency_in_months = data.message[i].frequency_in_months;
                        row.date_selection = data.message[i].date_selection;
                    }
                    frm.refresh_fields('payment_plan');        
                } else {
                    frappe.msgprint(__('Error: ') + data.exc);
                }
            }
        });
    },

    installment_starting_date:function(frm){
        if (frm.doc.payment_plan && frm.doc.payment_plan.length > 0) {
            frm.doc.payment_plan.forEach(function(row) {
                row.start_date = frm.doc.installment_starting_date;
                row.end_date = frm.doc.installment_ending_date;
            });
            frm.refresh_field("payment_plan");
        }
        let startingDate = frm.doc.installment_starting_date;
        let numberOfMonth = frm.doc.no_of_month_plan;

        if (startingDate && numberOfMonth) {
            let endingDate = frappe.datetime.add_months(startingDate, numberOfMonth);

            console.log(endingDate);
            frm.set_value('installment_ending_date', endingDate );
        }
    },
    
    no_of_month_plan: function(frm) {
        let startingDate = frm.doc.installment_starting_date;
        let numberOfMonth = frm.doc.no_of_month_plan;

        if (startingDate && numberOfMonth) {
            let endingDate = frappe.datetime.add_months(startingDate, numberOfMonth);

            console.log(endingDate);
            frm.set_value('installment_ending_date', endingDate );
        }
    },

    installment_ending_date: function(frm) {
        if (frm.doc.payment_plan && frm.doc.payment_plan.length > 0) {
            frm.doc.payment_plan.forEach(function(row) {
                row.start_date = frm.doc.installment_starting_date;
                row.end_date = frm.doc.installment_ending_date;
            });
            frm.refresh_field("payment_plan");
        }
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
                if (!r.exc && r.message && r.message.length > 0) {
                    var name = r.message[0].name;
                    var customer = r.message[0].customer;
                    var docType = r.message[0].Doc_type;
                    var salesBroker = r.message[0].sales_broker;
                    var salesAmount = r.message[0].sales_amount;
                    var receivedAmount = r.message[0].received_amount;
                    var sharePercentage = r.message[0].share_percentage;
                    var customerType = r.message[0].customer_type;
                    var balanceTransferAmount = salesAmount - receivedAmount

                    cur_frm.set_value('document_type', docType);
                    cur_frm.set_value('document_number', name);
                    cur_frm.set_value('sales_amount', salesAmount);
                    cur_frm.set_value('received_amount', receivedAmount);
                    cur_frm.set_value("balance_transfer", balanceTransferAmount);
                    cur_frm.set_value("reshedule_amount", balanceTransferAmount);
                    cur_frm.set_value('customer', customer);
                    cur_frm.refresh_fields(['document_type', 'document_number', 'sales_amount', 'received_amount', 'balance_transfer']);
                }
            },
            
        });
    },


    frappe.ui.form.on("Installment Payment Plan", {
        amount: function(frm, cdt, cdn) {
            set_payment_plan_summary(frm);
        },

        payment_schedule_remove: function(frm, cdt, cdn) {
            set_payment_plan_summary(frm);
        }
    });

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

    frappe.ui.form.on("Payment Plan", {
        payment_plan_add: function(frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            row.start_date = frm.doc.installment_starting_date;
            row.end_date = frm.doc.installment_ending_date;
            frm.refresh_field("payment_plan");
        }
    });
