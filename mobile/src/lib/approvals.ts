// Approvals (owner's plan, 24 November 2026): every approval ERPNext gives a person, across all their sites.
// ERPNext decides what is listed: its Workflow Actions (any document type with a workflow, see lib/inbox.ts) and
// custom_hr's attendance lists. The app only chooses how a document type is shown: designed cards for payments,
// purchase, stores, HR and attendance, a general card for anything else. Approving goes through ERPNext's own
// workflow (`apply_workflow`), which checks the role, the state and self-approval again.
import { z } from 'zod';

import { t as text } from '@/i18n';
import { type BootT, HR_API, Pending, ToVerify, isException, loadBoot } from '@/lib/attendance';
import { type Api, callErp, metaPath } from '@/lib/erp';
import { formatDate, formatMoney } from '@/lib/format';
import type { InboxAction } from '@/lib/inbox';
import { callKept, getChecked, getKept } from '@/lib/saved';

export type Area = 'payments' | 'purchase' | 'stores' | 'hr' | 'attendance' | 'other';
export const AREAS: Area[] = ['payments', 'purchase', 'stores', 'hr', 'attendance', 'other'];

type Rec = Record<string, unknown>;
const str = (r: Rec, f: string) => (typeof r[f] === 'string' && r[f] ? (r[f] as string) : null);
const num = (r: Rec, f: string) => {
  const n = typeof r[f] === 'number' ? (r[f] as number) : Number(r[f]);
  return r[f] === null || r[f] === undefined || r[f] === '' || !Number.isFinite(n) ? null : n;
};
const join = (...parts: (string | null | undefined | false)[]) => parts.filter(Boolean).join(' · ');
const days = (from: string | null, to: string | null) => (from && to && from !== to ? `${formatDate(from)} – ${formatDate(to)}` : formatDate(from ?? to ?? ''));

/** One line of a card's table: what, how much, its amount, and a note (stock left, rate warning). */
export type Line = { title: string; detail?: string; amount?: string };

type Spec = {
  area: Area;
  /** The list row: fields read with `frappe.client.get_list` (a missing field only loses the row's details). */
  fields: string[];
  amount?: string;
  currency?: string;
  party?: string;
  site?: string[];
  detail?: (r: Rec) => string;
  /** The card: the big line at the top (default: the amount), the facts in order, the table shown. */
  headline?: (doc: Rec) => string | null;
  facts: string[];
  lines?: { table: string; line: (row: Rec, doc: Rec) => Line };
  /** "Approve all" with one Face ID: only attendance and leave, never money (owner, 24 November 2026). */
  bulk?: boolean;
  /** Never kept on the phone for offline reading (owner: leave and payslips). */
  online?: boolean;
};

const money = (r: Rec, f: string, c?: string | null) => (num(r, f) === null ? undefined : formatMoney(num(r, f), c ?? str(r, 'currency')));
const itemLine = (row: Rec, doc: Rec): Line => ({
  title: str(row, 'item_name') ?? str(row, 'item_code') ?? '',
  detail: join(
    num(row, 'qty') !== null && `${num(row, 'qty')} ${str(row, 'uom') ?? str(row, 'stock_uom') ?? ''}`.trim() + (num(row, 'rate') !== null ? ` × ${money(row, 'rate', str(doc, 'currency'))}` : ''),
  ),
  amount: money(row, 'amount', str(doc, 'currency')),
});
const stockLine = (row: Rec): Line => ({
  title: str(row, 'item_name') ?? str(row, 'item_code') ?? '',
  detail: join(
    num(row, 'qty') !== null && `${num(row, 'qty')} ${str(row, 'uom') ?? str(row, 'stock_uom') ?? ''}`.trim(),
    (str(row, 's_warehouse') || str(row, 'from_warehouse')) && text('approvals.fromTo', { from: str(row, 's_warehouse') ?? str(row, 'from_warehouse') ?? '', to: str(row, 't_warehouse') ?? str(row, 'warehouse') ?? '' }),
  ),
});
const SITE = ['project', 'cost_center'];

