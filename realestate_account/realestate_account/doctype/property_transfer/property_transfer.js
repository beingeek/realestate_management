frappe.ui.form.on("Property Transfer", {
    refresh: function(frm) {
        if (frm.doc.docstatus == 0) {
            frm.add_custom_button(__('Generate Installments'), function(){
                if (!frm.doc.plot_no) {
                    frappe.throw({
                        title: __("Mandatory"),
                        message: __("Please Select a Plot No")
                    });
                } else {
                    frm.trigger("generate_installment");
                }
            }, __("Action"));
            frm.add_custom_button(__('Get Existing Schedule'), function(){
                if (!frm.doc.plot_no) {
                    frappe.throw({
                        title: __("Mandatory"),
                        message: __("Please Select a Plot No")
                    });
                } else {
                    frm.trigger("get_existing_schedule");
                }    
            }, __("Action"));
        }
    },
});

frappe.ui.form.on("Property Transfer", {
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

    payment_schedule_type:function(frm) {
        frm.clear_table('payment_schedule');
        frm.clear_table('payment_plan');
        frm.set_value('installment_starting_date', "");
        frm.set_value('no_of_month_plan', 0);
    },
    
    generate_installment: function(frm) {
        if (frm.doc.payment_schedule_type !== "Generate New Payment Schedule") {
            frappe.throw(__("Please change the payment Schedule type."));
        }
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
                    
                        frm.set_value('difference', frm.doc.total_transfer_amount - totalPaymentScheduleAmount);
                    
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
    document_number : function(frm) {
        if(frm.doc.document_number) {
            frappe.call({
                method: 'realestate_account.controllers.real_estate_controller.get_customer_partner',
                args: {
                    document_number: frm.doc.document_number,
                },
                callback: function(data) {
                    if (data.message) {
                        frm.clear_table('from_customer_partnership');
                        for (let i = 0; i < data.message.length; i++) {
                            var row = frm.add_child('from_customer_partnership');
                            row.customer = data.message[i].customer;
                            row.father_name = data.message[i].father_name;
                            row.id_card_no = data.message[i].id_card_no;
                            row.mobile_no = data.message[i].mobile_no;
                            row.address = data.message[i].address;
                            row.share_percentage = data.message[i].share_percentage;
                        }
                        frm.refresh_fields('from_customer_partnership');        
                    } else {
                        frappe.msgprint(__('Error: ') + data.exc);
                    }
                }
            });
        
        }
    },  
   
    get_existing_schedule: function(frm) {
        if (frm.doc.payment_schedule_type !== "Generate Existing Payment Schedule") {
            frappe.throw(__("Please change the payment Schedule type."));
        }
        let docType = frm.doc.document_type;
        let docNo = frm.doc.document_number;

        let method;
        if (docType === 'Plot Booking') {
            method = 'realestate_account.realestate_account.doctype.property_transfer.property_transfer.get_payment_list_from_booking_document';
        } else if (docType === 'Property Transfer') {
            method = 'realestate_account.realestate_account.doctype.property_transfer.property_transfer.get_payment_list_from_transfer_document';
        } else {
            frappe.msgprint(__('Invalid document type.'));
            return;
        }

        frappe.call({
            method: method,
            args: {
                doc_type: docType,
                doc_no: docNo
            },
            callback: function(data) {
                if (data.message) {
                    console.log(data.message);
                    frm.clear_table('payment_schedule');
                    for (let i = 0; i < data.message.length; i++) {
                        var row = frm.add_child('payment_schedule');
                        row.date = data.message[i].date;
                        row.amount = data.message[i].receivable_amount;
                        row.installment = data.message[i].installment;
                        row.installment_name = data.message[i].installment_name;
                        row.remarks = data.message[i].remarks;
                    }
                    frm.refresh_fields('payment_schedule');        
                } else {
                    frappe.msgprint(__('Error: ') + data.exc);
                }
            }
        });
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
                    cur_frm.set_value("total_transfer_amount", balanceTransferAmount);
                    cur_frm.set_value("from_sales_broker", salesBroker);
                    cur_frm.set_value('from_customer', customer);
                    cur_frm.set_value("from_share_percentage", sharePercentage);
                    cur_frm.set_value('from_customer_type', customerType);
                    cur_frm.refresh_fields(['document_type', 'document_number', 'sales_amount', 'received_amount', 'balance_transfer', 
                    'total_transfer_amount', 'from_sales_broker', 'from_customer', 'from_share_percentage', 'from_customer_type']);
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
