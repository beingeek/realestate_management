frappe.ui.form.on('Plot List', {
    refresh: function(frm) {
        frm.toggle_enable("hold_for_sale", frm.doc.status !== "Booked");
    },

	hold_for_sale: function(frm) {
        frm.toggle_display("reason_for_hold", frm.doc.hold_for_sale);
    },

	onload: function(frm) {
        frm.toggle_display("reason_for_hold", frm.doc.hold_for_sale);
    },

    land_area: function(frm) {
        calculate_total_amount(frm);
    },

    land_price: function(frm) {
        calculate_total_amount(frm);
    }
});

function calculate_total_amount(frm) {
    var total_amount = parseFloat(frm.doc.land_area) * parseFloat(frm.doc.land_price);
    frm.set_value('total', total_amount);
}