/** The designed cards. Field names are ERPNext's own; labels and formats come from ERPNext's metadata. */
export const SPECS: Record<string, Spec> = {
  'Payment Entry': {
    area: 'payments',
    fields: ['party_name', 'paid_amount', 'paid_from_account_currency', 'payment_type', 'mode_of_payment', 'project', 'cost_center'],
    amount: 'paid_amount',
    currency: 'paid_from_account_currency',
    party: 'party_name',
    site: SITE,
    detail: (r) => join(str(r, 'payment_type'), str(r, 'mode_of_payment')),
    facts: ['payment_type', 'mode_of_payment', 'paid_from', 'paid_to', 'posting_date', 'reference_no', 'reference_date', 'project', 'cost_center', 'remarks'],
    lines: {
      table: 'references',
      line: (row, doc) => ({ title: join(str(row, 'reference_doctype'), str(row, 'reference_name')), amount: money(row, 'allocated_amount', str(doc, 'paid_from_account_currency')) }),
    },
  },
  'Payment Request': {
    area: 'payments',
    fields: ['party', 'grand_total', 'currency', 'payment_request_type', 'transaction_date'],
    amount: 'grand_total',
    currency: 'currency',
    party: 'party',
    detail: (r) => join(str(r, 'payment_request_type'), str(r, 'transaction_date') && formatDate(str(r, 'transaction_date'))),
    facts: ['payment_request_type', 'reference_doctype', 'reference_name', 'transaction_date', 'mode_of_payment', 'party_type', 'subject'],
  },
  'Journal Entry': {
    area: 'payments',
    fields: ['title', 'total_debit', 'voucher_type', 'posting_date'],
    amount: 'total_debit',
    party: 'title',
    detail: (r) => join(str(r, 'voucher_type'), str(r, 'posting_date') && formatDate(str(r, 'posting_date'))),
    facts: ['voucher_type', 'posting_date', 'cheque_no', 'cheque_date', 'user_remark'],
    lines: {
      table: 'accounts',
      line: (row) => ({
        title: str(row, 'account') ?? '',
        detail: str(row, 'party') ?? undefined,
        amount: num(row, 'debit_in_account_currency')
          ? text('approvals.debit', { amount: formatMoney(num(row, 'debit_in_account_currency'), str(row, 'account_currency')) })
          : text('approvals.credit', { amount: formatMoney(num(row, 'credit_in_account_currency'), str(row, 'account_currency')) }),
      }),
    },
  },
  'Purchase Invoice': {
    area: 'payments',
    fields: ['supplier_name', 'grand_total', 'currency', 'bill_no', 'due_date', 'project', 'cost_center'],
    amount: 'grand_total',
    currency: 'currency',
    party: 'supplier_name',
    site: SITE,
    detail: (r) => join(str(r, 'bill_no') && text('approvals.bill', { bill: str(r, 'bill_no') ?? '' }), str(r, 'due_date') && text('approvals.due', { date: formatDate(str(r, 'due_date')) })),
    facts: ['bill_no', 'bill_date', 'posting_date', 'due_date', 'project', 'cost_center', 'total_taxes_and_charges'],
    lines: { table: 'items', line: itemLine },
  },
  'Material Request': {
    area: 'purchase',
    fields: ['title', 'material_request_type', 'schedule_date', 'set_warehouse'],
    party: 'title',
    detail: (r) => join(str(r, 'material_request_type'), str(r, 'schedule_date') && text('approvals.neededBy', { date: formatDate(str(r, 'schedule_date')) })),
    headline: (doc) => str(doc, 'material_request_type'),
    facts: ['material_request_type', 'transaction_date', 'schedule_date', 'set_from_warehouse', 'set_warehouse'],
    lines: { table: 'items', line: (row) => stockLine(row) },
  },
  'Supplier Quotation': {
    area: 'purchase',
    fields: ['supplier_name', 'grand_total', 'currency', 'transaction_date', 'valid_till'],
    amount: 'grand_total',
    currency: 'currency',
    party: 'supplier_name',
    detail: (r) => join(str(r, 'valid_till') && text('approvals.validTill', { date: formatDate(str(r, 'valid_till')) })),
    facts: ['transaction_date', 'valid_till', 'total_taxes_and_charges'],
    lines: { table: 'items', line: itemLine },
  },
  'Purchase Order': {
    area: 'purchase',
    fields: ['supplier_name', 'grand_total', 'currency', 'schedule_date', 'project'],
    amount: 'grand_total',
    currency: 'currency',
    party: 'supplier_name',
    site: ['project'],
    detail: (r) => join(str(r, 'schedule_date') && text('approvals.neededBy', { date: formatDate(str(r, 'schedule_date')) })),
    facts: ['schedule_date', 'transaction_date', 'project', 'set_warehouse', 'total_taxes_and_charges'],
    lines: { table: 'items', line: itemLine },
  },
  'Stock Entry': {
    area: 'stores',
    fields: ['stock_entry_type', 'from_warehouse', 'to_warehouse', 'project'],
    party: 'stock_entry_type',
    site: ['project'],
    detail: (r) => join((str(r, 'from_warehouse') || str(r, 'to_warehouse')) && text('approvals.fromTo', { from: str(r, 'from_warehouse') ?? '', to: str(r, 'to_warehouse') ?? '' })),
    headline: (doc) => str(doc, 'stock_entry_type'),
    facts: ['stock_entry_type', 'from_warehouse', 'to_warehouse', 'posting_date', 'project', 'remarks'],
    lines: { table: 'items', line: (row) => stockLine(row) },
  },
  'Purchase Receipt': {
    area: 'stores',
    fields: ['supplier_name', 'grand_total', 'currency', 'posting_date', 'project', 'set_warehouse'],
    amount: 'grand_total',
    currency: 'currency',
    party: 'supplier_name',
    site: ['project'],
    detail: (r) => join(str(r, 'set_warehouse')),
    facts: ['posting_date', 'set_warehouse', 'supplier_delivery_note', 'project'],
    lines: { table: 'items', line: itemLine },
  },
  'Leave Application': {
    area: 'hr',
    fields: ['employee_name', 'leave_type', 'from_date', 'to_date', 'total_leave_days'],
    party: 'employee_name',
    detail: (r) => join(str(r, 'leave_type'), days(str(r, 'from_date'), str(r, 'to_date'))),
    headline: (doc) => join(num(doc, 'total_leave_days') !== null && text('approvals.days', { count: num(doc, 'total_leave_days') ?? 0 }), days(str(doc, 'from_date'), str(doc, 'to_date'))),
    facts: ['leave_type', 'from_date', 'to_date', 'total_leave_days', 'half_day', 'description', 'department'],
    bulk: true,
    online: true,
  },
  'Expense Claim': {
    area: 'hr',
    fields: ['employee_name', 'total_claimed_amount', 'posting_date', 'project', 'cost_center'],
    amount: 'total_claimed_amount',
    party: 'employee_name',
    site: SITE,
    detail: (r) => join(str(r, 'posting_date') && formatDate(str(r, 'posting_date'))),
    facts: ['posting_date', 'project', 'cost_center', 'department', 'total_sanctioned_amount', 'total_advance_amount'],
    lines: { table: 'expenses', line: (row) => ({ title: str(row, 'expense_type') ?? '', detail: str(row, 'description') ?? undefined, amount: money(row, 'amount') }) },
  },
  'Employee Advance': {
    area: 'hr',
    fields: ['employee_name', 'advance_amount', 'currency', 'purpose'],
    amount: 'advance_amount',
    currency: 'currency',
    party: 'employee_name',
    detail: (r) => join(str(r, 'purpose')),
    facts: ['purpose', 'posting_date', 'mode_of_payment', 'department', 'repay_unclaimed_amount_from_salary'],
  },
  'Attendance Request': {
    area: 'hr',
    fields: ['employee_name', 'from_date', 'to_date', 'reason'],
    party: 'employee_name',
    detail: (r) => join(str(r, 'reason'), days(str(r, 'from_date'), str(r, 'to_date'))),
    headline: (doc) => days(str(doc, 'from_date'), str(doc, 'to_date')),
    facts: ['from_date', 'to_date', 'reason', 'explanation', 'half_day', 'department'],
    bulk: true,
  },
  'Shift Request': {
    area: 'hr',
    fields: ['employee_name', 'shift_type', 'from_date', 'to_date'],
    party: 'employee_name',
    detail: (r) => join(str(r, 'shift_type'), days(str(r, 'from_date'), str(r, 'to_date'))),
    headline: (doc) => join(str(doc, 'shift_type'), days(str(doc, 'from_date'), str(doc, 'to_date'))),
    facts: ['shift_type', 'from_date', 'to_date', 'department'],
  },
};

