import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';

import { confirmIdentity } from '@/auth/confirm';
import { useApiRef, useAuth } from '@/auth/session';
import { Icon } from '@/components/icon';
import { NoScreenshots } from '@/components/no-screenshots';
import { OfflineStrip } from '@/components/offline-strip';
import { PrivateImage } from '@/components/private-image';
import { Sheet, SheetOption } from '@/components/sheet';
import { Button, Status, T, TextArea } from '@/components/ui';
import { t as text } from '@/i18n';
import {
  type Attachment,
  type Card,
  ChangedError,
  type Flag,
  type Step,
  TRANSITIONS_METHOD,
  type Transition,
  Transitions,
  applyAction,
  applyToAll,
  currentQueue,
  isNegative,
  leaveBalance,
  loadCard,
  othersOnLeave,
  splitActions,
  stockLeft,
} from '@/lib/approvals';
import { callErp } from '@/lib/erp';
import { formatDate } from '@/lib/format';
import { useConnection } from '@/lib/saved';
import { useTheme } from '@/theme';

/** phone: one column; tablet: attachments and history under the card; wide: in their own column on the right. */
export type CardLayout = 'phone' | 'tablet' | 'wide';
const LINES_SHOWN = 5;

/** "2 of 5" in the list the person is working through, when the card was opened from it. */
export function usePosition(key: string) {
  const q = currentQueue();
  const i = q.findIndex((x) => x.key === key);
  return i < 0 ? null : text('approvals.position', { i: i + 1, n: q.length });
}

/** A step bar: what was done before (ticked), then this person's step. */
export function StepBar({ steps, current }: { steps: { label: string }[]; current: string }) {
  const t = useTheme();
  const pill = (label: string, mine: boolean, key: string) => (
    <View
      key={key}
      accessibilityLabel={mine ? label : text('approvals.stepDone', { step: label })}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 3, borderRadius: 999, backgroundColor: mine ? t.c.primary : t.c.okTint }}>
      {!mine && <Icon name="check" size={t.font(16)} color={t.c.ok} />}
      <T variant="small" style={{ fontWeight: '700', color: mine ? t.c.onPrimary : t.c.ok }}>
        {label}
      </T>
    </View>
  );
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 6 }} accessibilityLabel={[...steps.map((s) => s.label), current].join(', ')}>
      {steps.map((s, i) => pill(s.label, false, `s${i}`))}
      {pill(current, true, 'you')}
    </View>
  );
}

/** A warning or a check, on a tinted strip with its icon (never colour alone). */
export function FlagLine({ flag }: { flag: Flag }) {
  const t = useTheme();
  const tint = { ok: t.c.okTint, warn: t.c.warnTint, info: t.c.infoTint }[flag.kind];
  return (
    <View style={{ backgroundColor: tint, borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6 }}>
      <Status kind={flag.kind} label={flag.label} />
    </View>
  );
}

/** White box on the grey page, hair-line edge. */
export function Box({ children }: { children: ReactNode }) {
  const t = useTheme();
  return <View style={{ backgroundColor: t.c.bg, borderWidth: 1, borderColor: t.c.divider, borderRadius: 12, padding: 12, gap: 8 }}>{children}</View>;
}

export function Facts({ facts }: { facts: { label: string; value: string }[] }) {
  if (!facts.length) return null;
  return (
    <Box>
      {facts.map((f, i) => (
        <View key={`${f.label}-${i}`} style={{ flexDirection: 'row', flexWrap: 'wrap', columnGap: 12, rowGap: 2 }}>
          <T color="muted" style={{ minWidth: 120 }}>
            {f.label}
          </T>
          <T selectable style={{ flex: 1, minWidth: 140, fontWeight: '600' }}>
            {f.value}
          </T>
        </View>
      ))}
    </Box>
  );
}

