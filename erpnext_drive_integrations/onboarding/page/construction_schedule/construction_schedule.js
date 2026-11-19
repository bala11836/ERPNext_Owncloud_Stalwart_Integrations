// Construction Schedule (onboarding). Uses ERPNext's own bundled Gantt library (frappe-gantt), loaded the
// same way as ERPNext's Gantt view. Server checks decide everything (erpnext_drive_integrations.onboarding.schedule).
frappe.pages["construction-schedule"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Construction Schedule"), single_column: true });
	wrapper.hov_schedule = new OnboardingSchedule(page);
};

frappe.pages["construction-schedule"].on_page_show = function (wrapper) {
	const project = frappe.route_options && frappe.route_options.project;
	if (project && wrapper.hov_schedule) {
		frappe.route_options = null;
		wrapper.hov_schedule.project.set_value(project);
	}
};

const HOV_LIBS = [
	"assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.css",
	"assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.umd.js",
];

class OnboardingSchedule {
	constructor(page) {
		this.page = page;
		this.project = page.add_field({
			fieldtype: "Link", options: "Project", fieldname: "project", label: __("Project"),
			change: () => this.load(),
		});
		this.mode = page.add_field({
			fieldtype: "Select", fieldname: "mode", label: __("Zoom"), options: "Day\nWeek\nMonth", default: "Week",
			change: () => this.gantt && this.gantt.change_view_mode(this.mode.get_value()),
		});
		page.add_button(__("Print"), () => window.print(), { icon: "printer" });
		this.baseline_btn = page.add_button(__("Set baseline"), () => this.set_baseline());
		this.baseline_btn.hide();
		this.$legend = $(`<div class="hov-legend text-muted small" style="margin:8px 0 12px">
			<b>◆ ${__("Critical path")}</b> - ${__("delaying these delays the whole project")} &nbsp;|&nbsp;
			<b>${__("(overdue)")}</b> - ${__("end date passed, not complete")} &nbsp;|&nbsp;
			<b>${__("+N d vs baseline")}</b> - ${__("later than the original plan")}</div>`).appendTo(page.main);
		this.$info = $('<div class="hov-info"></div>').appendTo(page.main);
		this.$chart = $('<div class="hov-gantt"></div>').appendTo(page.main);
		$(`<style>
			.hov-gantt .bar-wrapper.hov-critical .bar { stroke: #8F0010; stroke-width: 2px; }
			.hov-gantt .bar-wrapper.hov-overdue .bar-label { font-weight: 700; }
			@media print { .page-head, .layout-side-section, .navbar, #hov-test-bar, #hov-refresh { display: none !important; } }
		</style>`).appendTo(page.main);
		this.$info.html(`<p class="text-muted">${__("Choose a project to see its schedule.")}</p>`);
	}

	async load() {
		const project = this.project.get_value();
		this.$chart.empty();
		if (!project) return;
		this.$info.html(`<p class="text-muted">${__("Loading...")}</p>`);
		let data;
		try {
			data = (await frappe.xcall("erpnext_drive_integrations.onboarding.schedule.get_schedule", { project }, "GET"));
		} catch (e) {
			this.$info.html(`<p class="text-danger">${__("Could not load this project.")}</p>`);
			return;
		}
		this.can_edit = data.can_edit;
		this.baseline_btn.toggle(!!this.can_edit);
		const today = frappe.datetime.get_today();
		const day = (v) => (v ? String(v).slice(0, 10) : null);
		const tasks = data.tasks.filter((t) => t.exp_start_date && t.exp_end_date).map((t) => {
			const end = day(t.exp_end_date);
			const slip = t.hov_baseline_end ? frappe.datetime.get_diff(end, day(t.hov_baseline_end)) : 0;
			const overdue = end < today && (t.progress || 0) < 100 && t.status !== "Completed";
			// frappe-gantt draws the label as HTML: escape the user-typed subject (audit UI-02).
			let label = (t.critical ? "◆ " : "") + frappe.utils.escape_html(t.subject);
			if (overdue) label += " " + __("(overdue)");
			if (slip > 0) label += ` (+${slip} d vs baseline)`;
			return {
				id: t.name, name: label, start: day(t.exp_start_date), end, progress: t.progress || 0,
				dependencies: (t.deps || []).join(", "),
				custom_class: [t.critical ? "hov-critical" : "", overdue ? "hov-overdue" : "", t.is_milestone ? "bar-milestone" : ""].join(" ").trim(),
			};
		});
		const missing = data.tasks.length - tasks.length;
		const who = this.can_edit ? __("You can drag bars to change dates.") : __("View only: dates can be changed by a Projects Manager or Project Coordinator.");
		this.$info.html(`<p><b>${frappe.utils.escape_html(data.project.project_name || data.project.name)}</b> - ${tasks.length} ${__("tasks")}${missing ? `, ${missing} ${__("without dates (not shown)")}` : ""}. ${who}</p>`);
		if (!tasks.length) return;
		await frappe.require(HOV_LIBS);
		this.gantt = new Gantt(this.$chart[0], tasks, {
			bar_height: 30, bar_corner_radius: 4, infinite_padding: false, date_format: "YYYY-MM-DD",
			view_mode: this.mode.get_value() || "Week", readonly: !this.can_edit, readonly_progress: true,
			on_double_click: (task) => frappe.set_route("Form", "Task", task.id),
			on_date_change: (task, start, end) => this.save(task, start, end),
		});
	}

	async save(task, start, end) {
		if (!this.can_edit) return;
		try {
			await frappe.xcall("erpnext_drive_integrations.onboarding.schedule.update_dates", {
				task: task.id, start: moment(start).format("YYYY-MM-DD HH:mm:ss"), end: moment(end).format("YYYY-MM-DD HH:mm:ss"),
			});
			frappe.show_alert({ message: __("Dates saved"), indicator: "green" });
		} catch (e) {
			this.load(); // put the bar back where ERPNext says it is
		}
	}

	set_baseline() {
		const project = this.project.get_value();
		if (!project) return;
		frappe.confirm(__("Freeze the current plan as the baseline for tasks that don't have one yet?"), async () => {
			const r = await frappe.xcall("erpnext_drive_integrations.onboarding.schedule.set_baseline", { project });
			frappe.show_alert({ message: __("Baseline set for {0} tasks", [r.baselined]), indicator: "green" });
			this.load();
		});
	}
}