const GENERAL_AMOUNT = ['grand_total', 'total_amount', 'paid_amount', 'total', 'amount'];
const GENERAL_PARTY = ['party_name', 'supplier_name', 'customer_name', 'employee_name', 'party', 'title'];
export const areaOf = (doctype: string): Area => SPECS[doctype]?.area ?? 'other';
export const keptOffline = (doctype: string) => !SPECS[doctype]?.online;

/** One row of the approvals list: a document waiting for this person, or a site's attendance. */
export type Item = {
  key: string;
  area: Area;
  title: string;
  detail: string;
  /** The ERPNext project it belongs to (the site filter), when the document has one. */
  project: string | null;
  amount: string | null;
  created: string;
  doc?: { doctype: string; name: string; state: string | null };
  attendance?: { site: string; mode: 'approve' | 'verify'; count: number; exceptions: number };
};

const Summaries = z.array(z.record(z.string(), z.unknown()));

/** One `get_list` per document type for the rows' details (permission-checked by ERPNext). */
async function summaries(api: Api, doctype: string, names: string[]): Promise<Map<string, Rec>> {
  const spec = SPECS[doctype];
  if (!spec) return new Map(); // general card: the row shows the type and name; the card reads the rest
  const args = {
    doctype,
    fields: ['name', ...spec.fields],
    filters: [['name', 'in', names]],
    limit_page_length: names.length,
  };
  try {
    const rows = await (keptOffline(doctype) ? callKept(api, 'frappe.client.get_list', Summaries, args) : callErp(api, 'frappe.client.get_list', Summaries, args));
    return new Map(rows.map((r) => [String(r.name), r]));
  } catch {
    return new Map(); // a field this ERPNext lacks, or no read right: the row still shows its type and name
  }
}

