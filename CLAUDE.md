# Instructions for Claude

The development and release policy in AGENTS.md is mandatory and
nonnegotiable. Read it before making any change, and follow it for every
change, including urgent fixes:

repository commit and push → deploy to the permanent test site → validate
there → promote that same tested revision to production.

Never develop directly in production or deploy uncommitted changes.

## Session routine (owner, 21 November 2026)

Two repositories: this **public** one (code, module READMEs, `docs/decisions.md`)
and a **private operations repository**, checked out next to this one as
`../unformat_erp_integrations` (branch `main`; run `git pull` first). The private
repository holds only records and private assets: the pending and priority list
(`docs/pending.md`), the production release log (`docs/production-releases.md`),
runbooks, handovers (`docs/handover-<date>.md`), deliberations, and brand assets
such as the logo. It never holds secrets (see AGENTS.md); those stay on the servers
and in the owner's password manager.

Do these without being asked:

1. **At the start of a session:** read AGENTS.md, then the newest handover in the
   private repository, the "How to use this list" and "Priority order" sections at
   the top of its `docs/pending.md`, and the open pull requests here (`gh pr list`).
   Summarise the state briefly. The owner decides what starts; do not push for it.
2. **After every merge and production update** (and after every incident or live
   change): update the private repository in the same session (release entry with the
   tested commit, rollback point and what test could not cover; the P item status)
   and push it.
3. **When the owner closes the session:** write or extend today's handover in the
   private repository (done, open items most urgent first, decisions, any secret that
   was exposed) and push it. Keep it current at milestones in case a session ends
   abruptly.
4. **P items:** related items are taken up together, tested together and merged as one
   release; each keeps its own status (see `docs/decisions.md`).

@AGENTS.md