function Attachments({ list }: { list: Attachment[] }) {
  const t = useTheme();
  const [open, setOpen] = useState<string | null>(null);
  if (!list.length) return null;
  return (
    <Box>
      <T style={{ fontWeight: '700' }}>{text('approvals.attached', { count: list.length })}</T>
      {list.map((a) => (
        <View key={a.name} style={{ gap: 8 }}>
          <Pressable
            accessibilityRole="button"
            disabled={!a.image}
            onPress={() => setOpen(open === a.name ? null : a.name)}
            style={{ minHeight: t.touch, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <Icon name={a.image ? 'image' : 'file'} size={t.font(22)} color={t.c.primary} />
            <View style={{ flex: 1 }}>
              <T>{a.fileName}</T>
              {!a.image && (
                <T variant="small" color="muted">
                  {text('approvals.fileOnComputer')}
                </T>
              )}
            </View>
            {a.image && <T color="primary" style={{ fontWeight: '700' }}>{open === a.name ? text('approve.hide') : text('approvals.open')}</T>}
          </Pressable>
          {open === a.name && <PrivateImage path={a.url} label={a.fileName} />}
        </View>
      ))}
    </Box>
  );
}

function History({ steps }: { steps: Step[] }) {
  if (!steps.length) return null;
  return (
    <Box>
      <T style={{ fontWeight: '700' }}>{text('approvals.history')}</T>
      {steps.map((s, i) => (
        <T key={i} variant="small" color="muted">
          {[s.state, s.by && text('approvals.by', { name: s.by }), formatDate(s.at, true)].filter(Boolean).join(' · ')}
        </T>
      ))}
    </Box>
  );
}

/**
 * One approval, as the owner's plan (24 November 2026): the amount (or what it is) first, who and where, the step
 * bar, the facts, warnings from ERPNext's data, the item lines, attachments and history; two big buttons for the
 * workflow's main no / yes, the rest under "More". Every action asks for Face ID, fingerprint or passcode; a
 * no-action needs a reason. ERPNext decides and re-checks everything; the app only refuses to send when the
 * document changed since it was shown.
 */
export function ApprovalCard({
  doctype,
  name,
  layout = 'phone',
  onDone,
  done,
}: {
  doctype: string;
  name: string;
  layout?: CardLayout;
  /** After an action: what happened, in words (the parent moves on to the next item). */
  onDone: (message: string) => void;
  /** What happened to the previous item, shown at the top. */
  done?: string;
}) {
  const t = useTheme();
  const apiRef = useApiRef();
  const { user } = useAuth();
  const { offline } = useConnection();
  const position = usePosition(`doc:${doctype}:${name}`);
  const [card, setCard] = useState<Card | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actions, setActions] = useState<Transition[] | null>(null);
  const [extra, setExtra] = useState<{ facts: { label: string; value: string }[]; stock: Map<string, number> }>({ facts: [], stock: new Map() });
  const [allLines, setAllLines] = useState(false);
  const [asking, setAsking] = useState<Transition | null>(null);
  const [reason, setReason] = useState('');
  const [more, setMore] = useState(false);
  const [phase, setPhase] = useState<'confirming' | 'sending' | null>(null);
  const [note, setNote] = useState<{ kind: 'danger' | 'warn' | 'ok'; label: string } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const busy = useRef(false);

  useEffect(() => {
    let live = true;
    loadCard(apiRef.current, doctype, name).then(
      (c) => {
        if (!live) return;
        setCard(c);
        setError(null);
        // Extras from ERPNext's own data; each is left out when it cannot be read.
        if (doctype === 'Leave Application') {
          Promise.all([leaveBalance(apiRef.current, c.doc), othersOnLeave(apiRef.current, c.doc)]).then(([balance, others]) => {
            if (!live) return;
            const days = Number(c.doc.total_leave_days) || 0;
            setExtra((x) => ({
              ...x,
              facts: [
                ...(balance !== null ? [{ label: text('approvals.balance'), value: text('approvals.balanceAfter', { now: balance, after: balance - days }) }] : []),
                ...(others !== null ? [{ label: text('approvals.sameDays'), value: text('approvals.othersOnLeave', { count: others }) }] : []),
              ],
            }));
          });
        }
        if (doctype === 'Stock Entry' || doctype === 'Material Request') {
          stockLeft(apiRef.current, c.doc).then((stock) => live && setExtra((x) => ({ ...x, stock })));
        }
      },
      (e: unknown) => live && setError(e instanceof Error ? e.message : String(e)),
    );
    callErp(apiRef.current, TRANSITIONS_METHOD, Transitions, { doc: { doctype, name } }).then(
      (list) => live && setActions(list),
      () => live && setActions(null),
    );
    return () => {
      live = false;
    };
  }, [apiRef, doctype, name, attempt]);

  const act = useCallback(
    async (tr: Transition, why: string) => {
      if (!card || busy.current) return;
      if (isNegative(tr.action) && !why.trim()) {
        setNote({ kind: 'danger', label: text('approvals.needReason') });
        return;
      }
      busy.current = true;
      setNote(null);
      setPhase('confirming');
      try {
        if (!(await confirmIdentity(text('workflow.confirm', { action: tr.action, name })))) {
          setNote({ kind: 'danger', label: text('workflow.notConfirmed') });
          return;
        }
        setPhase('sending');
        await applyAction(apiRef.current, card, tr.action, why, user ?? {});
        setAsking(null);
        setReason('');
        onDone(text('approvals.didAction', { action: tr.action, name, state: tr.next_state }));
      } catch (e) {
        if (e instanceof ChangedError) {
          setNote({ kind: 'warn', label: e.message });
          setAttempt((n) => n + 1); // show the new version; nothing was sent
        } else setNote({ kind: 'danger', label: e instanceof Error ? e.message : String(e) });
      } finally {
        busy.current = false;
        setPhase(null);
      }
    },
    [apiRef, card, name, onDone, user],
  );

  const sameKind = currentQueue().filter((i) => i.doc?.doctype === doctype);
  const approveAll = async () => {
    if (busy.current) return;
    busy.current = true;
    setNote(null);
    try {
      if (!(await confirmIdentity(text('approvals.confirmAll', { count: sameKind.length, doctype })))) {
        setNote({ kind: 'danger', label: text('workflow.notConfirmed') });
        return;
      }
      setPhase('sending');
      const results = await applyToAll(apiRef.current, sameKind.map((i) => ({ doctype, name: i.doc?.name ?? '' })));
      const failed = results.filter((r) => !r.ok);
      if (failed.length) setNote({ kind: 'danger', label: text('approve.partly', { done: results.length - failed.length, failed: failed.map((r) => `${r.name}: ${r.error}`).join('; ') }) });
      else onDone(text('approvals.allDone', { count: results.length }));
    } finally {
      busy.current = false;
      setPhase(null);
    }
  };

  if (error && !card) {
    return (
      <View style={{ padding: 16, gap: 12 }}>
        <OfflineStrip />
        <Status kind="danger" label={error} />
        <Button label={text('inbox.retry')} icon="refresh" secondary onPress={() => setAttempt((n) => n + 1)} />
      </View>
    );
  }
  if (!card) {
    return (
      <View style={{ padding: 16 }}>
        <Status kind="pending" label={text('approvals.loading')} />
      </View>
    );
  }

  const { yes, no, more: others } = splitActions(actions ?? []);
  const lines = allLines ? card.lines : card.lines.slice(0, LINES_SHOWN);
  const side = (
    <>
      <Attachments list={card.attachments} />
      <History steps={card.steps} />
    </>
  );
  const ask = (tr: Transition) => (isNegative(tr.action) ? (setReason(''), setAsking(tr)) : act(tr, ''));

  return (
    <View style={{ flex: 1, backgroundColor: t.c.page }}>
      <NoScreenshots />
      <View style={{ flex: 1, flexDirection: layout === 'wide' ? 'row' : 'column' }}>
        <View style={{ flex: 1 }}>
          <View style={{ backgroundColor: t.c.bg, paddingHorizontal: 16, paddingVertical: 12, gap: 6, borderBottomWidth: 1, borderBottomColor: t.c.divider }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
              <T variant="small" color="muted">
                {`${doctype} · ${name}`}
              </T>
              {position && (
                <T variant="small" color="muted" style={{ fontWeight: '700' }}>
                  {position}
                </T>
              )}
            </View>
            <T accessibilityRole="header" style={{ fontSize: t.font(layout === 'phone' ? 26 : 30), fontWeight: '800', fontVariant: ['tabular-nums'] }}>
              {card.headline}
            </T>
            {(card.party || card.project) && <T style={{ fontWeight: '600' }}>{[card.party, card.project].filter(Boolean).join(' · ')}</T>}
            <StepBar steps={card.steps.slice(-3).map((s) => ({ label: s.state }))} current={text('approvals.yourStep', { state: card.state ?? text('approvals.waiting') })} />
          </View>

          <ScrollView contentContainerStyle={{ padding: 12, gap: 10 }}>
            {done && <Status kind="ok" label={done} />}
            <OfflineStrip />
            <Facts facts={[...card.facts, ...extra.facts]} />
            {card.flags.map((f, i) => (
              <FlagLine key={i} flag={f} />
            ))}
            {card.lines.length > 0 && (
              <Box>
                {lines.map((l, i) => (
                  <View key={i} style={{ flexDirection: 'row', gap: 10, borderTopWidth: i ? 1 : 0, borderTopColor: t.c.divider, paddingTop: i ? 8 : 0 }}>
                    <View style={{ flex: 1, gap: 2 }}>
                      <T style={{ fontWeight: '700' }}>{l.title}</T>
                      {!!l.detail && (
                        <T variant="small" color="muted">
                          {l.detail}
                        </T>
                      )}
                      {extra.stock.has(String(i)) && (
                        <T variant="small" color={(extra.stock.get(String(i)) ?? 0) < 0 ? 'danger' : 'muted'}>
                          {text('approvals.stockLeft', { qty: extra.stock.get(String(i)) ?? 0 })}
                        </T>
                      )}
                    </View>
                    {!!l.amount && <T style={{ fontWeight: '700', fontVariant: ['tabular-nums'] }}>{l.amount}</T>}
                  </View>
                ))}
                {card.lines.length > LINES_SHOWN && (
                  <Pressable accessibilityRole="button" onPress={() => setAllLines(!allLines)} style={{ minHeight: t.touch, justifyContent: 'center' }}>
                    <T color="primary" style={{ fontWeight: '700' }}>
                      {allLines ? text('approvals.fewerLines') : text('approvals.moreLines', { count: card.lines.length - LINES_SHOWN })}
                    </T>
                  </Pressable>
                )}
              </Box>
            )}
            {layout !== 'wide' && side}
          </ScrollView>

          {/* The action bar stays at the bottom, the two main actions big and in thumb reach. */}
          <View style={{ backgroundColor: t.c.bg, borderTopWidth: 1, borderTopColor: t.c.divider, padding: 12, gap: 8 }}>
            {phase === 'sending' && <Status kind="pending" label={text('workflow.sending')} />}
            {note && <Status kind={note.kind} label={note.label} />}
            {offline && <Status kind="warn" label={text('approvals.needsInternet')} />}
            {!offline && actions && actions.length === 0 && <Status kind="info" label={text('workflow.none')} />}
            {(yes || no) && (
              <View style={{ flexDirection: 'row', gap: 10 }}>
                {no && (
                  <View style={{ flex: 1 }}>
                    <Button label={no.action} icon="undo" secondary tone="danger" disabled={offline || phase !== null} onPress={() => ask(no)} />
                  </View>
                )}
                {yes && (
                  <View style={{ flex: 1.4 }}>
                    <Button label={yes.action} icon="fingerprint" tone="ok" disabled={offline || phase !== null} onPress={() => ask(yes)} />
                  </View>
                )}
              </View>
            )}
            {others.length > 0 && <Button label={text('approvals.more', { actions: others.map((o) => o.action).join(' · ') })} icon="more" secondary disabled={offline || phase !== null} onPress={() => setMore(true)} />}
            {card.bulk && sameKind.length > 1 && yes && (
              <Button label={text('approvals.approveAll', { count: sameKind.length })} icon="fingerprint" secondary disabled={offline || phase !== null} onPress={approveAll} />
            )}
          </View>
        </View>
        {layout === 'wide' && (
          <ScrollView style={{ width: 320, flexGrow: 0, borderLeftWidth: 1, borderLeftColor: t.c.divider, backgroundColor: t.c.bg }} contentContainerStyle={{ padding: 12, gap: 10 }}>
            {side}
          </ScrollView>
        )}
      </View>

      <Sheet open={more} title={text('approvals.moreTitle')} onClose={() => setMore(false)}>
        {others.map((o) => (
          <SheetOption
            key={o.action}
            icon={isNegative(o.action) ? 'undo' : 'fingerprint'}
            label={o.action}
            detail={text('approvals.leadsTo', { state: o.next_state })}
            onPress={() => {
              setMore(false);
              ask(o);
            }}
          />
        ))}
      </Sheet>
      <Sheet open={!!asking} title={asking ? text('approvals.reasonTitle', { action: asking.action }) : ''} onClose={() => setAsking(null)}>
        <TextArea label={text('approvals.reason')} value={reason} onChange={setReason} />
        {note && <Status kind={note.kind} label={note.label} />}
        {asking && <Button label={text('approvals.withReason', { action: asking.action })} icon="fingerprint" tone="danger" disabled={phase !== null || !reason.trim()} onPress={() => act(asking, reason)} />}
      </Sheet>
    </View>
  );
}