export function docItem(a: InboxAction, r: Rec | undefined): Item {
  const spec = SPECS[a.reference_doctype];
  const row = r ?? {};
  const party = spec?.party ? str(row, spec.party) : null;
  const amount = spec?.amount ? money(row, spec.amount, spec.currency ? str(row, spec.currency) : null) : undefined;
  return {
    key: `doc:${a.reference_doctype}:${a.reference_name}`,
    area: areaOf(a.reference_doctype),
    title: join(a.reference_doctype, party),
    detail: join(a.reference_name, spec?.detail?.(row), a.workflow_state),
    project: (spec?.site ?? []).map((f) => str(row, f)).find(Boolean) ?? null,
    amount: amount ?? null,
    created: a.creation,
    doc: { doctype: a.reference_doctype, name: a.reference_name, state: a.workflow_state ?? null },
  };
}

/** The workflow approvals with their details; types are read in parallel. */
export async function loadDocItems(api: Api, actions: InboxAction[]): Promise<Item[]> {
  const byType = new Map<string, string[]>();
  for (const a of actions) byType.set(a.reference_doctype, [...(byType.get(a.reference_doctype) ?? []), a.reference_name]);
  const found = new Map<string, Map<string, Rec>>();
  await Promise.all([...byType].map(async ([doctype, names]) => found.set(doctype, await summaries(api, doctype, names))));
  return actions.map((a) => docItem(a, found.get(a.reference_doctype)?.get(a.reference_name)));
}

/** Attendance waiting at every site where the person approves (PM) or verifies (engineer), one row per site. */
export async function loadAttendanceItems(api: Api): Promise<Item[]> {
  let boot: BootT;
  try {
    boot = await loadBoot(api);
  } catch {
    return [];
  }
  type Site = BootT['sites'][number];
  type Waiting = { s: Site; mode: 'approve' | 'verify'; count: number; exceptions: number; first?: string };
  const asks: Promise<Waiting | null>[] = [];
  for (const s of boot.sites) {
    if (s.approver)
      asks.push(
        callKept(api, `${HR_API}.approvals`, Pending, { site: s.name })
          .then((all) => all.filter((e) => e.can_review))
          .then((l) => ({ s, mode: 'approve' as const, count: l.length, exceptions: l.filter(isException).length, first: l.map((e) => e.attendance_date).sort()[0] }))
          .catch(() => null),
      );
    if (s.verifier)
      asks.push(
        callKept(api, `${HR_API}.verifications`, ToVerify, { site: s.name })
          .then((l) => ({ s, mode: 'verify' as const, count: l.length, exceptions: 0, first: l.map((e) => e.attendance_date).sort()[0] }))
          .catch(() => null),
      );
  }
  const rows = await Promise.all(asks);
  return rows
    .filter((r): r is Waiting => r !== null && r.count > 0)
    .map(({ s, mode, count, exceptions, first }) => ({
      key: `att:${mode}:${s.name}`,
      area: 'attendance' as const,
      title: text(mode === 'verify' ? 'approvals.attendanceVerify' : 'approvals.attendance', { count }),
      detail: join(s.label, exceptions > 0 && text('approvals.exceptions', { count: exceptions })),
      project: s.project ?? null,
      amount: null,
      created: `${first ?? ''} 00:00:00`,
      attendance: { site: s.name, mode, count, exceptions },
    }));
}

