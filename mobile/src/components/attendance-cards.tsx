import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ScrollView, View } from 'react-native';
import { z } from 'zod';

import { confirmIdentity } from '@/auth/confirm';
import { useApiRef } from '@/auth/session';
import { Facts, FlagLine, StepBar } from '@/components/approval-card';
import { NoScreenshots } from '@/components/no-screenshots';
import { OfflineStrip } from '@/components/offline-strip';
import { PrivateImage } from '@/components/private-image';
import { Sheet } from '@/components/sheet';
import { Button, Status, T, TextArea } from '@/components/ui';
import { t as text } from '@/i18n';
import { EntryDetail, HR_API, Pending, type PendingT, Reviewed, ToVerify, asPending, clock, isException, photoPath } from '@/lib/attendance';
import { callErp } from '@/lib/erp';
import { formatDate } from '@/lib/format';
import { callKept, useConnection } from '@/lib/saved';
import { useTheme } from '@/theme';

type Mode = 'approve' | 'verify';
type Result = { name: string; ok: boolean; error?: string | null };

/** Exceptions (captured offline, absent) first, then by check-in time. */
const ordered = (list: PendingT[]) =>
  [...list].sort((a, b) => Number(isException(b)) - Number(isException(a)) || (a.check_in_time ?? '').localeCompare(b.check_in_time ?? ''));

/**
 * A site's attendance as cards, one worker at a time (the visitor-alert look in the owner's plan): the photo, the
 * facts, Return or Approve (Verify for the engineer), and "Approve all" with one Face ID. The server decides each
 * entry (`review_many` / `verify`) and nobody reviews their own capture. The list view stays as "Show as a list".
 */
