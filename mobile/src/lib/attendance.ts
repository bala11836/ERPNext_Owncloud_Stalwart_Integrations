// Attendance for Today (step T2): the person's own check-in, their team's marking, and what waits for their
// approval, from the custom_hr API (erpnext_drive_integrations.custom_hr.api, PR #38/#39). The server decides
// every role, site and shift; the app only counts and shows. Read only: the check-in, team and bulk-approval
// screens come with the attendance pilot (build guide phase 3).
import { z } from 'zod';

import { rememberServerClock } from '@/lib/capture';
import { type Api, callErp } from '@/lib/erp';

export const HR_API = 'erpnext_drive_integrations.custom_hr.api';

const Shift = z.object({
  name: z.string(),
  start: z.string(),
  end: z.string(),
  label: z.string().nullish(),
  attendance_date: z.string().nullish(),
});
const CheckInSite = z.object({
  name: z.string(),
  label: z.string(),
  latitude: z.number().nullish(),
  longitude: z.number().nullish(),
  radius_m: z.number().nullish(),
  maximum_accuracy_m: z.number().nullish(),
  shifts: z.array(Shift),
});
export type CheckInSiteT = z.infer<typeof CheckInSite>;
export const Boot = z.object({
  server_now: z.string().nullish(),
  sites: z.array(
    z.object({
      name: z.string(),
      label: z.string(),
      supervisor: z.boolean(),
      approver: z.boolean(),
      shifts: z.array(Shift),
      assets: z.array(z.object({ name: z.string(), label: z.string() })).default([]),
    }),
  ),
  check_in_sites: z.array(CheckInSite),
});
export type BootT = z.infer<typeof Boot>;

/** The attendance bootstrap; also remembers the server's clock for offline captures. */
export async function loadBoot(api: Api): Promise<BootT> {
  const boot = await callErp(api, `${HR_API}.bootstrap`, Boot);
  if (boot.server_now) await rememberServerClock(boot.server_now);
  return boot;
}
export const Mine = z.array(
  z.object({
    name: z.string(),
    site: z.string(),
    attendance_date: z.string(),
    state: z.string(),
    check_in_time: z.string().nullish(),
    check_out_time: z.string().nullish(),
  }),
);
const Team = z.object({ total: z.number(), missing: z.number() });
const Waiting = z.array(z.object({ name: z.string(), can_review: z.boolean() }));

/** The site's shift running at `now` ("HH:MM", phone time; for choosing a card only, never for a record). */
export function currentShift<S extends { start: string; end: string }>(shifts: S[], now: string): S | null {
  const within = (s: S) => (s.start <= s.end ? now >= s.start && now < s.end : now >= s.start || now < s.end);
  return shifts.find(within) ?? shifts[0] ?? null;
}

export type TodayAttendance = {
  /** Only for people who check in themselves (listed as Staff on a site). */
  self: { sites: string[]; today: z.infer<typeof Mine>[number] | null } | null;
  teams: { siteId: string; site: string; shiftId: string; shift: string; marked: number; total: number }[];
  approvals: { siteId: string; site: string; count: number }[];
};

/**
 * Null when the server has no attendance module (not deployed yet) or answers otherwise: Today then simply
 * shows no attendance cards.
 */
export async function loadTodayAttendance(api: Api, now: string, today: string): Promise<TodayAttendance | null> {
  let boot: BootT;
  try {
    boot = await loadBoot(api);
  } catch {
    return null;
  }
  const [mine, teams, approvals] = await Promise.all([
    boot.check_in_sites.length
      ? callErp(api, `${HR_API}.my_attendance`, Mine).catch(() => [])
      : Promise.resolve(null),
    Promise.all(
      boot.sites
        .filter((s) => s.supervisor)
        .map(async (s) => {
          const shift = currentShift(s.shifts, now);
          if (!shift) return null;
          try {
            const team = await callErp(api, `${HR_API}.team`, Team, { site: s.name, shift: shift.name });
            return {
              siteId: s.name,
              site: s.label,
              shiftId: shift.name,
              shift: shift.label ?? shift.name,
              marked: team.total - team.missing,
              total: team.total,
            };
          } catch {
            return null;
          }
        }),
    ),
    Promise.all(
      boot.sites
        .filter((s) => s.approver)
        .map(async (s) => {
          try {
            const pending = await callErp(api, `${HR_API}.approvals`, Waiting, { site: s.name });
            return { siteId: s.name, site: s.label, count: pending.filter((entry) => entry.can_review).length };
          } catch {
            return null;
          }
        }),
    ),
  ]);
  return {
    self: mine
      ? { sites: boot.check_in_sites.map((s) => s.label), today: mine.find((m) => m.attendance_date === today) ?? null }
      : null,
    teams: teams.filter((t): t is NonNullable<typeof t> => t !== null && t.total > 0),
    approvals: approvals.filter((a): a is NonNullable<typeof a> => a !== null && a.count > 0),
  };
}

/** "08:02" from ERPNext's "2026-11-23 08:02:41". */
export const clock = (value?: string | null) => /(\d{2}:\d{2})/.exec(value ?? '')?.[1] ?? '';

// ---- team marking (supervisor, P3c): custom_hr's `team` answer ----
export const Worker = z.object({
  employee: z.string(),
  employee_name: z.string().nullish(),
  designation: z.string().nullish(),
  machine_required: z.coerce.number().nullish(),
  state: z.string(),
  entry: z.string().nullish(),
  revision: z.number().nullish(),
  can_capture: z.boolean(),
  can_edit: z.boolean(),
});
export type WorkerT = z.infer<typeof Worker>;
export const TeamList = z.object({
  workers: z.array(Worker),
  total: z.number(),
  missing: z.number(),
  attendance_date: z.string(),
  truncated: z.boolean().nullish(),
});

/** Entries this supervisor still has to submit for approval (their own drafts). */
export const drafts = (workers: WorkerT[]) => workers.filter((w) => w.state === 'Draft' && w.can_edit && w.entry);

// ---- approval (PM, P3d): custom_hr's `approvals`, `entry` and `review_many` answers ----
export const Pending = z.array(
  z.object({
    name: z.string(),
    employee: z.string(),
    employee_name: z.string().nullish(),
    attendance_date: z.string(),
    shift: z.string(),
    attendance_status: z.string(),
    work_mode: z.string().nullish(),
    asset: z.string().nullish(),
    entry_type: z.string().nullish(),
    captured_offline: z.coerce.number().nullish(),
    check_in_time: z.string().nullish(),
    accuracy_m: z.number().nullish(),
    can_review: z.boolean(),
  }),
);
export type PendingT = z.infer<typeof Pending>[number];
export const EntryDetail = z.object({
  name: z.string(),
  photo: z.string().nullish(),
  remarks: z.string().nullish(),
  captured_at: z.string().nullish(),
  accuracy_m: z.number().nullish(),
});
export const Reviewed = z.array(
  z.object({ name: z.string(), ok: z.boolean(), error: z.string().nullish(), state: z.string().nullish() }),
);

/** "Exceptions only": what deserves a closer look before approving (captured offline, or absent). */
export const isException = (e: PendingT) => !!e.captured_offline || e.attendance_status === 'Absent';
