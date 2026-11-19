// Response Request: read-only audit record. One staff action: release the device lock.
frappe.ui.form.on("Response Request", {
	refresh(frm) {
		frm.disable_save();
		if (frm.doc.status === "Sent") {
			frm.add_custom_button(__("Release device lock"), () =>
				frappe.confirm(__("Let the link be opened again on a new device (e.g. the person opened it in WhatsApp, then in Chrome)?"), () =>
					frappe.xcall("erpnext_drive_integrations.onboarding.respond.reset_device", { request: frm.doc.name }).then(() => frm.reload_doc())
				)
			);
		}
	},
});
