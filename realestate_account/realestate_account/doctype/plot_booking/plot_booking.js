frappe.ui.form.on("Plot Booking", {
    refresh: function (frm) {
        frm.add_custom_button(
            __("Generate Installments"),
            function () {
                frm.trigger("generate_installment");
            },
        ).addClass("btn-primary");
    },

    project_name: function(frm) {
        var project_name = frm.doc.project_name;
        if (!frm.doc.project_name) {
            frappe.throw(__("Please select a project."));
            return;
        }
        if (frm.prompt_opened) {
            return;
        }

        frm.cscript.project_name = function(doc) {
            if (doc.project_name !== project_name) {
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
                    "status": 'Available', 'hold_for_sale': 0, 'project_name': frm.doc.project_name
                }
            })
        }, (values) => {
            frappe.model.set_value(frm.doctype, frm.docname, 'plot_no', values.selected_plot);
            frm.prompt_opened = false;
        }, __('Select Available Plot'));
    },

    premium_discount: function(frm) {
        var booking_grand_total = frm.doc.unit_cost + frm.doc.premium_discount;
        frm.set_value("total_sales_amount", booking_grand_total);
        frm.set_value("booking_grand_total", booking_grand_total);
    },

    //////// working on payment plan//////////
    installment_starting_date: function(frm) {
        calculateEndingDate(frm);
    },

    no_of_month_plan: function(frm) {
        calculateEndingDate(frm);
    },

    total_sales_amount: function(frm) {
        let total_schedule_amt = frm.doc.total_booking_amount + frm.doc.total_possession_amount + frm.doc.total_installment_amount;
        var difference = frm.doc.total_sales_amount - total_schedule_amt;
        frm.set_value('difference',difference)
        frm.refresh_field('difference');
    },

    generate_installment: function(frm) {
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

        var totalMonthlyInstallment             = 0
        var totalQuarterlyInstallment           = 0
        var totalHalfYearlyInstallment          = 0
        var totalYearlyInstallment              = 0
        var totalInstallmentAmount              = 0
        var difference                          = 0

        var quarterlyInstallmentCounter         = 1;
        var halfYearlyInstallmentCounter        = 1;
        var yearlyInstallmentCounter            = 1;

        if (!monthlyInstallment || !numberOfMonth || !startDate ) {
            frappe.msgprint(__('Please fill the Starting Date/ No of Month / Monthly Installment fields.'));
        } else if(!plotNumber || !bookingDate){
            frappe.msgprint(__('Please fill Plot Number & Booking Date fields.'));
            return;
        }

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

        totalInstallmentAmount = totalMonthlyInstallment + totalHalfYearlyInstallment + totalQuarterlyInstallment + totalYearlyInstallment

        difference = totalSalesAmount - (totalMonthlyInstallment + totalHalfYearlyInstallment + totalQuarterlyInstallment + totalYearlyInstallment + bookingAmount + possessionAmount)

        frm.set_value('total_monthly_installment',totalMonthlyInstallment)
        frm.set_value('total_quarterly_installment',totalQuarterlyInstallment)
        frm.set_value('total_half_yearly_installment',totalHalfYearlyInstallment)
        frm.set_value('total_yearly_installment',totalYearlyInstallment)
        frm.set_value('total_installment_amount',totalInstallmentAmount)
        frm.set_value('total_booking_amount',bookingAmount)
        frm.set_value('total_possession_amount',possessionAmount)
        frm.set_value('difference',difference)

        frm.refresh_fields()
    }
});


frappe.ui.form.on("Installment Payment Plan", {
    amount: function(frm, cdt, cdn) {
        set_payment_details(frm);
    },

    payment_schedule_remove: function(frm, cdt, cdn) {
        set_payment_details(frm);
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

function set_payment_details(frm) {
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

    let totalInstallmentAmount = totals['Monthly Installment'] + totals['Quarterly Installment'] + totals['Half Yearly Installment'] + totals['Yearly Installment'];
    let totalPaymentScheduleAmount =  totalInstallmentAmount + frm.doc.total_booking_amount + frm.doc.total_possession_amount;
    frm.set_value('total_monthly_installment',totals['Monthly Installment']);
    frm.set_value('total_quarterly_installment', totals['Quarterly Installment']);
    frm.set_value('total_half_yearly_installment', totals['Half Yearly Installment']);
    frm.set_value('total_yearly_installment', totals['Yearly Installment']);
    frm.set_value('total_booking_amount', totals['Booking Amount']);
    frm.set_value('total_possession_amount', totals['Possession Amount']);
    frm.set_value('total_installment_amount', totalInstallmentAmount);
    frm.set_value('difference', frm.doc.total_sales_amount - totalPaymentScheduleAmount);
    frm.refresh_fields();
}