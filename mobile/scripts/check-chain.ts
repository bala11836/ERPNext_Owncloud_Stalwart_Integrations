// Fails (exit 1) if the chain planner stops mapping roles to phones safely. Run: pnpm test
import { planChain, type Chain } from '../e2e/chain.ts';

const env = { E2E_PHONE_A: 'emulator-5554', E2E_PHONE_C: 'R58M00TEST' };
const chain = (steps: Chain['steps']): Chain => ({ name: 'check', steps });
const refused = (f: () => unknown) => {
  try {
    f();
    return false;
  } catch {
    return true;
  }
};

const planned = planChain(chain([{ phone: 'A', flow: 'flows/today.yaml' }, { phone: 'C', flow: 'flows/inbox.yaml' }]), env);
const problems = [
  planned.map((s) => s.device).join() !== 'emulator-5554,R58M00TEST' && 'phones not mapped to their device ids',
  !refused(() => planChain(chain([{ phone: 'B', flow: 'flows/today.yaml' }]), env)) && 'a phone without a device id was accepted',
  !refused(() => planChain(chain([{ phone: 'A', flow: 'flows/today.yaml & del x' }]), env)) && 'an unsafe flow path was accepted',
  !refused(() => planChain(chain([{ phone: 'A', flow: '../today.yaml' }]), env)) && 'a flow outside flows/ was accepted',
  !refused(() => planChain(chain([]), env)) && 'an empty chain was accepted',
  !refused(() => planChain(chain([{ phone: 'A', flow: 'flows/today.yaml' }]), { E2E_PHONE_A: 'x & del' })) && 'an unsafe device id was accepted',
].filter(Boolean);

if (problems.length) {
  console.error(`Chain planner check failed:\n${problems.join('\n')}`);
  process.exit(1);
}
console.log('Chain planner: ok');
