frappe.ui.form.on("Plot Booking", {
	setup(frm) {
		frm.trigger("set_queries");
	},

    refresh: function (frm) {
        if (frm.doc.doc_status === 0) {
            frm.add_custom_button(
                __("Generate Installments"),
                function () {
                    frm.trigger("generate_installment");
                },
            ).addClass("btn-primary");
        }
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
	
    installment_starting_date: function(frm) {
        calculateEndingDate(frm);
        replicateDates(frm);
    },

    no_of_month_plan: function(frm) {
        calculateEndingDate(frm);
    },

    installment_ending_date: function(frm) {
        replicateDates(frm);
    },

    generate_installment: function(frm) {
        frappe.call({
            method: "generate_installment",
            doc: frm.doc,
            callback: function(r) {
                if (r.message) {
                    r.message.sort(function(a, b) {
                        return new Date(a.date) - new Date(b.date);
                    });
    
                    frm.clear_table('payment_schedule');
                    $.each(r.message || [], function(i, row) {
                        frm.add_child('payment_schedule', row);
                    });
                    set_payment_plan_summary(frm);
                }
            }
        });
    },
});


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

    frm.set_value('difference', frm.doc.total_sales_amount - totalPaymentScheduleAmount);

    $.each(frm.doc.payment_plan || [], function(i, row) {
        if (plan_totals[row.plan_type]) {
            row.total_amount = plan_totals[row.plan_type];
        }
    })
    frm.refresh_fields();
}

function replicateDates(frm) {
    if (frm.doc.payment_plan && frm.doc.payment_plan.length > 0) {
        frm.doc.payment_plan.forEach(function(row) {
            row.start_date = frm.doc.installment_starting_date;
            row.end_date = frm.doc.installment_ending_date;
        });
        frm.refresh_field("payment_plan");
    }
}