export function AttendanceCards({ site, mode = 'approve', onDone }: { site: string; mode?: Mode; onDone: (message: string) => void }) {
  const t = useTheme();
  const apiRef = useApiRef();
  const { offline } = useConnection();
  const [entries, setEntries] = useState<PendingT[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [i, setI] = useState(0);
  const [detail, setDetail] = useState<z.infer<typeof EntryDetail> | null>(null);
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState('');
  const [phase, setPhase] = useState<'sending' | null>(null);
  const [note, setNote] = useState<{ kind: 'ok' | 'danger'; label: string } | null>(null);
  const busy = useRef(false);

  const load = useCallback(() => {
    (mode === 'verify'
      ? callKept(apiRef.current, `${HR_API}.verifications`, ToVerify, { site }).then(asPending)
      : callKept(apiRef.current, `${HR_API}.approvals`, Pending, { site })
    ).then(
      (list) => {
        setEntries(ordered(list.filter((e) => e.can_review)));
        setError(null);
      },
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    );
  }, [apiRef, site, mode]);
  useEffect(load, [load]);

  const list = entries ?? [];
  const e = list[Math.min(i, Math.max(0, list.length - 1))];
  useEffect(() => {
    if (!e) return;
    let live = true;
    // The photo shown is always this entry's own: `detail.name === e.name` below.
    callErp(apiRef.current, `${HR_API}.entry`, EntryDetail, { name: e.name }).then(
      (d) => live && setDetail(d),
      () => live && setDetail(null),
    );
    return () => {
      live = false;
    };
  }, [apiRef, e]);

  const send = async (names: string[], decision: 'Approve' | 'Return', remarks: string): Promise<Result[]> => {
    if (mode === 'approve') return callErp(apiRef.current, `${HR_API}.review_many`, Reviewed, { names, decision, remarks }, { post: true });
    const results: Result[] = [];
    for (const name of names) {
      try {
        await callErp(apiRef.current, `${HR_API}.verify`, z.unknown(), { name, decision: decision === 'Approve' ? 'Verify' : 'Return', remarks }, { post: true });
        results.push({ name, ok: true });
      } catch (err) {
        results.push({ name, ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    }
    return results;
  };

  const review = async (names: string[], decision: 'Approve' | 'Return', remarks = '') => {
    if (busy.current || !names.length) return;
    busy.current = true;
    setNote(null);
    try {
      const key = decision === 'Return' ? 'approve.confirmReturn' : mode === 'verify' ? 'verify.confirmVerify' : 'approve.confirmApprove';
      if (!(await confirmIdentity(text(key, { count: names.length })))) {
        setNote({ kind: 'danger', label: text('workflow.notConfirmed') });
        return;
      }
      setPhase('sending');
      const results = await send(names, decision, remarks.trim());
      const failed = results.filter((r) => !r.ok);
      const nameOf = (n: string) => list.find((x) => x.name === n)?.employee_name ?? n;
      setAsking(false);
      setReason('');
      if (failed.length) {
        setNote({ kind: 'danger', label: text('approve.partly', { done: results.length - failed.length, failed: failed.map((r) => `${nameOf(r.name)}: ${r.error}`).join('; ') }) });
        load();
        return;
      }
      const left = list.filter((x) => !names.includes(x.name));
      const message = text(decision === 'Return' ? 'approve.returned' : mode === 'verify' ? 'verify.verified' : 'approve.approved', { count: results.length });
      if (!left.length) onDone(message);
      else {
        setEntries(left); // the next worker slides in
        setNote({ kind: 'ok', label: message });
      }
    } catch (err) {
      setNote({ kind: 'danger', label: err instanceof Error ? err.message : String(err) });
    } finally {
      busy.current = false;
      setPhase(null);
    }
  };

  if (error && !entries) return <View style={{ padding: 16 }}><Status kind="danger" label={error} /></View>;
  if (!entries) return <View style={{ padding: 16 }}><Status kind="pending" label={text('approvals.loading')} /></View>;
  if (!e) return <View style={{ padding: 16 }}><Status kind="ok" label={text(mode === 'verify' ? 'verify.none' : 'approve.none')} /></View>;

  const name = e.employee_name ?? e.employee;
  const yes = text(mode === 'verify' ? 'approvals.verify' : 'approvals.approve');
  return (
    <View style={{ flex: 1, backgroundColor: t.c.page }}>
      <NoScreenshots />
      <View style={{ backgroundColor: t.c.bg, paddingHorizontal: 16, paddingVertical: 12, gap: 6, borderBottomWidth: 1, borderBottomColor: t.c.divider }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
          <T variant="small" color="muted">
            {text('approvals.attendanceAt', { shift: e.shift, date: formatDate(e.attendance_date) })}
          </T>
          <T variant="small" color="muted" style={{ fontWeight: '700' }}>
            {text('approvals.position', { i: Math.min(i, list.length - 1) + 1, n: list.length })}
          </T>
        </View>
        <T accessibilityRole="header" style={{ fontSize: t.font(24), fontWeight: '800' }}>
          {name}
        </T>
        <StepBar
          steps={[{ label: e.entry_type === 'Self' ? text('approve.self') : text('approve.team') }]}
          current={text(mode === 'verify' ? 'approvals.youVerify' : 'approvals.youApprove')}
        />
      </View>
      <ScrollView contentContainerStyle={{ padding: 12, gap: 10 }}>
        <OfflineStrip />
        {note && <Status kind={note.kind} label={note.label} />}
        {offline && !detail && <Status kind="info" label={text('approve.photoOffline')} />}
        {detail?.name === e.name && detail.photo ? <PrivateImage path={photoPath(detail.name)} label={text('approve.photoOf', { name })} /> : null}
        <Facts
          facts={[
            { label: text('approvals.status'), value: e.attendance_status },
            ...(e.check_in_time ? [{ label: text('approvals.checkIn'), value: clock(e.check_in_time) }] : []),
            ...(e.accuracy_m != null ? [{ label: text('approvals.gps'), value: text('approve.accuracy', { accuracy: Math.round(e.accuracy_m) }) }] : []),
            ...(detail?.name === e.name && detail.remarks ? [{ label: text('approvals.remarks'), value: detail.remarks }] : []),
          ]}
        />
        {!!e.captured_offline && <FlagLine flag={{ kind: 'warn', label: text('approve.offline') }} />}
        {e.attendance_status === 'Absent' && <FlagLine flag={{ kind: 'warn', label: text('approvals.absent') }} />}
        {!e.captured_offline && e.attendance_status !== 'Absent' && <FlagLine flag={{ kind: 'ok', label: text('approvals.sentOnline') }} />}
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <View style={{ flex: 1 }}>
            <Button label={text('approvals.previous')} icon="back" secondary disabled={i <= 0} onPress={() => setI(Math.max(0, i - 1))} />
          </View>
          <View style={{ flex: 1 }}>
            <Button label={text('approvals.next')} icon="chevron-right" secondary disabled={i >= list.length - 1} onPress={() => setI(Math.min(list.length - 1, i + 1))} />
          </View>
        </View>
        <Button
          label={text('approvals.showList')}
          icon="menu"
          secondary
          onPress={() => router.push({ pathname: mode === 'verify' ? '/attendance/verify' : '/attendance/approve', params: { site } })}
        />
      </ScrollView>
      <View style={{ backgroundColor: t.c.bg, borderTopWidth: 1, borderTopColor: t.c.divider, padding: 12, gap: 8 }}>
        {phase === 'sending' && <Status kind="pending" label={text('checkIn.sending')} />}
        {offline && <Status kind="warn" label={text(mode === 'verify' ? 'verify.needsInternet' : 'approve.needsInternet')} />}
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <View style={{ flex: 1 }}>
            <Button label={text('approvals.return')} icon="undo" secondary tone="danger" disabled={offline || !!phase} onPress={() => setAsking(true)} />
          </View>
          <View style={{ flex: 1.4 }}>
            <Button label={yes} icon="fingerprint" tone="ok" disabled={offline || !!phase} onPress={() => review([e.name], 'Approve')} />
          </View>
        </View>
        {list.length > 1 && (
          <Button
            label={text(mode === 'verify' ? 'approvals.verifyAll' : 'approvals.approveAll', { count: list.length })}
            icon="fingerprint"
            secondary
            disabled={offline || !!phase}
            onPress={() => review(list.map((x) => x.name), 'Approve')}
          />
        )}
      </View>
      <Sheet open={asking} title={text('approvals.returnTitle', { name })} onClose={() => setAsking(false)}>
        <TextArea label={text('approvals.reason')} value={reason} onChange={setReason} />
        {note && <Status kind={note.kind} label={note.label} />}
        <Button label={text('approvals.returnWithReason')} icon="undo" tone="danger" disabled={!!phase || !reason.trim()} onPress={() => review([e.name], 'Return', reason)} />
      </Sheet>
    </View>
  );
}
