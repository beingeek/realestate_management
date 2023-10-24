

 ///////// form Validation script/////////

frappe.ui.form.on('Property Transfer',  'validate',  function(frm) {
    if (frm.doc.from_customer === frm.doc.to_customer) {
        frappe.msgprint(('From Customer and To Customer cannot be the same.'));
        frappe.validated = false;
    }
    if (frm.doc.total_transfer_amount === 0) {
        frappe.msgprint(__('The Transfer amount should not zero'));
        frappe.validated = false;
    } 
    if (frm.doc.doc_date > frappe.datetime.get_today()) {
            frappe.throw(__("Future posting Document date not Allowed."));
            frappe.validated = false;
    }
    if (frm.doc.difference !== 0) {
        frappe.throw('Difference field should be zero')
        frappe.validated = false;
    }
    if (frm.doc.transfer_charge !== frm.doc.payment_type_total_amount) {
        frappe.throw("Transfer Charge & Payment type total Should be equal")
        frappe.validated = false;
    } 
    if (frm.doc.__islocal && !frm.doc.plot_no) {
        frappe.msgprint(__('Please enter a plot number before saving the document.'));
        frappe.validated = false;
    }
});

frappe.ui.form.on('Property Transfer', {
    onload: function (frm) {
        frm.toggle_display(['generate_installment'], frm.doc.__islocal);
    }
});




// frappe.ui.form.on('Property Transfer', {
//     validate: function(frm) {
//         if (!frm.doc.plot_no) {
//              frappe.call({
//                 method: 'realestate_account.realestate_account.doctype.property_transfer.property_transfer.validate_plot_no_on_client',
//                 args: {
//                     plot_no: frm.doc.plot_no
//                 },
//                 callback: function(r) {
//                     if (r.message && r.message.error) {
//                         frappe.msgprint(__(r.message.error));
//                         frappe.validated = false;
//                     }
//                     // Additional client-side logic if needed
//                 }
//             });
//         }
//     }
// });





//////Get plot_no Based on Project

frappe.ui.form.on('Property Transfer', {
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
                method: "realestate_account.realestate_account.doctype.property_transfer.property_transfer.get_plot_no",
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
            method: "realestate_account.realestate_account.doctype.property_transfer.property_transfer.get_previous_document_detail",
            args: {
                plot_no: doc.plot_no
            },
            callback: function(r) {
                console.log(r)
                if (!r.exc && r.message && r.message.length > 0) {
                    if (!r.exc && r.message && r.message.length > 0) {
                        var name = r.message[0].name;
                        var customer = r.message[0].customer;
                        var docType = r.message[0].Doc_type;
                        var docDate = r.message[0].DocDate;
                        var salesBroker = r.message[0].sales_broker;
                        var docTotal = r.message[0].receivable_amount;
                        var paidAmount = r.message[0].paid_amount;
                        var updateTotal = docTotal - paidAmount
                    
                        cur_frm.set_value('document_type', docType);
                        cur_frm.set_value('document_number', name);
                        cur_frm.set_value('base_doc_date', docDate);
                        cur_frm.set_value('base_doc_total', docTotal);
                        cur_frm.set_value('paid_amount', paidAmount);
                        cur_frm.set_value("transfer_amount", updateTotal);
                        cur_frm.set_value("total_transfer_amount", updateTotal);
                        cur_frm.set_value("from_sales_broker", salesBroker);
                        cur_frm.set_value('from_customer', customer);
                        cur_frm.refresh_field('from_customer');

                       
                }
            }
        }
    });
}


//////////// (update & reversal) Plot Booking document Status & Plot Master Data  ////////////////////////////////////////////////

