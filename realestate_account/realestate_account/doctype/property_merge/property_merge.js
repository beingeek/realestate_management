frappe.ui.form.on("Property Merge", {
    refresh: function (frm) {
        if (frm.doc.docstatus == 0) {
            frm.add_custom_button(
                __("Get Installment list"),
                function () {
                    frm.trigger("get_insallment_information");
                },
            ).addClass("btn-primary");
        }
    },
    get_insallment_information: function(frm) {
        let docNo;
        let method;

        if (frm.doc.ppr_active === 0) {
            docNo = frm.doc.document_number;

            if (frm.doc.document_type === 'Plot Booking') {
                method = 'realestate_account.controllers.real_estate_controller.get_installment_list_from_booking';
            } else if (frm.doc.document_type === 'Property Transfer') {
                method = 'realestate_account.controllers.real_estate_controller.get_installment_list_from_transfer';
            } else {
                frappe.msgprint(__('Invalid document type.'));
                return;
            }
        } else {
            docNo = frm.doc.payment_plan_reschedule;
            method = 'realestate_account.controllers.real_estate_controller.get_installment_list_from_payment_reschedule';
        }
    
        frappe.call({
            method: method,
            args: {
                doc_no: docNo,
            },
            callback: function(data) {
                frm.clear_table('installment');
                frm.set_value("installment_total", 0);
                let receivable_total = 0;
                data.message.sort((a, b) => new Date(a.date) - new Date(b.date));
                for (let i = 0; i < (data.message.length); i++) {
                    if (data.message[i].receivable_amount > 0) {
                        var row = frm.add_child("installment");
                        row.installment = data.message[i].Installment;
                        row.installment_amount = data.message[i].installment_amount;
                        row.receivable_amount = data.message[i].receivable_amount;
                        row.base_doc_idx = data.message[i].idx;
                        row.date = data.message[i].date;
                        row.base_doc_no = data.message[i].name;
                        row.remaining_amount = data.message[i].receivable_amount;
                        receivable_total += data.message[i].receivable_amount;
                        row.paid_amount = 0;
                    }
                }
                frm.get_field("installment").grid.cannot_add_rows = true;
                frm.refresh_fields("installment");
            }
        });
    },
    merge_document_number : function(frm) {
        if(frm.doc.document_number) {
            frappe.call({
                method: 'realestate_account.controllers.real_estate_controller.get_customer_partner',
                args: {
                    document_number: frm.doc.document_number,
                },
                callback: function(data) {
                    if (data.message) {
                        frm.clear_table('customer_partnership');
                        for (let i = 0; i < data.message.length; i++) {
                            var row = frm.add_child('customer_partnership');
                            row.customer = data.message[i].customer;
                            row.father_name = data.message[i].father_name;
                            row.id_card_no = data.message[i].id_card_no;
                            row.mobile_no = data.message[i].mobile_no;
                            row.address = data.message[i].address;
                            row.share_percentage = data.message[i].share_percentage;
                        }
                        frm.refresh_fields('customer_partnership');        
                    } else {
                        frappe.msgprint(__('Error: ') + data.exc);
                    }
                }
            });
        
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
                    console.log(r);
                if (!r.exc && r.message && r.message.length > 0) {
                    if (!r.exc && r.message && r.message.length > 0) {
                        var name = r.message[0].name;
                        var Customer = r.message[0].customer;
                        var docType = r.message[0].Doc_type;
                        var share_percentage = r.message[0].share_percentage;
                        var pprActive = r.message[0].ppr_active;
                        var ppRechedule = r.message[0].payment_plan_reschedule;
                        var salesAmount = r.message[0].sales_amount;
                        var receivedAmount = r.message[0].received_amount;
                        var balanceAmount =  r.message[0].sales_amount - r.message[0].received_amount;

                        cur_frm.set_value('document_type', docType);
                        cur_frm.set_value('document_number', name);
                        cur_frm.set_value("sales_amount", salesAmount);
                        cur_frm.set_value("received_amount", receivedAmount);
                        cur_frm.set_value("balance_amount", balanceAmount);
                        cur_frm.set_value("payment_plan_reschedule", ppRechedule);
                        cur_frm.set_value("ppr_active", pprActive);
                        cur_frm.set_value("from_customer", Customer);	 
                    }
                }
            }
        });
    },
    

frappe.ui.form.on("Property Merge", {
    deduction:function(frm) {
        calc_net_amount(frm);
    },
    merge_amount:function(frm) {
        calc_net_amount(frm);
    },
    balance_amount:function(frm) {
        calc_net_amount(frm);
    },
    merge_project: function(frm) {
        var merge_project = frm.doc.merge_project;
        if (!frm.doc.merge_project) {
            frappe.throw(__("Please select a Merge project."));
            return;
        }
        if (frm.prompt_opened) {
            return;
        }

        frm.cscript.merge_project = function(doc) {
            if (doc.merge_project !== merge_project) {
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
                    "status": 'Booked', 'project': frm.doc.merge_project
                }
            })
        }, (values) => {
            frappe.model.set_value(frm.doctype, frm.docname, 'merge_plot_no', values.selected_plot);
            frm.prompt_opened = false;
        }, __('Select Available Plot'));
    }
});
    cur_frm.cscript.merge_plot_no = function(doc) {
        frappe.call({
            method: "realestate_account.controllers.real_estate_controller.get_previous_document_detail",
            args: {
                plot_no: doc.merge_plot_no
            },
            callback: function(r) {
                console.log(r);
            if (!r.exc && r.message && r.message.length > 0) {
                if (!r.exc && r.message && r.message.length > 0) {
                    var receivedAmount = r.message[0].received_amount;
                    var Customer = r.message[0].customer;
                    var name = r.message[0].name;    
                    var docType = r.message[0].Doc_type;
                    var share_percentage = r.message[0].share_percentage;
                    var customer_type = r.message[0].customer_type;
                    var sales_broker = r.message[0].sales_broker;

                    cur_frm.set_value('merge_sales_broker', sales_broker);
                    cur_frm.set_value('merge_document_type', docType);
                    cur_frm.set_value('merge_document_number', name);
                    cur_frm.set_value("merge_amount", receivedAmount);
                    cur_frm.set_value("merge_customer", Customer);
                    cur_frm.set_value("merge_share_percentage", share_percentage);
                    cur_frm.set_value("merge_customer_type", customer_type);
                }
            }
        }
    });
}


frappe.ui.form.on("Property Merge Payment Installment", {
    paid_amount:  function(frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        if(item.paid_amount > item.receivable_amount) {
            frappe.model.set_value(cdt, cdn,'paid_amount',0) ;
            frappe.msgprint('paid amount is greater than receivable amount');
        } else {
            let total = 0;
            frm.doc.installment.forEach(d=>{
                total = total + parseFloat(d.paid_amount);
                
                frm.doc.installment_total = total;
                frm.refresh_field('installment_total');
            })

            let rAmount = parseFloat(item.receivable_amount) - parseFloat(item.paid_amount);
            frappe.model.set_value(cdt, cdn,'remaining_amount',rAmount) ;
        }
    },
    installment_remove: function(frm) {
        let total = 0;
        let receivable = 0;
        frm.doc.installment.forEach(d=>{
             total = total + flt(d.paid_amount);
             receivable = receivable + flt(d.receivable_amount);
        })
        
        frm.doc.installment_total = total;
        frm.refresh_field('installment_total');
    }
});


function calc_net_amount(frm) {
    var netAmount = frm.doc.merge_amount - frm.doc.deduction;
    frm.set_value("net_amount_merge", netAmount);
}
