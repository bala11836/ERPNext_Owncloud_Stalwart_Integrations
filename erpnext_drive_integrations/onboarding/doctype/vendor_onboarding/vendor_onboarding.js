// Vendor Onboarding (ADR-039): staff buttons. The server re-checks every role and rule.
// No manual check buttons (MD 2026-11-12): a complete IFSC / GSTIN saves the Draft, and the server fills the
// bank and GST boxes by itself (erpnext_drive_integrations.onboarding.vendor.auto_fill).
const hov_auto_check = (frm, field, length) => {
	const value = String(frm.doc[field] || "").trim();
	if ((frm.is_new() || frm.doc.status === "Draft") && frm.is_dirty() && (!value || value.length === length)) frm.save();
};
frappe.ui.form.on("Vendor Onboarding", {
	gstin: (frm) => hov_auto_check(frm, "gstin", 15),
	ifsc: (frm) => hov_auto_check(frm, "ifsc", 11),
	no_gst: (frm) => hov_auto_check(frm, "no_gst", 1),
	refresh(frm) {
		const auto = __("Filled automatically");
		["bank_name", "bank_branch"].forEach((f) => frm.set_df_property(f, "description", auto + " " + __("from the IFSC")));
		["gst_legal_name", "gst_status"].forEach((f) => frm.set_df_property(f, "description", auto + " " + __("from the GSTIN")));
		if (frm.is_new()) return;
		const call = (method, args) =>
			frappe.call({ method: `erpnext_drive_integrations.onboarding.vendor.${method}`, args: { name: frm.doc.name, ...args }, freeze: true });
		const st = frm.doc.status;
		frm.page.set_indicator(__(st), { Draft: "gray", Sent: "blue", "Submitted by vendor": "orange", Approved: "green", Rejected: "red" }[st]);

		if (st === "Draft") {
			frm.add_custom_button(__("Send to vendor"), () =>
				frappe.confirm(__("The onboarding link is created only once. Later changes need a KYC Amendment. Send now?"), () =>
					call("send").then((r) => {
						hov_show_link(r.message.manual_link);
						frm.reload_doc();
					})
				)
			).addClass("btn-primary");
		}
		if (st === "Submitted by vendor") {
			const approve = (confirm) =>
				call("approve", { confirm_duplicates: confirm ? 1 : 0 }).then((r) => {
					const m = r.message || {};
					if (m.duplicates) {
						frappe.confirm(
							__("Possible duplicates:") + "<br>" + m.duplicates.map(frappe.utils.escape_html).join("<br>") + "<br><br>" + __("Approve anyway?"),
							() => approve(true)
						);
					} else {
						frappe.show_alert({ message: __("Supplier {0} created", [m.supplier]), indicator: "green" });
						frm.reload_doc();
					}
				});
			frm.add_custom_button(__("Approve and create Supplier"), () => approve(false), __("Decide"));
		}
		if (["Sent", "Submitted by vendor"].includes(st)) {
			frm.add_custom_button(__("Reject"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }, (v) =>
					call("reject", { reason: v.reason }).then(() => frm.reload_doc())
				), __("Decide"));
		}
		if (frm.doc.checks && st !== "Draft") {
			const lines = frm.doc.checks.split("\n").map((l) => {
				const icon = l.startsWith("[error]") ? "✖" : l.startsWith("[warning]") ? "⚠" : "ℹ";
				return `${icon} ${frappe.utils.escape_html(l.replace(/^\[\w+\]\s*/, ""))}`;
			});
			frm.set_intro(lines.join("<br>"), st === "Approved" ? "green" : "orange");
		}
	},
});

function hov_show_link(url) {
	const d = new frappe.ui.Dialog({
		title: __("Share this link (shown only once)"),
		fields: [{
			fieldtype: "HTML",
			options: `<p>${__("Send it to the vendor yourself (WhatsApp / SMS from your phone). It opens on one device only and will not be shown again.")}</p>
				<input class="form-control" readonly value="${frappe.utils.escape_html(url)}">`,
		}],
		primary_action_label: __("Copy link"),
		primary_action() {
			frappe.utils.copy_to_clipboard(url);
		},
	});
	d.show();
}