frappe.ui.form.on('Property Transfer', {
    before_submit: function(frm) {
        if (frm.doc.document_number) {
        
        let docType = frm.doc.document_type;
        
        let method;
        if (docType === 'Plot Booking') {
            method = 'realestate_account.realestate_account.doctype.property_transfer.property_transfer.plot_master_data_booking_document_status_update';
        } else if (docType === 'Property Transfer') {
            method = 'realestate_account.realestate_account.doctype.property_transfer.property_transfer.plot_master_data_transfer_document_status_update';
        } else {
            frappe.msgprint(__('Invalid document type.'));
            return;
        }

        frappe.call({
            method: method,
            args: {
                transfer:frm.doc.name
            },
            callback: function(r) {
                if (!r.exc) {
                    if (r.message === 'Success') {
                        frappe.msgprint(__("Plot Master Data & Booking document status updated"));
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
},
    before_cancel: function(frm) {
        if (frm.doc.document_number) {
            let docType = frm.doc.document_type;
        
            let method;
            if (docType === 'Plot Booking') {
                method = 'realestate_account.realestate_account.doctype.property_transfer.property_transfer.plot_master_data_booking_document_status_update_reversal';
            } else if (docType === 'Property Transfer') {
                method = 'realestate_account.realestate_account.doctype.property_transfer.property_transfer.plot_master_data_transfer_document_status_update_reversal';
            } else {
                frappe.msgprint(__('Invalid document type.'));
                return;
            }

            frappe.call({
                method: method,
                args: {
                    transfer:frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        console.log(r);
                        if (r.message === 'Success') {
                            frappe.msgprint(__("Reversal of Plot Master Data & Booking document status updated"));
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


//////////////////Payment Schedule ////////////////////////////////////////////

frappe.ui.form.on('Property Transfer', {
    installment_starting_date: function(frm) {
        calculateEndingDate(frm);
    },
    no_of_month_plan: function(frm) {
        calculateEndingDate(frm);
    }
});
function calculateEndingDate(frm) {
    var startingDate = frm.doc.installment_starting_date;
    var numberOfMonth = frm.doc.no_of_month_plan;

    if (startingDate && numberOfMonth) {
        var endingDate = frappe.datetime.add_months(startingDate, numberOfMonth);

        frm.set_value('installment_ending_date', endingDate);
    }
}

frappe.ui.form.on('Property Transfer', {
    adjustment: function(frm) {
        calculate_transfer_amount(frm);
    }
});

function calculate_transfer_amount(frm) {
    var totalTransferAmount = frm.doc.base_doc_total + frm.doc.adjustment;
    frm.set_value("total_transfer_amount", totalTransferAmount);
    frm.set_value("transfer_amount", totalTransferAmount);
}

frappe.ui.form.on('Plot Booking', {
    total_transfer_amount: function(frm) {
        calculateDifference(frm);
    }
});
function calculateDifference(frm) {
    var totalBookingAmount      = (frm.doc.total_booking_amount) ?? 0 ;
    var totalPossessionAmount   = (frm.doc.total_possession_amount) ?? 0;
    var totalInstallmentAmount  = (frm.doc.total_installment_amount) ?? 0; 
    var totalSalesAmount        = (frm.doc.total_sales_amount) ?? 0; 

    var difference              = totalSalesAmount - (totalBookingAmount+totalInstallmentAmount+totalPossessionAmount)
    
    frm.set_value('difference',difference)
    frm.refresh_field('difference');
    
}

frappe.ui.form.on('Property Transfer', {
    generate_installment: function(frm) {
        frm.fields_dict['generate_installment'].$input.css({
            'background-color': 'blue',
            'color': 'white'
        });
            var numberOfMonth           = frm.doc.no_of_month_plan;
            var startDate               = frm.doc.installment_starting_date;
            var bookingDate             = frm.doc.doc_date;
            var bookingAmount           = (frm.doc.booking_amount) ?? 0 ;
            var possessionAmount        = (frm.doc.possession_amount) ?? 0; 
            var monthlyInstallment      = (frm.doc.monthly_installment_amount) ?? 0;
            var quarterlyInstallment    = (frm.doc.quarterly_installment_amount) ?? 0;
            var halfYearlyInstallment   = (frm.doc.half_yearly_installment_amount) ?? 0;
            var yearlyInstallment       = (frm.doc.yearly_installment_amount) ?? 0;
            var plotNumber              = frm.doc.plot_no;
            var totalSalesAmount        = (frm.doc.total_transfer_amount) ?? 0; 

            if (!monthlyInstallment || !numberOfMonth || !startDate ) {
                frappe.msgprint(__('Please fill the Starting Date/ No of Month / Monthly Installment fields.'));
            } else if(!plotNumber || !bookingDate){
                frappe.msgprint(__('Please fill Plot Number & Doc Date fields.'));
                return;
            }
                    
            frm.clear_table('payment_schedule');
          
            var totalMonthlyInstallment             = 0
            var totalQuarterlyInstallment           = 0
            var totalHalfYearlyInstallment          = 0
            var totalYearlyInstallment              = 0
            var totalInstallmentAmount              = 0
            var difference                          = 0

            frm.clear_table('payment_schedule');

            if (bookingAmount  > 0) {
                frm.add_child('payment_schedule', {   
                    installment: 'Booking Amount',
                    date:bookingDate,
                    amount: bookingAmount 
                });
            }

            for (var i = 0; i < numberOfMonth; i++) {
                if (monthlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Monthly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: monthlyInstallment
                    });
                    totalMonthlyInstallment = totalMonthlyInstallment + monthlyInstallment 
                }

                if (i >= 2 && (i - 2) % 3 === 0 && quarterlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Quarterly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: quarterlyInstallment
                    });
                    totalQuarterlyInstallment = totalQuarterlyInstallment + quarterlyInstallment
                }

                if (i >= 5 && (i - 5) % 6 === 0 && halfYearlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Half Yearly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: halfYearlyInstallment
                    });
                    totalHalfYearlyInstallment = totalHalfYearlyInstallment + halfYearlyInstallment
                }
   
                if (i >= 11 && (i - 11) % 12 === 0 && yearlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Yearly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: yearlyInstallment
                    });
                    totalYearlyInstallment = totalYearlyInstallment + yearlyInstallment
                }
            }
            
            if (possessionAmount   > 0) {
                frm.add_child('payment_schedule', {   
                    installment: 'Possession Amount',
                    date:frappe.datetime.add_months(startDate, numberOfMonth),
                    amount: possessionAmount  
                });
            }          

            totalInstallmentAmount = totalMonthlyInstallment + totalHalfYearlyInstallment + totalQuarterlyInstallment 
                                    + totalYearlyInstallment
                                    
            difference = totalSalesAmount - (totalMonthlyInstallment + totalHalfYearlyInstallment + totalQuarterlyInstallment 
                                            + totalYearlyInstallment + bookingAmount + possessionAmount)

            frm.refresh_field('payment_schedule');

            frm.set_value('total_monthly_installment',totalMonthlyInstallment)
            frm.refresh_field('total_monthly_installment');

            frm.set_value('total_quarterly_installment',totalQuarterlyInstallment)
            frm.refresh_field('total_quarterly_installment');

            frm.set_value('total_half_yearly_installment',totalHalfYearlyInstallment)
            frm.refresh_field('total_half_yearly_installment');
            
            frm.set_value('total_yearly_installment',totalYearlyInstallment)
            frm.refresh_field('total_yearly_installment');
            
            frm.set_value('total_installment_amount',totalInstallmentAmount)
            frm.refresh_field('total_installment_amount');

            frm.set_value('total_booking_amount',bookingAmount)
            frm.refresh_field('total_booking_amount');

            frm.set_value('total_possession_amount',possessionAmount)
            frm.refresh_field('total_possession_amount');

            frm.set_value('difference',difference)
            frm.refresh_field('difference');
            
        }
    });

frappe.ui.form.on("Installment Payment Plan", {
    payment_schedule_remove: function(frm, cdt, cdn) {
                
        let totals = {
            'Booking Amount': 0,
            'Monthly Installment': 0,
            'Quarterly Installment': 0,
            'Half Yearly Installment': 0,
            'Yearly Installment': 0,
            'Possession Amount': 0,
        };

        frm.doc.payment_schedule.forEach(d => {
            let type = d.installment;
            totals[type] += flt(d.amount);
        });

        frm.doc.total_monthly_installment = totals['Monthly Installment'];
        frm.refresh_field('total_monthly_installment');

        frm.doc.total_quarterly_installment = totals['Quarterly Installment'];
        frm.refresh_field('total_quarterly_installment');
    
        frm.doc.total_half_yearly_installment = totals['Half Yearly Installment'];
        frm.refresh_field('total_half_yearly_installment');
      
        frm.doc.total_yearly_installment = totals['Yearly Installment'];
        frm.refresh_field('total_yearly_installment');

        frm.doc.total_booking_amount = totals['Booking Amount'];
        frm.refresh_field('total_booking_amount');

        frm.doc.total_possession_amount = totals['Possession Amount'];
        frm.refresh_field('total_possession_amount');
        
        let totalInstallmentAmount = totals['Monthly Installment'] +
                                     totals['Quarterly Installment'] +
                                     totals['Half Yearly Installment'] +
                                     totals['Yearly Installment'];

        frm.doc.total_installment_amount = totalInstallmentAmount;
        frm.refresh_field('total_installment_amount');
        
        let totalSalesAmount = (frm.doc.total_sales_amount) ?? 0;
        let totalPaymentScheduleAmount = totals['Monthly Installment'] +
                                         totals['Quarterly Installment'] +
                                         totals['Half Yearly Installment'] +
                                         totals['Yearly Installment'] +
                                         totals['Booking Amount'] +
                                         totals['Possession Amount'];
    
        frm.doc.difference = totalSalesAmount - totalPaymentScheduleAmount;
        frm.refresh_field('difference');
        
    }
});


////////////////////// Call for create_journal_entry /////////////////////////

frappe.ui.form.on('Property Transfer', {
    on_submit: function(frm) {
        let paidAmount = frm.doc.paid_amount;
        let transferAmount = frm.doc.transfer_charge;
        if (paidAmount !== 0 || transferAmount !== 0) {                
            frappe.call({
            method: "realestate_account.realestate_account.doctype.property_transfer.property_transfer.create_journal_entry",
            args: {
                property_transfer: frm.doc.name
            },
            callback: function(r) {
                if (!r.exc) {
                    console.log(r);
                    if (r.message && r.message.journal_entry) {
                        frappe.msgprint({
                            message: r.message.message,  
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            message: __(r.message || 'Error creating Journal Entry'),
                            indicator: 'red'
                        });
                        frappe.validated = false; 
                    }
                } else {
                    frappe.msgprint({
                        message: __('Error creating Journal Entry..'),
                        indicator: 'red'
                    });
                    frappe.validated = false; 
                }
            }
                            
        });
    }
}
});


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
 



// frappe.ui.form.on('Property Transfer', {
//     refresh: function(frm) {
//         var last_plot_no = '';
//         frm.fields_dict['project'].$input.on('change', function() {
//             var current_plot_no = frm.doc.plot_no;
//             if (current_plot_no !== last_plot_no) {
//                 frm.set_value('project', '');
//                 frm.refresh_field('project');
//                 last_plot_no = current_plot_no;
//             }
//         });
//     }
// });

//////////////////Bank Account Filter /////////////////

// frappe.ui.form.on('Property Transfer', {
//     mode_of_payment: function(frm) {
//         frm.trigger('refresh_account');
//     },
//     refresh_account: function(frm) {
//         if (frm.doc.mode_of_payment === 'Cash') {
//             frm.set_value('payment_ledger', ''); 
//             frm.set_query('payment_ledger', function() {
//                 return {
//                     filters: {
//                         account_type: 'Cash',
//                         is_group: 0  
//                     }
//                 };
//             });
//         } else if (frm.doc.mode_of_payment === 'Cheque' ||frm.doc.mode_of_payment === 'Bank Transfer') {
//             frm.set_value('payment_ledger', ''); 
//             frm.set_query('payment_ledger', function() {
//                 return {
//                     filters: {
// 						account_type: 'Bank',
//                         is_group: 0  
//                     }
//                 };
//             });
//         }
//     }
// });




// frappe.ui.form.on("Installment Payment Plan", "amount", function(frm, cdt, cdn) {
    
//     let totals = {
//         'Booking Amount': 0,
//         'Monthly Installment': 0,
//         'Quarterly Installment': 0,
//         'Half Yearly Installment': 0,
//         'Yearly Installment': 0,
//         'Possession Amount': 0,
//     };

//     frm.doc.payment_schedule.forEach(d => {
//         let type = d.installment;
//         totals[type] += flt(d.amount);
//     });

//     frm.doc.total_quarterly_installment = totals['Quarterly Installment'];
//     frm.refresh_field('total_quarterly_installment');

//     frm.doc.total_half_yearly_installment = totals['Half Yearly Installment'];
//     frm.refresh_field('total_half_yearly_installment');

//     frm.doc.total_monthly_installment = totals['Monthly Installment'];
//     frm.refresh_field('total_monthly_installment');
  
//     frm.doc.total_yearly_installment = totals['Yearly Installment'];
//     frm.refresh_field('total_yearly_installment');

//     frm.doc.total_booking_amount = totals['Booking Amount'];
//     frm.refresh_field('total_booking_amount');

//     frm.doc.total_possession_amount = totals['Possession Amount'];
//     frm.refresh_field('total_possession_amount');

//     let totalInstallmentAmount = totals['Monthly Installment'] +
//                                  totals['Quarterly Installment'] +
//                                  totals['Half Yearly Installment'] +
//                                  totals['Yearly Installment'];

//     frm.doc.total_installment_amount = totalInstallmentAmount;
//     frm.refresh_field('total_installment_amount');
    
//     let totalSalesAmount = (frm.doc.total_sales_amount) ?? 0;
//     let totalPaymentScheduleAmount = totals['Monthly Installment'] +
//                                     totals['Quarterly Installment'] +
//                                     totals['Half Yearly Installment'] +
//                                     totals['Yearly Installment'] +
//                                     totals['Booking Amount'] +
//                                     totals['Possession Amount'];
    
//     frm.doc.difference = totalSalesAmount - totalPaymentScheduleAmount;
//     frm.refresh_field('difference');
// });





