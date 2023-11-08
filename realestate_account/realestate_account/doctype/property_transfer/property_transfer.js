
frappe.ui.form.on('Property Transfer', {
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
                console.log(r)
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
    refresh: function (frm) {
        frm.add_custom_button(
            __("Generate Installments"),
            function () {
                frm.trigger("generate_installment");
            },
        ).addClass("btn-primary");
    },
    generate_installment: function(frm) {
            var numberOfMonth           = frm.doc.no_of_month_plan;
            var startDate               = frm.doc.installment_starting_date;
            var bookingDate             = frm.doc.posting_date;
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
            var quarterlyInstallmentCounter         = 1; 
            var halfYearlyInstallmentCounter        = 1; 
            var yearlyInstallmentCounter            = 1; 



            frm.clear_table('payment_schedule');

            if (bookingAmount  > 0) {
                frm.add_child('payment_schedule', {   
                    installment: 'Booking Amount',
                    date:bookingDate,
                    amount: bookingAmount,
                    installment_name : 'Booking Amount'
                });
            }

            for (var i = 0; i < numberOfMonth; i++) {
                if (monthlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Monthly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: monthlyInstallment,
                        installment_name: `Monthly Installment - ${i + 1}`
                    });
                    totalMonthlyInstallment = totalMonthlyInstallment + monthlyInstallment 
                }
  
                if (i >= 2 && (i - 2) % 3 === 0 && quarterlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Quarterly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: quarterlyInstallment,
                        installment_name :`Quarterly Installment - ${quarterlyInstallmentCounter }`   
                    });
                    totalQuarterlyInstallment = totalQuarterlyInstallment + quarterlyInstallment;
                    quarterlyInstallmentCounter ++;
                }
                
                if (i >= 5 && (i - 5) % 6 === 0 && halfYearlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Half Yearly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: halfYearlyInstallment,
                        installment_name :`Half Yearly Installment - ${halfYearlyInstallmentCounter}`
                    });
                    totalHalfYearlyInstallment = totalHalfYearlyInstallment + halfYearlyInstallment;
                    halfYearlyInstallmentCounter ++;
                }
   
                if (i >= 11 && (i - 11) % 12 === 0 && yearlyInstallment > 0) {
                    frm.add_child('payment_schedule', {   
                        installment: 'Yearly Installment',
                        date: frappe.datetime.add_months(startDate, i),
                        amount: yearlyInstallment,
                        installment_name :`Yearly Installment - ${yearlyInstallmentCounter }`  
                    });
                    totalYearlyInstallment = totalYearlyInstallment + yearlyInstallment
                    yearlyInstallmentCounter ++;
                }
  
            }
            
            if (possessionAmount   > 0) {
                frm.add_child('payment_schedule', {   
                    installment: 'Possession Amount',
                    date:frappe.datetime.add_months(startDate, numberOfMonth),
                    amount: possessionAmount,
                    installment_name : 'Possession Amount'  
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
 
