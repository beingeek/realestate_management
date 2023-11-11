frappe.ui.form.on("Plot Booking", {
    refresh: function(frm) {
        frm.fields_dict['sales_broker'].get_query = function() {
            return {
                filters: {
                    'supplier_group': 'Sales Broker'
                }
            };
        };
    }
})

frappe.ui.form.on("Plot Booking", {
    refresh: function (frm) {
        frm.add_custom_button(
            __("Generate Installments"),
            function () {
                frm.trigger("generate_installment");
            },
        ).addClass("btn-primary");
    },
   
    premium_discount: function(frm) {
        var booking_grand_total = frm.doc.unit_cost + frm.doc.premium_discount;
        frm.set_value("total_sales_amount", booking_grand_total);
        frm.set_value("booking_grand_total", booking_grand_total);
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
                    "status": 'Available', 'hold_for_sale': 0, 'project': frm.doc.project
                }
            })
        }, (values) => {
            frappe.model.set_value(frm.doctype, frm.docname, 'plot_no', values.selected_plot);
            frm.prompt_opened = false;
        }, __('Select Available Plot'));
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

        let plan_totals = {}
        let totalPaymentScheduleAmount = 0;

        frappe.call({
            method:"generate_installment",
            doc:frm.doc,
            callback(r){
                if (r.message) {
                    frm.clear_table('payment_schedule');
                    $.each(r.message || [], function(i, row) {
                        frm.add_child('payment_schedule', row);
                        if (!plan_totals[row.installment]) {
                            plan_totals[row.installment] = flt(row.amount);
                        } else {
                            plan_totals[row.installment] += flt(row.amount);
                        }
                        totalPaymentScheduleAmount += flt(row.amount);
                    })
                    frm.set_value('difference', frm.doc.total_sales_amount - totalPaymentScheduleAmount);
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
});


frappe.ui.form.on("Installment Payment Plan", {
    // amount: function(frm, cdt, cdn) {
    //     set_payment_details(frm);
    // },

    // payment_schedule_remove: function(frm, cdt, cdn) {
    //     set_payment_details(frm);
    // }
});
});

function calculateEndingDate(frm) {
    var startingDate = frm.doc.installment_starting_date;
    var numberOfMonth = frm.doc.no_of_month_plan;

    if (startingDate && numberOfMonth) {
        var endingDate = frappe.datetime.add_months(startingDate, numberOfMonth);

        frm.set_value('installment_ending_date', endingDate);
    }
}

// function set_payment_details(frm) {
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

//     let totalInstallmentAmount = totals['Monthly Installment'] + totals['Quarterly Installment'] + totals['Half Yearly Installment'] + totals['Yearly Installment'];
//     let totalPaymentScheduleAmount =  totalInstallmentAmount + frm.doc.total_booking_amount + frm.doc.total_possession_amount;
//     frm.set_value('total_monthly_installment',totals['Monthly Installment']);
//     frm.set_value('total_quarterly_installment', totals['Quarterly Installment']);
//     frm.set_value('total_half_yearly_installment', totals['Half Yearly Installment']);
//     frm.set_value('total_yearly_installment', totals['Yearly Installment']);
//     frm.set_value('total_booking_amount', totals['Booking Amount']);
//     frm.set_value('total_possession_amount', totals['Possession Amount']);
//     frm.set_value('total_installment_amount', totalInstallmentAmount);
//     frm.set_value('difference', frm.doc.total_sales_amount - totalPaymentScheduleAmount);
//     frm.refresh_fields();
// }