// ---- ages (owner, 23 November 2026: amber after one day, red after two) ----
export type Age = { label: string; level: 'new' | 'amber' | 'red' };
const parseLocal = (v: string) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/.exec(v);
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +(m[4] ?? 0), +(m[5] ?? 0)).getTime() : NaN;
};
export function ageOf(created: string, now: number = Date.now()): Age {
  const ms = now - parseLocal(created);
  if (!Number.isFinite(ms)) return { label: '', level: 'new' };
  const min = Math.max(0, Math.floor(ms / 60000));
  const level = min >= 2 * 1440 ? 'red' : min >= 1440 ? 'amber' : 'new';
  const label =
    min < 1 ? text('age.now') : min < 60 ? text('age.minutes', { n: min }) : min < 1440 ? text('age.hours', { n: Math.floor(min / 60) }) : text(min < 2880 ? 'age.day' : 'age.days', { n: Math.floor(min / 1440) });
  return { label, level };
}

/** Longest waiting first, then split into "waiting longest" (a day or more) and newer. */
export function arrange(items: Item[], now: number = Date.now()) {
  const sorted = [...items].sort((a, b) => parseLocal(a.created) - parseLocal(b.created));
  return {
    longest: sorted.filter((i) => ageOf(i.created, now).level !== 'new'),
    newer: sorted.filter((i) => ageOf(i.created, now).level === 'new'),
  };
}

// ---- the card: the document, its ERPNext metadata, attachments and workflow history ----
const Meta = z.object({
  docs: z.array(
    z.object({
      name: z.string(),
      title_field: z.string().nullish(),
      fields: z.array(
        z.object({
          fieldname: z.string(),
          fieldtype: z.string(),
          label: z.string().nullish(),
          options: z.string().nullish(),
          hidden: z.coerce.number().nullish(),
          in_list_view: z.coerce.number().nullish(),
        }),
      ),
    }),
  ),
});
const GetDoc = z.object({
  docs: z.array(z.record(z.string(), z.unknown())).min(1),
  docinfo: z
    .object({
      attachments: z.array(z.object({ name: z.string(), file_name: z.string().nullish(), file_url: z.string().nullish() })).default([]),
      workflow_logs: z.array(z.object({ content: z.string().nullish(), owner: z.string().nullish(), creation: z.string() })).default([]),
      user_info: z.record(z.string(), z.object({ fullname: z.string().nullish() })).nullish(),
    })
    .nullish(),
});
export const GETDOC_PATH = '/api/method/frappe.desk.form.load.getdoc';
const metaCache = new Map<string, z.infer<typeof Meta>>();
export const clearApprovalCache = () => metaCache.clear();

export type Fact = { label: string; value: string };
export type Step = { state: string; by: string | null; at: string };
export type Attachment = { name: string; fileName: string; url: string; image: boolean };
export type Flag = { kind: 'ok' | 'warn' | 'info'; label: string };
export type Card = {
  doctype: string;
  name: string;
  modified: string | null;
  state: string | null;
  headline: string;
  party: string | null;
  project: string | null;
  facts: Fact[];
  lines: Line[];
  steps: Step[];
  attachments: Attachment[];
  flags: Flag[];
  bulk: boolean;
  doc: Rec;
};

const IMAGE = /\.(jpe?g|png|webp|gif|heic)$/i;
const HIDDEN = new Set(['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button', 'Image', 'Fold', 'Heading', 'Password', 'Signature', 'Geolocation', 'JSON', 'Code', 'Barcode', 'Table', 'Table MultiSelect', 'Attach', 'Attach Image']);

