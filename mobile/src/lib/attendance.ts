// Attendance for Today (step T2): the person's own check-in, their team's marking, and what waits for their
// approval, from the custom_hr API (erpnext_drive_integrations.custom_hr.api, PR #38/#39). The server decides
// every role, site and shift; the app only counts and shows. Read only: the check-in, team and bulk-approval
// screens come with the attendance pilot (build guide phase 3).
import { z } from 'zod';

import { type Api, callErp } from '@/lib/erp';

export const HR_API = 'erpnext_drive_integrations.custom_hr.api';

const Shift = z.object({ name: z.string(), start: z.string(), end: z.string(), label: z.string().nullish() });
const Boot = z.object({
  sites: z.array(
    z.object({ name: z.string(), label: z.string(), supervisor: z.boolean(), approver: z.boolean(), shifts: z.array(Shift) }),
  ),
  check_in_sites: z.array(z.object({ name: z.string(), label: z.string() })),
});
const Mine = z.array(
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
const Waiting = z.array(z.object({ name: z.string() }));

/** The site's shift running at `now` ("HH:MM", phone time; for choosing a card only, never for a record). */
export function currentShift<S extends { start: string; end: string }>(shifts: S[], now: string): S | null {
  const within = (s: S) => (s.start <= s.end ? now >= s.start && now < s.end : now >= s.start || now < s.end);
  return shifts.find(within) ?? shifts[0] ?? null;
}

export type TodayAttendance = {
  /** Only for people who check in themselves (listed as Staff on a site). */
  self: { sites: string[]; today: z.infer<typeof Mine>[number] | null } | null;
  teams: { site: string; shift: string; marked: number; total: number }[];
  approvals: { site: string; count: number }[];
};

/**
 * Null when the server has no attendance module (not deployed yet) or answers otherwise: Today then simply
 * shows no attendance cards.
 */
export async function loadTodayAttendance(api: Api, now: string, today: string): Promise<TodayAttendance | null> {
  let boot: z.infer<typeof Boot>;
  try {
    boot = await callErp(api, `${HR_API}.bootstrap`, Boot);
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
            return { site: s.label, shift: shift.label ?? shift.name, marked: team.total - team.missing, total: team.total };
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
            return { site: s.label, count: (await callErp(api, `${HR_API}.approvals`, Waiting, { site: s.name })).length };
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
