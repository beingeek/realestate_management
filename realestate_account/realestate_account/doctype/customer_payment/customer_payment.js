
frappe.ui.form.on("Customer Payment", {
    onload: function (frm) {
        frm.toggle_display(['get_insallment_information'], frm.doc.__islocal);
    }
}),

frappe.ui.form.on('Customer Payment', {
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
                    "status": 'Booked', 'project_name': frm.doc.project_name
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
                    var address = r.message[0].address;
                    var sales_amount = r.message[0].sales_amount;
                    var received_amount = r.message[0].received_amount
                    var remaining_amount = sales_amount-received_amount

                    cur_frm.set_value('document_type', docType);
                    cur_frm.set_value('document_number', name);
                    cur_frm.clear_table('installment');
                    cur_frm.refresh_field('installment'); 
                    cur_frm.set_value("total_paid_amount", 0);
                    cur_frm.refresh_fields("total_paid_amount");
                    cur_frm.set_value("sales_amount", sales_amount );
                    cur_frm.refresh_fields("sales_amount");
                    cur_frm.set_value("received_amount", received_amount );
                    cur_frm.refresh_fields("received_amount");
                    cur_frm.set_value("remaining_amount", remaining_amount );
                    cur_frm.refresh_fields("remaining_amount");
                    cur_frm.set_value("customer_name", customer );
                    cur_frm.refresh_fields("customer_name");
                    cur_frm.set_value("address", address);
                    cur_frm.refresh_fields("address");                
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
                        row.installment_amount = data.message[i].installment_amount;
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
        frm.doc.installment_total = total;
        frm.refresh_field('installment_total');
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
        
        	frm.doc.installment_total = total;
            frm.refresh_field('installment_total');
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
        
        frm.doc.installment_total = total;
        frm.refresh_field('installment_total');
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
