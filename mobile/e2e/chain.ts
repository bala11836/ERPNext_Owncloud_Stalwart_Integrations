// A chain runs flows on the phones that play each role, one step after another (see e2e/README.md).

export type Phone = 'A' | 'B' | 'C';
export type Step = { phone: Phone; flow: string };
export type Chain = { name: string; steps: Step[] };
export type Planned = Step & { device: string };

const PHONES: readonly string[] = ['A', 'B', 'C'];
// The flow path goes onto a command line: letters, digits, '-', '_', '/' and '.' only.
const SAFE_FLOW = /^flows\/[\w/-]+\.yaml$/;

/** Each step with the adb device id of its phone (E2E_PHONE_A, _B, _C); refuses anything unclear. */
export function planChain(chain: Chain, env: Record<string, string | undefined>): Planned[] {
  if (!chain.steps?.length) throw new Error(`${chain.name}: the chain has no steps`);
  return chain.steps.map((s, i) => {
    if (!PHONES.includes(s.phone)) throw new Error(`Step ${i + 1}: phone must be A, B or C`);
    if (!SAFE_FLOW.test(s.flow)) throw new Error(`Step ${i + 1}: flow must look like flows/name.yaml`);
    const device = env[`E2E_PHONE_${s.phone}`];
    if (!device || !/^[\w.:-]+$/.test(device)) {
      throw new Error(`Step ${i + 1}: set E2E_PHONE_${s.phone} to phone ${s.phone}'s id (see "adb devices")`);
    }
    return { ...s, device };
  });
}
