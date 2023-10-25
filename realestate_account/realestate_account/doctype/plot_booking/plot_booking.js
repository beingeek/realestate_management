frappe.ui.form.on('Plot Booking', 'validate', function(frm) {
    if (frm.doc.difference !== 0) {
        frappe.msgprint(__('Amount of Installment Total and Grand Total is not matched'));
        frappe.validated = false;
    }

    if (frm.doc.booking_date > frappe.datetime.get_today()) {
        frappe.msgprint(__('Future booking date not allowed.'));
        frappe.validated = false;
    }

    frm.doc.payment_schedule.forEach(d => {
        if (parseFloat(d.amount) <= 0) {
            frappe.msgprint(__('Please remove 0 Amount Row in Payment Schedule'));
            frappe.validated = false;
        }
    });
});

frappe.ui.form.on('Plot Booking', {
    onload: function (frm) {
        frm.toggle_display(['generate_installment'], frm.doc.__islocal);
    }
});



///////////////////////////Plot Master Data Update Script//////////////////////////////////////////////

frappe.ui.form.on('Plot Booking', {
    on_submit: function(frm) {
        if (frm.doc.plot_no) {
            frappe.call({
                method: "realestate_account.realestate_account.doctype.plot_booking.plot_booking.update_after_submit",
                args: {
                    plot_booking_name: frm.doc.name
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
    },
    after_cancel: function(frm) {
        if (frm.doc.plot_no) {
            frappe.call({
                method: "realestate_account.realestate_account.doctype.plot_booking.plot_booking.update_after_cancel",
                args: {
                    plot_booking_name: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        console.log(r);
                        frappe.msgprint(__('ownership detail removed..'));
                    } else {
                        frappe.msgprint(__('Failed to remove the detail.'));
                    }
                }
            });
        }
    }
});

frappe.ui.form.on("Plot Booking", {
    project_name: function(frm) {
        var project_name = frm.doc.project_name;
        if (!project_name) {
            frappe.msgprint(__("Please select a project."));
            
        }
    },
    plot_no: function(frm) {
        refresh_plot_feature(frm);
        }
    });
        function refresh_plot_feature(frm) {
            frappe.call({
                method: "realestate_account.realestate_account.doctype.plot_booking.plot_booking.get_plot_detail",
                args: {
                    plot_no: frm.doc.plot_no
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('land_price', r.message.land_price);
                        frm.set_value('plot_feature', r.message.plot_feature);
                        frm.set_value('area', r.message.land_area);
                        frm.set_value('uom', r.message.uom);
                        frm.set_value('unit_cost', r.message.total_unit_value);
                        frm.set_value('booking_grand_total', r.message.total_unit_value);
                        frm.set_value('total_sales_amount', r.message.total_unit_value);
                    }
                }
            });
        }

frappe.ui.form.on('Plot Booking', {
    premium_discount: function(frm) {
        calculate_booking_grand_total(frm);
    }
});

function calculate_booking_grand_total(frm) {
    var booking_grand_total = frm.doc.unit_cost + frm.doc.premium_discount;
    frm.set_value("total_sales_amount", booking_grand_total);
    frm.set_value("booking_grand_total", booking_grand_total);
}

//////// working on payment plan//////////

frappe.ui.form.on('Plot Booking', {
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
    total_sales_amount: function(frm) {
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

frappe.ui.form.on('Plot Booking', {
    onload: function(frm) {
        setTimeout(function() {
            frm.fields_dict['generate_installment'].$input.css({
                'background-color': 'black',
                'color': 'white'
            });
        }, 1000); 
    }
});


frappe.ui.form.on('Plot Booking', {
    generate_installment: function(frm) {
        frm.fields_dict['generate_installment'].$input.css({
            'background-color': 'blue',
            'color': 'white'
        });
            var numberOfMonth           = frm.doc.no_of_month_plan;
            var startDate               = frm.doc.installment_starting_date;
            var bookingDate             = frm.doc.booking_date;
            var bookingAmount           = (frm.doc.booking_amount) ?? 0 ;
            var possessionAmount        = (frm.doc.possession_amount) ?? 0; 
            var monthlyInstallment      = (frm.doc.monthly_installment_amount) ?? 0;
            var quarterlyInstallment    = (frm.doc.quarterly_installment_amount) ?? 0;
            var halfYearlyInstallment   = (frm.doc.half_yearly_installment_amount) ?? 0;
            var yearlyInstallment       = (frm.doc.yearly_installment_amount) ?? 0;
            var plotNumber              = frm.doc.plot_no;
            var totalSalesAmount        = (frm.doc.total_sales_amount) ?? 0; 

            if (!monthlyInstallment || !numberOfMonth || !startDate ) {
                frappe.msgprint(__('Please fill the Starting Date/ No of Month / Monthly Installment fields.'));
            } else if(!plotNumber || !bookingDate){
                frappe.msgprint(__('Please fill Plot Number & Booking Date fields.'));
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

frappe.ui.form.on("Installment Payment Plan", "amount", function(frm, cdt, cdn) {
    
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

    frm.doc.total_quarterly_installment = totals['Quarterly Installment'];
    frm.refresh_field('total_quarterly_installment');

    frm.doc.total_half_yearly_installment = totals['Half Yearly Installment'];
    frm.refresh_field('total_half_yearly_installment');

    frm.doc.total_monthly_installment = totals['Monthly Installment'];
    frm.refresh_field('total_monthly_installment');
  
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
});

frappe.ui.form.on("Plot Booking", {
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

        frm.cscript.project_name = function(doc) {
            if (doc.project_name !== project_name) {
                frm.dialog_opened = false;
            }
        };

        frappe.call({
            method: "realestate_account.realestate_account.doctype.plot_booking.plot_booking.get_available_plots",
            args: {
                project_name: project_name,
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
                                    label: `${plot.plot_no} - ${plot.land_price} - ${plot.plot_feature}`,
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


////////////////////////////////   Create A/P invoice & plot Status Check & Accounting Period Check///////////////////////////

frappe.ui.form.on('Plot Booking', {
        on_submit: function(frm) {
            if ((frm.doc.commission_amount ?? 0)!== 0) {
            frappe.call({
            method: "realestate_account.realestate_account.doctype.plot_booking.plot_booking.create_invoice",
            args: {
                plot_booking: frm.doc.name,
            },
            callback: function(r) {
                if (!r.exc) {
                       console.log(r);
                    if (r.message && r.message.invoice) {
                        frappe.msgprint({
                            message: r.message.message,  
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            message: __(r.message || 'Error creating Purchase Invoice'),
                            indicator: 'red'
                        });
                        frappe.validated = false; 
                    }
                } else {
                    frappe.msgprint({
                        message: __('Error creating Purchase Invoice..'),
                        indicator: 'red'
                    });
                    frappe.validated = false; 
                }
            }
                            
        });
    }
},
    before_submit: function(frm) {
        if (frm.doc.plot_no) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Plot List',
                    filters: {name: frm.doc.plot_no },
                    fieldname: 'status'
                },
                callback: function(response) {
                    if (response.message) {
                        console.log(response);
                        var status = response.message.status;
                        
                        if (status === 'Booked') {
                            frappe.msgprint(__('The plot no you try to booking is already booked'));
                            frappe.validated = false; 
                        }
                    }
                }
            });
        };
    },
    before_submit: function(frm) {
            if (frm.doc.commission_amount !== 0) {
                checkAccountingPeriodOpen(frm.doc.booking_date);
            }
        }
    });
    function checkAccountingPeriodOpen(postingDate) {
        frappe.call({
            method: 'realestate_account.realestate_account.doctype.plot_booking.plot_booking.check_accounting_period_open',
            args: {
                booking_date: postingDate
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
    













