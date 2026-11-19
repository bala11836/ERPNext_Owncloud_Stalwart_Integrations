// KYC Amendment (ADR-039): staff buttons. The server re-checks roles, the verified email and every value.
frappe.ui.form.on("KYC Amendment", {
	refresh(frm) {
		if (frm.is_new()) return;
		const call = (method) => frappe.call({ method: `erpnext_drive_integrations.onboarding.amendment.${method}`, args: { name: frm.doc.name }, freeze: true });
		const st = frm.doc.status;
		frm.page.set_indicator(__(st), { Draft: "gray", Sent: "blue", Approved: "green", Rejected: "red" }[st] || "orange");
		if (st === "Draft") {
			frm.add_custom_button(__("Send to vendor"), () =>
				frappe.confirm(__("This goes to the vendor's current principal contact email ({0}). Send?", [frm.doc.send_to_email || "?"]), () =>
					call("send").then(() => frm.reload_doc())
				)
			).addClass("btn-primary");
		}
		if (["Confirmed by vendor", "Submitted by vendor"].includes(st)) {
			frm.add_custom_button(__("Approve and apply"), () =>
				frappe.confirm(
					frm.doc.includes_bank_change
						? __("This changes the vendor's BANK details: a new bank account is created and the old one disabled. Approve?")
						: __("Apply these changes to the supplier?"),
					() => call("approve").then(() => frm.reload_doc())
				)
			).addClass("btn-primary");
		}
	},
});