type MetaT = z.infer<typeof Meta>['docs'][number];
function factOf(meta: MetaT | undefined, doc: Rec, fieldname: string): Fact | null {
  const f = meta?.fields.find((x) => x.fieldname === fieldname);
  const v = doc[fieldname];
  if (!f || v === null || v === undefined || v === '' || HIDDEN.has(f.fieldtype)) return null;
  if (f.fieldtype === 'Check') return v ? { label: f.label || fieldname, value: text('approvals.yes') } : null;
  const value =
    f.fieldtype === 'Currency'
      ? formatMoney(v, str(doc, 'currency'))
      : f.fieldtype === 'Date' || f.fieldtype === 'Datetime'
        ? formatDate(v, f.fieldtype === 'Datetime')
        : String(v).replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
  return value ? { label: f.label || fieldname, value } : null;
}

/** Warnings and checks ERPNext's own data gives, without a server change. */
function flagsOf(doctype: string, doc: Rec, attachments: number): Flag[] {
  const flags: Flag[] = [];
  const items = Array.isArray(doc.items) ? (doc.items as Rec[]) : [];
  if (doctype === 'Purchase Order' || doctype === 'Purchase Invoice' || doctype === 'Supplier Quotation') {
    const dearer = items.filter((r) => (num(r, 'last_purchase_rate') ?? 0) > 0 && (num(r, 'rate') ?? 0) > (num(r, 'last_purchase_rate') ?? 0));
    for (const r of dearer.slice(0, 2)) {
      const last = num(r, 'last_purchase_rate') ?? 0;
      const pct = Math.round((((num(r, 'rate') ?? 0) - last) / last) * 100);
      flags.push({ kind: 'warn', label: text('approvals.rateAbove', { item: str(r, 'item_name') ?? str(r, 'item_code') ?? '', pct, last: formatMoney(last, str(doc, 'currency')) }) });
    }
    if (dearer.length > 2) flags.push({ kind: 'warn', label: text('approvals.moreAbove', { count: dearer.length - 2 }) });
    const quotations = [...new Set(items.map((r) => str(r, 'supplier_quotation')).filter(Boolean))];
    if (quotations.length) flags.push({ kind: 'ok', label: text('approvals.fromQuotation', { names: quotations.join(', ') }) });
    const requests = [...new Set(items.map((r) => str(r, 'material_request')).filter(Boolean))];
    if (requests.length) flags.push({ kind: 'info', label: text('approvals.fromRequest', { names: requests.join(', ') }) });
  }
  if (doctype === 'Payment Entry') {
    const refs = Array.isArray(doc.references) ? doc.references.length : 0;
    if (refs) flags.push({ kind: 'info', label: text('approvals.against', { count: refs }) });
  }
  if (doctype === 'Expense Claim') {
    flags.push(attachments ? { kind: 'ok', label: text('approvals.receipts', { count: attachments }) } : { kind: 'warn', label: text('approvals.noReceipts') });
  }
  return flags;
}

