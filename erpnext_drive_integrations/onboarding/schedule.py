"""Construction schedule (Gantt) for an ERPNext Project (MD, 2026-11-08).

Bars = the Project's Tasks (planned start / end, % done); arrows = each Task's "Depends On" list;
critical path = tasks with zero slack; baseline = the original plan frozen into two custom Task fields.
Reading uses ERPNext's own permissions. Moving dates and setting the baseline are limited to the
Projects Manager and Project Coordinator roles (MD decision), and ERPNext's Task rules still apply.
"""
from datetime import date, datetime

import frappe
from frappe import _

EDIT_ROLES = {"Projects Manager", "Project Coordinator"}


def can_edit_dates(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool(EDIT_ROLES & set(frappe.get_roles(user)))


def _day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def critical_path(tasks):
    """Classic critical path on planned durations. tasks: [{name, start, end, deps:[names]}].

    Returns the names with zero slack. Tasks without dates are ignored; a dependency loop returns no
    critical path rather than failing the whole page.
    """
    dated = {t["name"]: t for t in tasks if t.get("start") and t.get("end")}
    duration = {n: (_day(t["end"]) - _day(t["start"])).days + 1 for n, t in dated.items()}
    deps = {n: [d for d in dated[n].get("deps", []) if d in dated] for n in dated}
    order, state = [], {}

    def visit(n):
        if state.get(n) == 1:
            raise ValueError("dependency loop")
        if state.get(n) == 2:
            return
        state[n] = 1
        for d in deps[n]:
            visit(d)
        state[n] = 2
        order.append(n)

    try:
        for n in dated:
            visit(n)
    except ValueError:
        return []
    early_finish = {}
    for n in order:
        early_finish[n] = max((early_finish[d] for d in deps[n]), default=0) + duration[n]
    project_end = max(early_finish.values(), default=0)
    successors = {n: [m for m in dated if n in deps[m]] for n in dated}
    late_finish = {}
    for n in reversed(order):
        late_finish[n] = min((late_finish[s] - duration[s] for s in successors[n]), default=project_end)
    return [n for n in order if late_finish[n] - early_finish[n] == 0]


@frappe.whitelist(methods=["GET"])
def get_schedule(project: str):
    if not frappe.has_permission("Project", "read", project):
        frappe.throw(_("You don't have permission to see this project."), frappe.PermissionError)
    rows = frappe.get_list(
        "Task",
        filters={"project": project, "status": ["!=", "Cancelled"]},
        fields=["name", "subject", "exp_start_date", "exp_end_date", "progress", "status", "is_group",
                "is_milestone", "parent_task", "hov_baseline_start", "hov_baseline_end"],
        order_by="exp_start_date asc, name asc",
        limit_page_length=0,
    )
    names = [r.name for r in rows]
    deps = {}
    for d in frappe.get_all("Task Depends On", filters={"parent": ["in", names or [""]], "parenttype": "Task"},
                            fields=["parent", "task"]):
        if d.task in names:
            deps.setdefault(d.parent, []).append(d.task)
    tasks = [{"name": r.name, "start": r.exp_start_date, "end": r.exp_end_date, "deps": deps.get(r.name, [])}
             for r in rows]
    critical = set(critical_path(tasks))
    return {
        "project": frappe.db.get_value("Project", project, ["name", "project_name", "status"], as_dict=True),
        "can_edit": can_edit_dates() and bool(frappe.has_permission("Task", "write")),
        "tasks": [dict(r, deps=deps.get(r.name, []), critical=r.name in critical) for r in rows],
    }


def _require_editor(task=None):
    if not can_edit_dates():
        frappe.throw(_("Only a Projects Manager or Project Coordinator can change the schedule."),
                     frappe.PermissionError)
    if task and not frappe.has_permission("Task", "write", task):
        frappe.throw(_("You don't have permission to change this task."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def update_dates(task: str, start: str, end: str):
    _require_editor(task)
    if _day(start) > _day(end):
        frappe.throw(_("The start date must be on or before the end date."))
    doc = frappe.get_doc("Task", task)
    doc.exp_start_date, doc.exp_end_date = start, end
    doc.save()  # ERPNext's own Task validations (dependencies, project dates) still run
    return {"name": doc.name, "exp_start_date": doc.exp_start_date, "exp_end_date": doc.exp_end_date}


@frappe.whitelist(methods=["POST"])
def set_baseline(project: str, overwrite: int = 0):
    """Freeze the current plan as the baseline (only tasks without one, unless overwrite)."""
    _require_editor()
    if not frappe.has_permission("Project", "read", project):
        frappe.throw(_("You don't have permission to see this project."), frappe.PermissionError)
    done = 0
    for t in frappe.get_list("Task", filters={"project": project}, pluck="name", limit_page_length=0):
        doc = frappe.get_doc("Task", t)
        if not frappe.has_permission("Task", "write", doc) or not (doc.exp_start_date and doc.exp_end_date):
            continue
        if doc.hov_baseline_start and not int(overwrite):
            continue
        doc.db_set({"hov_baseline_start": doc.exp_start_date, "hov_baseline_end": doc.exp_end_date})
        done += 1
    return {"baselined": done}
