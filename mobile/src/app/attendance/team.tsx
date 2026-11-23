import { Stack, router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';
import { z } from 'zod';

import { confirmIdentity } from '@/auth/confirm';
import { useApiRef } from '@/auth/session';
import { Button, Choice, Row, Status } from '@/components/ui';
import { t as text } from '@/i18n';
import { type BootT, HR_API, TeamList, type WorkerT, drafts, loadBoot } from '@/lib/attendance';
import { callErp } from '@/lib/erp';
import { statusKind } from '@/lib/my-hr';
import { useTheme } from '@/theme';

type Team = z.infer<typeof TeamList>;

/**
 * The supervisor's team for one site and shift (custom_hr `team`): who is marked, who is not. Tap a worker to
 * mark them; "Submit for approval" sends the shift's drafts to the site's approvers (Face ID first).
 */
export default function TeamScreen() {
  const t = useTheme();
  const apiRef = useApiRef();
  const params = useLocalSearchParams<{ site: string; shift: string }>();
  const [shift, setShift] = useState(params.shift);
  const [boot, setBoot] = useState<BootT | null>(null);
  const [team, setTeam] = useState<Team | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [note, setNote] = useState<{ kind: 'ok' | 'danger' | 'pending'; label: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([loadBoot(apiRef.current), callErp(apiRef.current, `${HR_API}.team`, TeamList, { site: params.site, shift })])
      .then(([b, tm]) => {
        setBoot(b);
        setTeam(tm);
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [apiRef, params.site, shift]);
  useFocusEffect(load); // back from marking a worker: the list is fresh

  const site = boot?.sites.find((s) => s.name === params.site);
  const own = team ? drafts(team.workers) : [];

  const submitAll = async () => {
    if (busy || !own.length) return;
    setNote(null);
    if (!(await confirmIdentity(text('team.confirmSubmit', { count: own.length })))) {
      setNote({ kind: 'danger', label: text('workflow.notConfirmed') });
      return;
    }
    setBusy(true);
    const failed: string[] = [];
    for (const w of own) {
      try {
        await callErp(apiRef.current, `${HR_API}.submit`, z.unknown(), { name: w.entry }, { post: true });
      } catch (e) {
        failed.push(`${w.employee_name ?? w.employee}: ${e instanceof Error ? e.message : String(e)}`);
      }
    }
    setBusy(false);
    setNote(
      failed.length
        ? { kind: 'danger', label: text('team.submitPartly', { done: own.length - failed.length, failed: failed.join('; ') }) }
        : { kind: 'ok', label: text('team.submitted', { count: own.length }) },
    );
    load();
  };

  const open = (w: WorkerT) =>
    router.push({
      pathname: '/attendance/mark',
      params: {
        site: params.site,
        shift,
        employee: w.employee,
        workerName: w.employee_name ?? w.employee,
        machine: w.machine_required ? '1' : '0',
        entry: w.entry ?? '',
        revision: String(w.revision ?? 0),
      },
    });

  return (
    <ScrollView
      style={{ backgroundColor: t.c.bg }}
      refreshControl={<RefreshControl refreshing={loading && !!team} onRefresh={load} />}>
      <Stack.Screen options={{ title: site?.label ?? text('team.title') }} />
      <View style={{ padding: 16, gap: 12 }}>
        {error && <Status kind="danger" label={error} />}
        {!team && !error && <Status kind="pending" label={text('myHr.loading')} />}
        {site && (
          <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
            {site.shifts.map((s) => (
              <Choice
                key={s.name}
                label={text('checkIn.shift', { shift: s.label ?? s.name, start: s.start, end: s.end })}
                selected={s.name === shift}
                onPress={() => setShift(s.name)}
              />
            ))}
          </View>
        )}
        {team && (
          <Status
            kind={team.missing ? 'pending' : 'ok'}
            label={text('team.marked', { marked: team.total - team.missing, total: team.total, date: team.attendance_date })}
          />
        )}
        {note && <Status kind={note.kind} label={note.label} />}
        {busy && <Status kind="pending" label={text('checkIn.sending')} />}
        {own.length > 0 && (
          <Button label={text('team.submit', { count: own.length })} icon="fingerprint" onPress={submitAll} disabled={busy} />
        )}
        {team?.truncated && <Status kind="warn" label={text('team.truncated')} />}
      </View>
      {team?.workers.map((w) => (
        <View key={w.employee}>
          <Row
            title={w.employee_name ?? w.employee}
            subtitle={[w.designation, w.machine_required ? text('team.machine') : null].filter(Boolean).join(' · ')}
            onPress={w.can_capture || w.can_edit ? () => open(w) : undefined}
          />
          <View style={{ paddingHorizontal: 16, paddingVertical: 6 }}>
            <Status kind={w.state === 'Not recorded' || w.state === 'Returned' ? 'warn' : statusKind(w.state)} label={w.state} />
          </View>
        </View>
      ))}
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}