/** Everything the card shows, read as the signed-in person (ERPNext checks the read right). */
export async function loadCard(api: Api, doctype: string, name: string): Promise<Card> {
  const metaKey = metaPath(doctype);
  const path = `${GETDOC_PATH}?${new URLSearchParams({ doctype, name }).toString()}`;
  const [metas, got] = await Promise.all([
    metaCache.get(metaKey) ?? (keptOffline(doctype) ? getKept(api, metaKey, Meta) : getChecked(api, metaKey, Meta)).then((m) => (metaCache.set(metaKey, m), m)),
    keptOffline(doctype) ? getKept(api, path, GetDoc) : getChecked(api, path, GetDoc),
  ]);
  const doc = got.docs[0];
  const meta = metas.docs.find((m) => m.name === doctype);
  const spec = SPECS[doctype];
  const info = got.docinfo;
  const who = (email: string | null | undefined) => (email ? (info?.user_info?.[email]?.fullname ?? email) : null);

  const factNames = spec?.facts ?? (meta?.fields ?? []).filter((f) => f.in_list_view && !f.hidden).map((f) => f.fieldname);
  const amountField = spec?.amount ?? GENERAL_AMOUNT.find((f) => num(doc, f) !== null);
  const amount = amountField ? money(doc, amountField, spec?.currency ? str(doc, spec.currency) : str(doc, 'currency')) : undefined;
  const partyField = spec?.party ?? GENERAL_PARTY.find((f) => str(doc, f));
  const title = meta?.title_field ? str(doc, meta.title_field) : null;
  const table = spec?.lines;
  const rows = table && Array.isArray(doc[table.table]) ? (doc[table.table] as Rec[]) : [];
  const attachments = (info?.attachments ?? [])
    .filter((a) => a.file_url)
    .map((a) => ({ name: a.name, fileName: a.file_name ?? a.name, url: a.file_url ?? '', image: IMAGE.test(a.file_name ?? a.file_url ?? '') }));

  return {
    doctype,
    name,
    modified: str(doc, 'modified'),
    state: str(doc, 'workflow_state'),
    headline: (spec?.headline ? spec.headline(doc) : null) || amount || title || name,
    party: (partyField ? str(doc, partyField) : null) ?? title,
    project: (spec?.site ?? SITE).map((f) => str(doc, f)).find(Boolean) ?? null,
    facts: factNames.map((f) => factOf(meta, doc, f)).filter((f): f is Fact => f !== null),
    lines: table ? rows.map((r) => table.line(r, doc)) : [],
    steps: [...(info?.workflow_logs ?? [])]
      .sort((a, b) => a.creation.localeCompare(b.creation))
      .map((l) => ({ state: (l.content ?? '').replace(/<[^>]*>/g, '').trim(), by: who(l.owner), at: l.creation }))
      .filter((s) => s.state),
    attachments,
    flags: flagsOf(doctype, doc, attachments.length),
    bulk: !!spec?.bulk,
    doc,
  };
}

/** Leave: the balance left after this application (HRMS's own calculation). Unknown: null. */
export async function leaveBalance(api: Api, doc: Rec): Promise<number | null> {
  const employee = str(doc, 'employee');
  const leaveType = str(doc, 'leave_type');
  const from = str(doc, 'from_date');
  if (!employee || !leaveType || !from) return null;
  try {
    return await callErp(api, 'hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on', z.coerce.number(), {
      employee,
      leave_type: leaveType,
      date: from,
    });
  } catch {
    return null;
  }
}

/** Leave: how many others of the same department are on leave on any of these days. Unknown: null. */
export async function othersOnLeave(api: Api, doc: Rec): Promise<number | null> {
  const department = str(doc, 'department');
  const from = str(doc, 'from_date');
  const to = str(doc, 'to_date');
  if (!department || !from || !to) return null;
  try {
    const rows = await callErp(api, 'frappe.client.get_list', Summaries, {
      doctype: 'Leave Application',
      fields: ['name'],
      filters: [
        ['department', '=', department],
        ['status', 'in', ['Open', 'Approved']],
        ['docstatus', '<', 2],
        ['from_date', '<=', to],
        ['to_date', '>=', from],
        ['name', '!=', str(doc, 'name') ?? ''],
      ],
      limit_page_length: 50,
    });
    return rows.length;
  } catch {
    return null;
  }
}

/** Stores: the stock at the store it leaves from, per item ("left after this"). Unknown items are left out. */
export async function stockLeft(api: Api, doc: Rec): Promise<Map<string, number>> {
  const items = Array.isArray(doc.items) ? (doc.items as Rec[]) : [];
  const from = (r: Rec) => str(r, 's_warehouse') ?? str(r, 'from_warehouse') ?? str(doc, 'from_warehouse') ?? str(doc, 'set_from_warehouse');
  const wanted = items.filter((r) => str(r, 'item_code') && from(r));
  if (!wanted.length) return new Map();
  try {
    const bins = await callErp(api, 'frappe.client.get_list', Summaries, {
      doctype: 'Bin',
      fields: ['item_code', 'warehouse', 'actual_qty'],
      filters: [
        ['item_code', 'in', [...new Set(wanted.map((r) => str(r, 'item_code')))]],
        ['warehouse', 'in', [...new Set(wanted.map(from))]],
      ],
      limit_page_length: 200,
    });
    const have = new Map(bins.map((b) => [`${str(b, 'item_code')}|${str(b, 'warehouse')}`, num(b, 'actual_qty') ?? 0]));
    // Keyed by the row's place in the item table, the same order as the card's lines.
    const left = new Map<string, number>();
    items.forEach((r, i) => {
      const k = `${str(r, 'item_code')}|${from(r)}`;
      if (have.has(k)) left.set(String(i), (have.get(k) ?? 0) - (num(r, 'stock_qty') ?? num(r, 'qty') ?? 0));
    });
    return left;
  } catch {
    return new Map();
  }
}

