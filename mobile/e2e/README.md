# Robot tests on phones (Maestro)

A robot taps through the app on real and virtual phones, the way a person would, and checks what each screen
shows. A **chain** runs steps on different phones one after another, so one role's action can be checked on the
next role's phone (for example supervisor, then engineer, then project manager).

## Phones

| Phone | Plays | What it is |
|:--|:--|:--|
| A | Supervisor, staff | Android virtual phone on the test PC |
| B | Engineer | Android virtual phone on the test PC (small screen) |
| C | Project manager, money and HR approvers | A real Android phone on USB (real fingerprint, ringtone, camera) |

A virtual tablet runs in place of phone A or B for the tablet layouts. Each phone is signed in **once by hand**
with its test account (passkeys can't be automated, by design); after that the flows run with the app's saved
sign-in. No passwords, keys or account names are stored in any file here.

## Setup (once per PC)

1. Java 17 and the Android SDK (platform-tools, emulator).
2. Maestro, pinned: CLI **2.12.1** from `github.com/mobile-dev-inc/Maestro/releases/tag/cli-2.12.1`
   (`maestro.zip`, SHA-256 `54dbb0716425626604973cbb374c585ca30272375d9ce15177a1152765ddd9d7`). Check the digest
   before unpacking. Keep usage reporting off: set `MAESTRO_CLI_NO_ANALYTICS=1`.
3. Never use Maestro Cloud, `maestro cloud` or `--analyze`: they send the app and screenshots of test-site data to
   an outside service.
4. The app on each phone points at the **test site** (`EXPO_PUBLIC_ERP_URL`). Never run these flows against
   production.

## Run

From `mobile/`:

```bash
# one flow on one phone (adb devices lists the ids)
maestro --device <id> test e2e/flows/today.yaml -e APP_ID=com.example.erp

# a chain: each step on its phone, stops at the first failure
E2E_PHONE_A=<id> E2E_PHONE_B=<id> E2E_PHONE_C=<id> MAESTRO=<path to maestro> node e2e/run-chain.ts e2e/chains/smoke.json
```

Screenshots and logs go to `e2e/results/` (ignored by git: they show test-site data). On the real phone, touch the
fingerprint sensor when the app lock asks.

## Files

- `flows/`: one file per screen check. `_open.yaml` opens the app and waits for Today; the others build on it.
  Flows tagged `read-only` change nothing in ERPNext (Outdoor mode is a setting on the phone only).
- `chains/`: which flow runs on which phone, in order.
- `chain.ts`, `run-chain.ts`: the chain runner (checked by `scripts/check-chain.ts` in `pnpm test`).

The full list of screens and test points is in the test plan (Round 0 to 3); flows that create or approve
documents come once the test site has the test accounts and two test sites.
