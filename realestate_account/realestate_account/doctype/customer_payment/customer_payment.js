
frappe.ui.form.on("Customer Payment",  'validate',  function(frm) {
    if (frm.doc.total_paid_amount <= 0) {
        frappe.throw('Total paid amount is less than or equal to zero')
        frappe.validated = false;
    } 
    if (frm.doc.doc_date > frappe.datetime.get_today()) {
            frappe.throw(__("Future Document date not Allowed."));
            frappe.validated = false;
    }
    if ((frm.doc.total_paid_amount ) > (frm.doc.total_remaining_balance)) {
        frappe.throw('paid amount not greater then installment amount')
        frappe.validated = false;
    }
});

frappe.ui.form.on("Customer Payment", {
    onload: function (frm) {
        frm.toggle_display(['get_insallment_information'], frm.doc.__islocal);
    },
});



frappe.ui.form.on('Customer Payment', {
    project_name: function(frm) {
            var project_name = frm.doc.project_name;
            if (!project_name) {
                frappe.msgprint(__("Please select a project."));
                return;
            }
            if (frm.dialog_opened) {
                return;
            }
            frm.dialog_opened = true;
            frm.cscript.project = function(doc) {
                if (doc.project_name !== project_name) {
                    frm.dialog_opened = false;
                }
            };   
            frappe.call({
                method: "realestate_account.realestate_account.doctype.customer_payment.customer_payment.get_plot_no",
                args: {
                    project: project_name,
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
            method: "realestate_account.realestate_account.doctype.customer_payment.customer_payment.get_plot_detail",
            args: {
                plot_no: doc.plot_no
            },
            callback: function(r) {
                console.log(r)
                if (!r.exc && r.message && r.message.length > 0) {
                    var name = r.message[0].name;
                    var docType = r.message[0].doc_type; 
                    var customer = r.message[0].customer;
                    
                    cur_frm.set_value('document_type', docType);
                    cur_frm.set_value('document_number', name);
                    cur_frm.clear_table('installment');
                    cur_frm.refresh_field('installment'); 
                    cur_frm.set_value("total_remaining_balance", 0);
                    cur_frm.refresh_fields("total_remaining_balance");
                    cur_frm.set_value("total_paid_amount", 0);
                    cur_frm.refresh_fields("total_paid_amount");
                    cur_frm.set_value("customer_name", customer );
                    cur_frm.refresh_fields("customer_name");        
                    cur_frm.set_value('payment_date', frappe.datetime.get_today()); 
                    cur_frm.refresh_fields('payment_date');
            
                }
            }
        });
    };
                
    
frappe.ui.form.on('Customer Payment', {
    get_insallment_information: function(frm, cdt, cdn) {
        let docType = frm.doc.document_type;
        let docNo = frm.doc.document_number;

        // if (!docNo) {
        //     frappe.msgprint(__('Please specify a valid document number.'));
        //     return;
        // }

        let method;
        if (docType === 'Plot Booking') {
            method = 'realestate_account.realestate_account.doctype.customer_payment.customer_payment.get_installment_list_from_booking';
        } else if (docType === 'Property Transfer') {
            method = 'realestate_account.realestate_account.doctype.customer_payment.customer_payment.get_installment_list_from_transfer';
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
                frm.clear_table('installment');
                console.log(data.message);
                let receivable_total = 0;
                for (let i = 0; i < data.message.length; i++) {
                    if (data.message[i].receivable_amount > 0) {
                        var row = frm.add_child("installment");
                        row.installment = data.message[i].Installment;
                        row.receivable_amount = data.message[i].receivable_amount;
                        row.base_doc_idx = data.message[i].idx;
                        row.date = data.message[i].date;
                        row.base_doc_no = data.message[i].name;
                        row.remaining_amount = data.message[i].receivable_amount;
                        receivable_total = receivable_total + data.message[i].receivable_amount;
                    }
                }
                frm.doc.total_remaining_balance = receivable_total;
                frm.refresh_fields("total_remaining_balance");

                frm.set_value("total_paid_amount", 0);
                frm.refresh_fields("total_paid_amount");

                frm.get_field("installment").grid.cannot_add_rows = true;
                frm.refresh_fields("installment");
            }
        });
    },
    total_paid_amount: function(frm, cdt, cdn) {
        let ptotal = frm.doc.total_paid_amount;
        let total = 0;

        frm.doc.installment.forEach(d => {
            if (ptotal > d.receivable_amount) {
                d.paid_amount = d.receivable_amount;
                ptotal = ptotal - d.receivable_amount;
            } else {
                d.paid_amount = ptotal;
                ptotal = 0;
            }

            d.remaining_amount = parseFloat(d.receivable_amount) - parseFloat(d.paid_amount);

            total = total + flt(d.paid_amount);
        });

        frm.refresh_field('installment');
        frm.doc.grand_total = total;
        frm.refresh_field('grand_total');
    }
});


frappe.ui.form.on("Customer Payment Installment", "paid_amount", function(frm, cdt, cdn) {
    let item = locals[cdt][cdn]; 
    if(item.paid_amount > item.receivable_amount)
    {
        frappe.model.set_value(cdt, cdn,'paid_amount',0) ;
        frappe.msgprint({
            title: __('Message'),
            indicator: 'green',
            message: __('paid amount is greater than receivable amount')
        });
    }
    else
    {
        let total = 0;
        frm.doc.installment.forEach(d=>{
        	total = total + parseFloat(d.paid_amount);
        	
        	frm.doc.total_paid_amount = total;
            frm.refresh_field('total_paid_amount');
        
        	frm.doc.grand_total = total;
            frm.refresh_field('grand_total');
        })
       
        let rAmount = parseFloat(item.receivable_amount) - parseFloat(item.paid_amount);
        frappe.model.set_value(cdt, cdn,'remaining_amount',rAmount) ;
    }
});


frappe.ui.form.on("Customer Payment Installment", {
    installment_remove: function(frm) {
        let total = 0;
        let receivable = 0;
        frm.doc.installment.forEach(d=>{
             total = total + flt(d.paid_amount);
             receivable = receivable + flt(d.receivable_amount);
        })
        
        frm.doc.total_remaining_balance  = receivable;
        frm.refresh_fields("total_remaining_balance");
        
        frm.doc.total_paid_amount = total;
        frm.refresh_field('total_paid_amount');
        
        frm.doc.grand_total = total;
        frm.refresh_field('grand_total');
    }
});




//////////////////////// Call for create_journal_entry /////////////////////////

frappe.ui.form.on('Customer Payment', {
    on_submit: function(frm) {
        let paidAmount = frm.doc.total_paid_amount;
        if (paidAmount !== 0) {
            frappe.call({
                method: "realestate_account.realestate_account.doctype.customer_payment.customer_payment.create_journal_entry",
                args: {
                    cust_pmt: frm.doc.name
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


//////////////////Bank Account Filter /////////////////

frappe.ui.form.on('Customer Payment', {
    refresh: function(frm) {
        frm.fields_dict['payment_type'].grid.get_field('ledger').get_query = function(doc, cdt, cdn) {
                    // Access the child object
            var child = locals[cdt][cdn];
        
                    // Your dynamic query logic based on the child object
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
 

frappe.ui.form.on('Customer Payment', {
    validate: function(frm) {
        removeUnpaidInstallments(frm);
    },
});

function removeUnpaidInstallments(frm) {
    for (let i = frm.doc.installment.length - 1; i >= 0; i--) {
        let installment = frm.doc.installment[i];
        if (installment.paid_amount === 0) {
            frm.doc.installment.splice(i, 1);
        }
    }
    frm.refresh_field('installment');
}


// frappe.ui.form.on('Customer Payment', {
//     refresh: function(frm) {
//         // Trigger the refresh event for the child table
//         frm.fields_dict['payment_type'].grid.get_field('ledger').get_query = function(doc, cdt, cdn) {
//             var child = locals[cdt][cdn];
//             if (child.mode_of_payment === 'Cash') {
//                 return {
//                     filters: {
//                         account_type: 'Cash',
//                         is_group: 0 
//                     }
//                 };
//             } else if (child.mode_of_payment === 'Cheque' || child.mode_of_payment === 'Bank Transfer') {
//                 return {
//                     filters: {
//                         account_type: 'Bank',
//                         is_group: 0 
//                     }
//                 };
//             }
//         };
//     },
    
//     // Triggered when the mode_of_payment field changes
//     mode_of_payment: function(frm, cdt, cdn) {
//         // Refresh the ledger field
//         frm.clear_field('ledger');
//     }
// });









/////////////////////////////////// Payment Type //////////////////////////////////////////////

frappe.ui.form.on("Payment Type", "amount", function(frm, cdt, cdn) {
    let item = locals[cdt][cdn]; 
    let total = 0;
    frm.doc.payment_type.forEach(d => {
        total = total + parseFloat(d.amount);
    });
    
    frm.doc.payment_type_total_amount = total;
    frm.refresh_field('payment_type_total_amount');
});



frappe.ui.form.on("Payment Type", {
    payment_type_remove: function(frm) {
        let total = 0;

        frm.doc.payment_type.forEach(d=>{
             total = total + flt(d.amount);
        })            
        frm.doc.payment_type_total_amount = total;
        frm.refresh_field('payment_type_total_amount');
    }
});

frappe.ui.form.on("Customer Payment",  'validate',  function(frm) {
    if (frm.doc.total_paid_amount !== frm.doc.payment_type_total_amount) {
        frappe.throw('Installment payment and payment type should be zero')
        frappe.validated = false;
    } 
})


frappe.ui.form.on("Payment Type", {
    onload: function(frm) {
        setTimeout(function() {
            frm.fields_dict['get_insallment_information'].$input.css({
                'background-color': 'black',
                'color': 'white'
            });
        }, 1000); 
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

frappe.ui.form.on('Customer Payment', {
    validate: function(frm) {
        checkAccountingPeriodOpen(frm.doc.payment_date);
    },
    before_submit: function(frm) {
            checkAccountingPeriodOpen(frm.doc.payment_date);
    }
});
function checkAccountingPeriodOpen(postingDate) {
    frappe.call({
        method: 'realestate_account.realestate_account.doctype.customer_payment.customer_payment.check_accounting_period',
        args: {
            payment_date: postingDate
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

frappe.ui.form.on('Customer Payment', {
    validate: function(frm) {
        if (frm.doc.book_number && frm.doc.project_name) {
            frappe.call({
                method: 'realestate_account.realestate_account.doctype.customer_payment.customer_payment.check_duplicate_book_number',
                args: {
                    'book_number': frm.doc.book_number,
                    'project': frm.doc.project_name,
                    'doc_name': frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.is_duplicate) {
                        frappe.msgprint(__('Duplicate book number found for the project. Another Customer Payment: {0}', [r.message.duplicate_payment]));
                        frm.set_value('book_number', '');
                        frappe.validated = false;
                    }
                }
            });
        }
    }
});