// ---- actions: ERPNext's workflow transitions for this person ----
export const Transitions = z.array(z.object({ action: z.string(), next_state: z.string() }));
export type Transition = z.infer<typeof Transitions>[number];
export const TRANSITIONS_METHOD = 'frappe.model.workflow.get_transitions';
export const APPLY_METHOD = 'frappe.model.workflow.apply_workflow';
export const COMMENT_METHOD = 'frappe.desk.form.utils.add_comment';
export const MODIFIED_METHOD = 'frappe.client.get_value';

const NEGATIVE = /reject|return|send back|decline|deny|cancel|hold|revert/i;
const POSITIVE = /approve|accept|verify|confirm|submit|authori[sz]e|release|pay|sanction|pass/i;
export const isNegative = (action: string) => NEGATIVE.test(action);

/** The two big buttons (no / yes) and the rest under "More", whatever names ERPNext's workflow uses. */
export function splitActions(list: Transition[]): { yes: Transition | null; no: Transition | null; more: Transition[] } {
  const yes = list.find((t) => POSITIVE.test(t.action) && !NEGATIVE.test(t.action)) ?? list.find((t) => !NEGATIVE.test(t.action)) ?? null;
  const no = list.find((t) => t !== yes && NEGATIVE.test(t.action)) ?? null;
  return { yes, no, more: list.filter((t) => t !== yes && t !== no) };
}

export class ChangedError extends Error {}

/**
 * Apply one workflow action. ERPNext loads the document fresh and checks everything; the app first checks the
 * document was not changed after the card was loaded (then nothing is sent). A reason goes in as a comment.
 */
export async function applyAction(
  api: Api,
  card: Pick<Card, 'doctype' | 'name' | 'modified'>,
  action: string,
  reason: string,
  user: { email?: string | null; name?: string | null },
) {
  if (card.modified) {
    const now = await callErp(api, MODIFIED_METHOD, z.object({ modified: z.string() }), { doctype: card.doctype, filters: card.name, fieldname: 'modified' });
    if (now.modified !== card.modified) throw new ChangedError(text('approvals.changed'));
  }
  await callErp(api, APPLY_METHOD, z.object({ name: z.string() }).passthrough(), { doc: { doctype: card.doctype, name: card.name }, action }, { post: true });
  if (reason.trim()) {
    await callErp(
      api,
      COMMENT_METHOD,
      z.unknown(),
      { reference_doctype: card.doctype, reference_name: card.name, content: `${action}: ${reason.trim()}`, comment_email: user.email ?? '', comment_by: user.name ?? '' },
      { post: true },
    ).catch(() => {}); // the action itself is done; a missing comment is not a reason to report failure
  }
}

/** "Approve all" (leave, attendance requests): the same yes-action on each, one after another; each result kept. */
export async function applyToAll(api: Api, docs: { doctype: string; name: string }[]) {
  const results: { name: string; ok: boolean; error?: string }[] = [];
  for (const d of docs) {
    try {
      const { yes } = splitActions(await callErp(api, TRANSITIONS_METHOD, Transitions, { doc: d }));
      if (!yes) throw new Error(text('workflow.none'));
      await callErp(api, APPLY_METHOD, z.object({ name: z.string() }).passthrough(), { doc: d, action: yes.action }, { post: true });
      results.push({ name: d.name, ok: true });
    } catch (e) {
      results.push({ name: d.name, ok: false, error: e instanceof Error ? e.message : String(e) });
    }
  }
  return results;
}

// ---- the order the person is working through (the Inbox sets it; the card shows "2 of 5" and moves on) ----
let queue: Item[] = [];
export const setQueue = (items: Item[]) => {
  queue = items;
};
export const currentQueue = () => queue;
/** The item is done: take it out of the list and return the one to show next (the following one, else the one before). */
export function finish(key: string): Item | null {
  const i = queue.findIndex((x) => x.key === key);
  queue = queue.filter((x) => x.key !== key);
  return i < 0 ? (queue[0] ?? null) : (queue[i] ?? queue[i - 1] ?? null);
}
