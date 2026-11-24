import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, View, useWindowDimensions } from 'react-native';

import { useApiRef } from '@/auth/session';
import { ApprovalCard } from '@/components/approval-card';
import { AttendanceCards } from '@/components/attendance-cards';
import { AREA_LOOK, ApprovalRow } from '@/components/approval-row';
import { Icon } from '@/components/icon';
import { OfflineStrip } from '@/components/offline-strip';
import { Sheet, SheetOption } from '@/components/sheet';
import { Button, Choice, Row, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { AREAS, type Area, type Item, arrange, finish, loadAttendanceItems, loadDocItems, setQueue } from '@/lib/approvals';
import { loadBoot } from '@/lib/attendance';
import { formatDate, formatValue } from '@/lib/format';
import { type InboxNotification, markRead, refreshInbox, useInbox } from '@/lib/inbox';
import { useTheme } from '@/theme';

const plain = (html?: string | null) => formatValue({ fieldname: 'subject', fieldtype: 'Text Editor' }, html ?? '');

/** "No site" in the site picker: documents not tied to a project (HR, head office). */
const NO_SITE = '';

/**
 * Inbox (owner's plan, 24 November 2026): every approval waiting for the person across all their sites (ERPNext's
 * Workflow Actions and custom_hr's attendance), longest waiting first, filtered by site and area; then their
 * notifications. Phone: a row opens the card. Tablet: the card opens on the right; wide (landscape): attachments
 * and history get their own column.
 */
export default function Inbox() {
  const t = useTheme();
  const apiRef = useApiRef();
  const inbox = useInbox();
  const { width } = useWindowDimensions();
  const tablet = width >= 768;
  const wide = width >= 1100;
  const [docs, setDocs] = useState<Item[]>([]);
  const [attendance, setAttendance] = useState<Item[]>([]);
  const [labels, setLabels] = useState<Map<string, string>>(new Map());
  const [area, setArea] = useState<Area | 'all'>('all');
  const [site, setSite] = useState<string | null>(null);
  const [picker, setPicker] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [done, setDone] = useState<string | undefined>();

  const reload = useCallback(() => {
    refreshInbox(apiRef.current);
    loadAttendanceItems(apiRef.current).then(setAttendance);
    loadBoot(apiRef.current).then(
      (b) => setLabels(new Map(b.sites.flatMap((s) => (s.project ? [[s.project, s.project_name || s.project] as [string, string]] : [])))),
      () => {},
    );
  }, [apiRef]);
  useFocusEffect(reload);
  useEffect(() => {
    let live = true;
    loadDocItems(apiRef.current, inbox.actions).then((items) => live && setDocs(items));
    return () => {
      live = false;
    };
  }, [apiRef, inbox.actions]);

  const all = [...docs, ...attendance];
  const inSite = all.filter((i) => site === null || (site === NO_SITE ? !i.project : i.project === site));
  const counts = AREAS.map((a) => [a, inSite.filter((i) => i.area === a).length] as const).filter(([, n]) => n > 0);
  const { longest, newer } = arrange(inSite.filter((i) => area === 'all' || i.area === area));
  const order = [...longest, ...newer];
  useEffect(() => {
    setQueue(order); // the card's "2 of 5" and its next item follow what is on screen
  });
  const projects = [...new Set(all.map((i) => i.project).filter((p): p is string => !!p))];
  const siteLabel = (p: string) => labels.get(p) ?? p;
  const shown = tablet ? (order.find((i) => i.key === selected) ?? order[0] ?? null) : null;

  const open = (item: Item) => {
    setDone(undefined);
    if (tablet) return setSelected(item.key);
    if (item.attendance) router.push({ pathname: '/approvals/attendance', params: { site: item.attendance.site, mode: item.attendance.mode } });
    else if (item.doc) router.push({ pathname: '/approvals/[doctype]/[name]', params: { doctype: item.doc.doctype, name: item.doc.name } });
  };
  const after = (key: string) => (message: string) => {
    const next = finish(key);
    setDone(message);
    setSelected(next?.key ?? null);
    reload();
  };
  const openNotification = (n: InboxNotification) => {
    if (!n.read) markRead(apiRef.current, n.name);
    if (n.document_type && n.document_name) {
      router.push({ pathname: '/doc/[doctype]/[name]', params: { doctype: n.document_type, name: n.document_name } });
    }
  };
  const heading = (label: string) => (
    <T variant="small" color="muted" style={{ paddingHorizontal: 16, paddingTop: 18, paddingBottom: 6, fontWeight: '700', letterSpacing: 0.5 }}>
      {label.toUpperCase()}
    </T>
  );
  const siteName = site === null ? text('approvals.allSites') : site === NO_SITE ? text('approvals.noSite') : siteLabel(site);

  const list = (
    <ScrollView
      style={{ flex: 1, backgroundColor: t.c.page }}
      refreshControl={<RefreshControl refreshing={inbox.loading && inbox.loaded} onRefresh={reload} />}>
      <OfflineStrip />
      <View style={{ backgroundColor: t.c.bg, paddingTop: 10, gap: 10, borderBottomWidth: 1, borderBottomColor: t.c.divider }}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={text('approvals.pickSite', { site: siteName })}
          onPress={() => setPicker(true)}
          style={{ minHeight: t.touch, flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 16 }}>
          <Icon name="site" size={t.font(22)} color={t.c.primary} />
          <T color="primary" style={{ flex: 1, fontWeight: '700' }}>
            {siteName}
          </T>
          <Icon name="chevron-down" size={t.font(22)} color={t.c.primary} />
        </Pressable>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingHorizontal: 16, paddingBottom: 12 }}>
          <Choice label={text('approvals.allCount', { count: inSite.length })} selected={area === 'all'} onPress={() => setArea('all')} />
          {counts.map(([a, n]) => (
            <Choice key={a} label={`${text(AREA_LOOK[a].label)} ${n}`} selected={area === a} onPress={() => setArea(a)} />
          ))}
        </ScrollView>
      </View>

      {inbox.error && (
        <View style={{ padding: 16, gap: 12 }}>
          <Status kind="danger" label={text('inbox.error', { error: inbox.error })} />
          <Button label={text('inbox.retry')} icon="refresh" secondary onPress={reload} />
        </View>
      )}
      {!inbox.loaded && !inbox.error && (
        <View style={{ padding: 16 }}>
          <Status kind="pending" label={text('inbox.loading')} />
        </View>
      )}
      {done && !tablet && (
        <View style={{ padding: 16 }}>
          <Status kind="ok" label={done} />
        </View>
      )}
      {inbox.loaded && order.length === 0 && (
        <View style={{ padding: 16 }}>
          <Status kind="none" label={text('inbox.noneWaiting')} />
        </View>
      )}
      {longest.length > 0 && heading(text('approvals.longest'))}
      {longest.map((i) => (
        <ApprovalRow key={i.key} item={i} selected={shown?.key === i.key} onPress={() => open(i)} />
      ))}
      {newer.length > 0 && heading(text('approvals.newer'))}
      {newer.map((i) => (
        <ApprovalRow key={i.key} item={i} selected={shown?.key === i.key} onPress={() => open(i)} />
      ))}

      {inbox.loaded && (
        <>
          {heading(text('inbox.notifications'))}
          {inbox.notifications.length === 0 ? (
            <View style={{ paddingHorizontal: 16, paddingBottom: 16 }}>
              <Status kind="none" label={text('inbox.noNotifications')} />
            </View>
          ) : (
            inbox.notifications.map((n) => (
              <Row
                key={n.name}
                title={plain(n.subject) || text('inbox.notification')}
                subtitle={[!n.read && text('inbox.unread'), formatDate(n.creation, true)].filter(Boolean).join(' · ')}
                selected={!n.read}
                onPress={() => openNotification(n)}
              />
            ))
          )}
        </>
      )}
    </ScrollView>
  );

  const pick = (p: string | null) => {
    setSite(p);
    setPicker(false);
  };
  return (
    <View style={{ flex: 1, flexDirection: 'row', backgroundColor: t.c.page }}>
      <View style={tablet ? { width: wide ? 400 : 360, borderRightWidth: 1, borderRightColor: t.c.divider } : { flex: 1 }}>{list}</View>
      {tablet && (
        <View style={{ flex: 1 }}>
          {shown?.doc && (
            <ApprovalCard key={shown.key} doctype={shown.doc.doctype} name={shown.doc.name} layout={wide ? 'wide' : 'tablet'} done={done} onDone={after(shown.key)} />
          )}
          {shown?.attendance && <AttendanceCards key={shown.key} site={shown.attendance.site} mode={shown.attendance.mode} onDone={after(shown.key)} />}
          {!shown && (
            <View style={{ padding: 24, gap: 12 }}>
              {done && <Status kind="ok" label={done} />}
              <Status kind="none" label={text('inbox.noneWaiting')} />
            </View>
          )}
        </View>
      )}
      <Sheet open={picker} title={text('approvals.siteTitle')} onClose={() => setPicker(false)}>
        <SheetOption icon="site" label={text('approvals.allSites')} detail={text('approvals.waitingCount', { count: all.length })} selected={site === null} onPress={() => pick(null)} />
        {projects.map((p) => (
          <SheetOption
            key={p}
            icon="site"
            label={siteLabel(p)}
            detail={text('approvals.waitingCount', { count: all.filter((i) => i.project === p).length })}
            selected={site === p}
            onPress={() => pick(p)}
          />
        ))}
        {all.some((i) => !i.project) && (
          <SheetOption
            icon="site"
            label={text('approvals.noSite')}
            detail={text('approvals.waitingCount', { count: all.filter((i) => !i.project).length })}
            selected={site === NO_SITE}
            onPress={() => pick(NO_SITE)}
          />
        )}
      </Sheet>
    </View>
  );
}
