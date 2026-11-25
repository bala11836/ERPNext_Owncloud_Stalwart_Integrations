// Runs a chain across the test phones, one step after another, and stops at the first failure.
// Run from mobile/: node e2e/run-chain.ts e2e/chains/smoke.json   (settings: e2e/README.md)
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { planChain, type Chain } from './chain.ts';

const file = process.argv[2];
if (!file) {
  console.error('Usage: node e2e/run-chain.ts e2e/chains/<chain>.json');
  process.exit(2);
}
const chain = JSON.parse(readFileSync(file, 'utf8')) as Chain;
const steps = planChain(chain, process.env);
const maestro = process.env.MAESTRO ?? 'maestro';
const appId = process.env.APP_ID ?? 'com.example.erp';
const out = path.join('e2e', 'results', `${path.basename(file, '.json')}-${new Date().toISOString().replace(/[:.]/g, '-')}`);

console.log(`${chain.name}: ${steps.length} steps`);
for (const [i, s] of steps.entries()) {
  console.log(`\nStep ${i + 1} of ${steps.length}: phone ${s.phone} (${s.device}) runs ${s.flow}`);
  const args = ['--device', s.device, 'test', path.join('e2e', s.flow), '-e', `APP_ID=${appId}`, '--test-output-dir', path.join(out, `${i + 1}-${s.phone}`)];
  // Windows starts maestro.bat only through the shell; every argument was checked by planChain.
  const run = spawnSync(maestro, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  if (run.status !== 0) {
    console.error(`\nFAILED at step ${i + 1} (phone ${s.phone}, ${s.flow}). Screens and logs: ${out}`);
    process.exit(1);
  }
}
console.log(`\nPASSED: all ${steps.length} steps. Screens and logs: ${out}`);
