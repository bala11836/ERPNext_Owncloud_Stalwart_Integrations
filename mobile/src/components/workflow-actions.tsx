import { useEffect, useRef, useState } from 'react';
import { View } from 'react-native';
import { z } from 'zod';

import { confirmIdentity } from '@/auth/confirm';
import { useApiRef } from '@/auth/session';
import { Button, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { callErp } from '@/lib/erp';
import { refreshInbox } from '@/lib/inbox';

const Transitions = z.array(z.object({ action: z.string(), next_state: z.string() }));
type Transition = z.infer<typeof Transitions>[number];

export const TRANSITIONS_METHOD = 'frappe.model.workflow.get_transitions';
export const APPLY_METHOD = 'frappe.model.workflow.apply_workflow';

/**
 * The workflow actions ERPNext allows the person on this document (Approve, Reject, ...), each confirmed with
 * Face ID, fingerprint or passcode. ERPNext checks everything again when the action is applied (the role, the
 * current state, no self-approval) and its refusal is shown as it gives it.
 */
export function WorkflowActions({ doctype, name }: { doctype: string; name: string }) {
  const apiRef = useApiRef();
  const [transitions, setTransitions] = useState<Transition[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const actionInProgress = useRef(false);
  const [phase, setPhase] = useState<'confirming' | 'sending' | null>(null);
  const [attempt, setAttempt] = useState(0);
  const doc = { doctype, name };

  useEffect(() => {
    let live = true;
    callErp(apiRef.current, TRANSITIONS_METHOD, Transitions, { doc: { doctype, name } }).then(
      (list) => live && setTransitions(list),
      (e: unknown) => live && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      live = false;
    };
  }, [apiRef, doctype, name, attempt]);

  const act = async (tr: Transition) => {
    if (actionInProgress.current) return;
    actionInProgress.current = true;
    setPhase('confirming');
    setError(null);
    setDone(null);
    try {
      if (!(await confirmIdentity(text('workflow.confirm', { action: tr.action, name })))) {
        setError(text('workflow.notConfirmed'));
        return;
      }
      setPhase('sending');
      await callErp(apiRef.current, APPLY_METHOD, z.object({ name: z.string() }), { doc, action: tr.action }, { post: true });
      setDone(text('workflow.done', { action: tr.action, state: tr.next_state }));
      setTransitions(null);
      setAttempt((n) => n + 1); // the next state may offer this person other actions
      refreshInbox(apiRef.current);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      actionInProgress.current = false;
      setPhase(null);
    }
  };

  if (!transitions && !error && !done) return null;
  return (
    <View style={{ gap: 12, padding: 16 }}>
      {phase === 'sending' && <Status kind="pending" label={text('workflow.sending')} />}
      {done && <Status kind="ok" label={done} />}
      {error && <Status kind="danger" label={error} />}
      {transitions && transitions.length > 0 && (
        <>
          <T variant="small" color="muted" style={{ fontWeight: '700' }}>
            {text('workflow.heading').toUpperCase()}
          </T>
          {transitions.map((tr, i) => (
            <Button
              key={tr.action}
              label={tr.action}
              icon="fingerprint"
              secondary={i > 0}
              disabled={phase !== null}
              onPress={() => act(tr)}
            />
          ))}
        </>
      )}
      {transitions && transitions.length === 0 && !done && <Status kind="info" label={text('workflow.none')} />}
    </View>
  );
}
