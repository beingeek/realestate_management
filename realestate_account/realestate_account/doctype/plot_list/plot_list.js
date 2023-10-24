// Copyright (c) 2023, CE Construction and contributors
// For license information, please see license.txt


frappe.ui.form.on('Plot List', {
    refresh: function(frm) {
        var status = frm.doc.status;
        frm.toggle_enable("hold_for_sale", status !== "Booked");
    }
});

frappe.ui.form.on('Plot List', {
	hold_for_sale: function(frm) {
        var holdForSale = frm.doc.hold_for_sale;
        frm.toggle_display("reason_for_hold", holdForSale);
    },

	onload: function(frm) {
        var holdForSale = frm.doc.hold_for_sale;
        frm.toggle_display("reason_for_hold", holdForSale);
    }
});

frappe.ui.form.on('Plot List', {
    land_area: function(frm) {
        calculate_total_amount(frm);
    },
    land_price: function(frm) {
        calculate_total_amount(frm);
    }
});

function calculate_total_amount(frm) {
    var  total_amount = parseFloat(frm.doc.land_area) * parseFloat(frm.doc.land_price);
    frm.set_value('total', total_amount);
}