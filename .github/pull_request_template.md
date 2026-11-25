## What and why

## Module(s) touched
<!-- from modules.json -->

## Roles affected
<!-- Every role this change reaches (e.g. supervisor, engineer, project manager, payments approver, no-role user).
     For each: what it must see or do, what it must not, and how ERPNext refusing the rest was checked
     (hiding a screen is not security). "None" if no role sees a difference. -->
| Role | Must see / do | Must not see / do | ERPNext refuses (how checked) |
|:--|:--|:--|:--|

## Promotion plan
<!-- output of `python tools/promotion_plan.py <commit production runs> <this branch>`: stacks, steps, live settings, restarts, what test cannot cover -->

## How it was tested
- [ ] `python tools/check_repository.py`
- [ ] `python tools/run_unit_tests.py`
- [ ] **Branch deployed to the test site and validated** (required before merge).
      Tested commit: `` Result: ``
      Not covered by test (production-only files, limits): ``

## Safety
- [ ] No secrets, tokens or business data in the diff
- [ ] Third-party code/artwork licensed and attributed
- [ ] AI assistance used? Say so here:

Order: branch → test → merge → `main` → production. Production is updated only from `main`, after owner confirmation.
