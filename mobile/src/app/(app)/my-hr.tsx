import { router, useFocusEffect } from 'expo-router';
import { type ReactNode, useCallback, useState } from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';

import { useApiRef } from '@/auth/session';
import { NoScreenshots } from '@/components/no-screenshots';
import { Button, Row, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { formatDate, formatMoney, localToday } from '@/lib/format';
import { type MyHr as Data, type Section, loadMyHr, statusKind } from '@/lib/my-hr';
import { useTheme } from '@/theme';

const openDoc = (doctype: string, name: string) =>
  router.push({ pathname: '/doc/[doctype]/[name]', params: { doctype, name } });

/** My HR: the person's own leave, expense claims, holidays and payslips (Frappe HR's own app API). */
export default function MyHr() {
  const t = useTheme();
  const apiRef = useApiRef();
  const [data, setData] = useState<Data | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    loadMyHr(apiRef.current, localToday()).then(
      (d) => {
        setData(d);
        setError(null);
        setLoading(false);
      },
      (e: unknown) => {
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      },
    );
  }, [apiRef]);
  useFocusEffect(load);

  const heading = (key: Parameters<typeof text>[0]) => (
    <T variant="small" color="muted" style={{ paddingHorizontal: 16, paddingTop: 18, paddingBottom: 6, fontWeight: '700' }}>
      {text(key).toUpperCase()}
    </T>
  );
  const part = <S,>(s: Section<S>, empty: (d: S) => boolean, rows: (d: S) => ReactNode) =>
    'error' in s ? (
      <View style={{ paddingHorizontal: 16 }}>
        <Status kind="danger" label={text('myHr.partError', { error: s.error })} />
      </View>
    ) : empty(s.data) ? (
      <View style={{ paddingHorizontal: 16 }}>
        <Status kind="info" label={text('myHr.none')} />
      </View>
    ) : (
      rows(s.data)
    );

  return (
    <ScrollView
      style={{ backgroundColor: t.c.bg }}
      refreshControl={<RefreshControl refreshing={loading && data !== undefined} onRefresh={load} />}>
      <NoScreenshots />
      {error && (
        <View style={{ padding: 16, gap: 12 }}>
          <Status kind="danger" label={text('myHr.error', { error })} />
          <Button label={text('inbox.retry')} icon="refresh" secondary onPress={load} />
        </View>
      )}
      {data === undefined && !error && (
        <View style={{ padding: 16 }}>
          <Status kind="pending" label={text('myHr.loading')} />
        </View>
      )}
      {data === null && (
        <View style={{ padding: 16 }}>
          <Status kind="warn" label={text('myHr.noEmployee')} />
        </View>
      )}
      {data && (
        <>
          <View style={{ padding: 16, gap: 4 }}>
            <T variant="title">{data.employee?.employee_name || data.employee?.name}</T>
            <T color="muted">
              {[data.employee?.name, data.employee?.designation, data.employee?.department].filter(Boolean).join(' · ')}
            </T>
          </View>

          {heading('myHr.leaveBalance')}
          {part(
            data.balances,
            (b) => Object.keys(b).length === 0,
            (b) =>
              Object.entries(b).map(([type, v]) => (
                <Row
                  key={type}
                  title={type}
                  subtitle={text('myHr.balance', { left: v.balance_leaves ?? 0, of: v.allocated_leaves ?? 0 })}
                />
              )),
          )}

          {heading('myHr.leaves')}
          {part(
            data.leaves,
            (l) => l.length === 0,
            (l) =>
              l.map((a) => (
                <View key={a.name}>
                  <Row
                    title={`${a.leave_type}: ${formatDate(a.from_date)} – ${formatDate(a.to_date)}`}
                    subtitle={text('myHr.days', { days: a.total_leave_days ?? 0 })}
                    onPress={() => openDoc('Leave Application', a.name)}
                  />
                  <View style={{ paddingHorizontal: 16, paddingVertical: 8 }}>
                    <Status kind={statusKind(a.status)} label={a.status ?? ''} />
                  </View>
                </View>
              )),
          )}

          {heading('myHr.claims')}
          {'data' in data.summary && (
            <View style={{ paddingHorizontal: 16, gap: 6, paddingBottom: 6 }}>
              <Status
                kind="pending"
                label={text('myHr.pending', { amount: formatMoney(data.summary.data.total_pending_amount ?? 0, data.summary.data.currency) })}
              />
              <Status
                kind="ok"
                label={text('myHr.approved', { amount: formatMoney(data.summary.data.total_approved_amount ?? 0, data.summary.data.currency) })}
              />
            </View>
          )}
          {part(
            data.claims,
            (c) => c.length === 0,
            (c) =>
              c.map((claim) => (
                <View key={claim.name}>
                  <Row
                    title={`${claim.expense_type ?? claim.name}: ${formatMoney(claim.total_claimed_amount, claim.currency)}`}
                    subtitle={formatDate(claim.posting_date)}
                    onPress={() => openDoc('Expense Claim', claim.name)}
                  />
                  <View style={{ paddingHorizontal: 16, paddingVertical: 8 }}>
                    <Status kind={statusKind(claim.approval_status)} label={claim.approval_status ?? claim.status ?? ''} />
                  </View>
                </View>
              )),
          )}

          {heading('myHr.holidays')}
          {part(
            data.holidays,
            (h) => h.length === 0,
            (h) => h.map((d) => <Row key={d.holiday_date} title={formatDate(d.holiday_date)} subtitle={d.description ?? ''} />),
          )}

          {heading('myHr.payslips')}
          {part(
            data.slips,
            (s) => s.length === 0,
            (s) =>
              s.map((slip) => (
                <Row
                  key={slip.name}
                  title={`${formatDate(slip.start_date)} – ${formatDate(slip.end_date)}`}
                  subtitle={text('myHr.netPay', { amount: formatMoney(slip.net_pay, slip.currency) })}
                  onPress={() => openDoc('Salary Slip', slip.name)}
                />
              )),
          )}
          <View style={{ height: 24 }} />
        </>
      )}
    </ScrollView>
  );
}
