---
name: repo-maintenance
description: Runs a quick GitHub repo health smoke test (GHAS alerts, dependabot PRs, Actions/CI health, branch protection) and reports a summary table. Use when asked to do repo maintenance, a repo health check, or "is all well" on a GitHub repo.
---

# Repo Maintenance

## Overview

Invoked manually, e.g.: "carry out repo maintenance for <org>/<repo>".
Repos are given as `<org>/<repo>` (GitHub).

This skill currently covers the initial smoke-test phase: a quick,
read-only health check, ending in a single summary table and a pause for
the user to decide next steps. It does not yet perform any fixes.

**Hard constraint:** never merge `main` into a branch directly (no
`git merge`, no `gh api .../update-branch`, no equivalent). For the user's
own branches, bring them up to date via rebase onto `main`. For Dependabot
branches, never touch the branch directly at all - ask Dependabot via a PR
comment (`@dependabot rebase`, or `@dependabot recreate` if it refuses).
See step 5 for the incident that established this rule.

## Steps

### 1. Verify `gh` access to the target repo

The user has multiple GitHub accounts logged into `gh`. The account needed
for a given org/repo may not be the currently active one, so access can fail
even though `gh` itself is authenticated.

1. Confirm `gh` is installed: `gh --version`
2. Check logged-in accounts and which is active: `gh auth status`
3. Try `gh repo view <org>/<repo>` with the currently active account.
4. If it fails with something like:
   `GraphQL: Could not resolve to a Repository with the name '<org>/<repo>'. (repository)`
   this usually means the active account lacks access, not that the repo
   doesn't exist. Switch accounts and retry:
   `gh auth switch --hostname github.com --user <other-account>`
5. Re-run `gh repo view <org>/<repo>` to confirm access.

Known account/org mappings (maintain your own list here as you discover
them, e.g.):

- Org `<some-org>` requires account `<some-github-account>`, not the
  default/personal account `<default-account>`.

Do not assume the active account is correct - always verify with
`gh repo view` before proceeding with any maintenance steps, and switch
accounts if needed.

### 2. Run the smoke test

Run all checks below, then present **one** consolidated summary table (see
"Output format") and stop. Do not fix, dismiss, merge, or otherwise act on
any finding at this stage - just report.

Use `<org>/<repo>` = target repo throughout.

**a) GHAS (GitHub Advanced Security) alerts**

```bash
gh api -X GET repos/<org>/<repo>/dependabot/alerts -f state=open \
  --jq '.[] | {number, severity: .security_advisory.severity, package: .dependency.package.name, summary: .security_advisory.summary}'

gh api -X GET repos/<org>/<repo>/code-scanning/alerts -f state=open \
  --jq '.[] | {number, severity: .rule.severity, rule: .rule.id, path: .most_recent_instance.location.path}'

gh api -X GET repos/<org>/<repo>/secret-scanning/alerts -f state=open \
  --jq '.[] | {number, secret_type, created_at}'
```

`[]` (empty, exit 0) means clean for that alert type - valid "all clear",
not an error.

**b) Open Dependabot PRs**

```bash
gh pr list --repo <org>/<repo> --author "app/dependabot" --state open
```

**c) Recent Actions failures**

```bash
gh run list --repo <org>/<repo> --limit 20 --json databaseId,name,conclusion,headBranch,event,createdAt \
  --jq '.[] | select(.conclusion=="failure")'
```

`--limit 20` only covers the most recent runs across all workflows
combined, so an infrequent (e.g. scheduled) workflow that's been silently
failing for a long time can be missed here - covered by check (e) below.

**d) Branch protection on the default branch**

```bash
gh repo view <org>/<repo> --json defaultBranchRef --jq '.defaultBranchRef.name'
gh api repos/<org>/<repo>/branches/<default-branch>/protection
```

A 404 means branch protection is **not enabled at all** - flag immediately.
If present, note in particular: `required_status_checks.contexts`,
`required_pull_request_reviews` (review count, code owner requirement),
`enforce_admins.enabled`, `allow_force_pushes`/`allow_deletions`.

Then validate the required checks are still real (not stale/renamed jobs)
by comparing against an actual recent/open PR's checks:

```bash
gh pr checks <pr-number> --repo <org>/<repo>
```

Any context in `required_status_checks.contexts` missing from this list is
a stale/broken requirement. A required check showing `fail` (as opposed to
missing) is a currently-failing gate, not stale - fold it into (c)/(e).

**e) Per-workflow last-run status**

Complements (c): catches infrequently-run workflows failing silently
outside the last-20-runs window, and disabled workflows.

```bash
gh api repos/<org>/<repo>/actions/workflows --jq '.workflows[] | {id, name, path, state}'

gh api -X GET repos/<org>/<repo>/actions/workflows/<workflow-id>/runs -f per_page=1 \
  --jq '.workflow_runs[0] | {name, conclusion, created_at, event}'
```

Flag: any workflow with `state != "active"`, and any workflow whose last
run `conclusion` is `failure`.

### 3. Judge repo infrastructure readiness for contributions

Separate from the raw smoke-test facts (step 2d), this step forms an
explicit judgment: is the repo actually in a state where a normal
contribution (a PR) can be reviewed and merged? Synthesize, don't just
re-list.

Inputs already gathered in step 2d cover most of it:

- Branch protection enabled?
- Required checks are real/currently produced (not stale)?

Two more checks to add here:

```bash
# Are Actions enabled for the repo at all, and what's allowed to run?
gh api repos/<org>/<repo>/actions/permissions

# Default workflow token permissions (ties to GHAS "missing workflow
# permissions" style findings - overly broad default is a smell, but
# absence of "write" is the main thing to confirm)
gh api repos/<org>/<repo>/actions/permissions/workflow
```

Judgment rules of thumb:

- `enabled: false` on actions/permissions -> 🛑, nothing can run, contributions structurally blocked.
- `default_workflow_permissions: write` -> ⚠️, broader than needed by default (not blocking, but a hardening note).
- Missing branch protection, or a required check context that's stale/missing -> 🛑, contributions cannot be safely merged as configured.
- `enforce_admins: false` -> always mention as a note, but do not treat as blocking on its own; team may accept this as a deliberate exception. Revisit with more nuance later.

CODEOWNERS is assumed valid and is **not** independently checked by this
skill (GitHub itself validates syntax); do not add path-matching or
existence checks for it.

"Checks stuck permanently skipping/pending" is not currently treated as a
concern for this repo/team - not checked for now.

Produce one verdict line for this step, e.g.:

> Repo infra: ✅ ready for contributions (branch protection enabled, required checks valid, Actions enabled, default token permissions read-only). Note: `enforce_admins` is `false`.

**Open gap:** so far this step has only been exercised on a repo where
everything came back fine (✅). We do not yet have agreed remediation
guidance for the ⚠️/🛑 cases (e.g. branch protection missing, a required
check stale, Actions disabled). The next time step 3 turns up a real
finding, stop and work out with the user what the recommended next action
is, then update this section of the skill with that guidance instead of
improvising silently.

### 4. Output format

Present findings as a single table, high-level only (no raw JSON, no full
alert dumps) - drill-down details stay available on request, not dumped by
default.

| Check | Status | Detail |
|---|---|---|
| GHAS: Dependabot alerts | ⚠️ / ✅ | count by severity, e.g. "8 open (5 high, 3 medium)" |
| GHAS: Code scanning | ⚠️ / ✅ | count, or "0 open" |
| GHAS: Secret scanning | ⚠️ / ✅ | count, or "0 open" |
| Open Dependabot PRs | ℹ️ | count, e.g. "3 open (pre-commit, uv, github-actions groups)" |
| Recent Actions failures | ⚠️ / ✅ | count + short pattern, e.g. "4 failures, recurring: uv/pymdown-extensions update on main" |
| Branch protection | ✅ / ⚠️ / 🛑 | enabled/not enabled + notable gaps, e.g. "enabled, but enforce_admins=false" |
| Required checks validity | ✅ / 🛑 | "valid" or which context(s) are stale/missing |
| Per-workflow health | ✅ / ⚠️ | any disabled workflows or workflows whose last run failed |
| Repo infra readiness (contributions) | ✅ / ⚠️ / 🛑 | one-line verdict from step 3, e.g. "ready - Actions enabled, checks valid; note: enforce_admins=false" |

Status symbols: ✅ fine, ℹ️ informational/routine (no action implied), ⚠️
worth a look, 🛑 significant/urgent (e.g. no branch protection, stale
required check, secret scanning hit).

After the table: stop and wait for the user's input on how to proceed. Do
not take any corrective action automatically.

### 5. Dependabot PR triage: approve & merge the trivial ones

Only after the smoke test/readiness assessment has been presented and the
user has decided to proceed with cleanup. This step handles the low-risk
case; anything not covered below is left alone and just noted.

Dependabot PRs are grouped by ecosystem so they don't intersect (e.g.
`github-actions`, `uv`, `pre-commit` as separate grouped PRs) - this is the
normal setup for repos maintained with this skill, not something to fix.

For each open dependabot PR, check in order and stop at the first failing
condition:

1. **Required checks pass.**

   ```bash
   gh pr checks <pr-number> --repo <org>/<repo>
   ```

   Only the checks listed in branch protection's `required_status_checks.contexts`
   matter here (e.g. `build`, `Governance checks`); other checks showing
   `skipping` (e.g. `deploy`, `CodeQL` on a docs/dep-only change) are fine to
   ignore. Any required check `fail` -> stop, note the PR as blocked, do not
   touch it further.

2. **No unresolved review conversations.**

   ```bash
   gh api graphql -f query='
   query($owner:String!, $repo:String!, $pr:Int!) {
     repository(owner:$owner, name:$repo) {
       pullRequest(number:$pr) {
         reviewThreads(first:50) { nodes { isResolved isOutdated } }
       }
     }
   }' -f owner=<org> -f repo=<repo> -F pr=<pr-number> \
     --jq '.data.repository.pullRequest.reviewThreads.nodes'
   ```

   Any thread with `isResolved: false` -> stop, note the PR as blocked (needs
   human attention), do not touch it further.

3. **Approve and merge.** If both above pass:

   ```bash
   gh pr review <pr-number> --repo <org>/<repo> --approve --body "Automated repo-maintenance: all required checks pass, no unresolved conversations."
   ```

   Then check the repo's allowed merge methods before merging - not all repos
   allow squash:

   ```bash
   gh api repos/<org>/<repo> --jq '{allow_merge_commit, allow_squash_merge, allow_rebase_merge}'
   ```

   Use whichever is allowed (prefer squash if available, else merge commit,
   else rebase). Use `--auto` since the branch is commonly `behind` main
   (branch protection has `required_status_checks.strict: true`, so checks
   must re-validate against latest `main` before merge can complete):

   ```bash
   gh pr merge <pr-number> --repo <org>/<repo> --merge --auto   # or --squash / --rebase, whichever is allowed
   ```

   A `GraphQL: Merge method X merging is not allowed on this repository`
   error means that method is disabled for the repo - fall back to the next
   allowed method rather than erroring out.

   **If `mergeStateStatus` is `BEHIND`:** the PR branch needs to be updated
   against `main` before checks can re-validate and auto-merge can proceed.

   **Never use `gh api -X PUT repos/<org>/<repo>/pulls/<pr>/update-branch`
   (or any direct merge-main-into-branch action) on a Dependabot branch.**
   This repo's convention is: own feature branches get rebased on `main`;
   Dependabot branches are updated by asking Dependabot itself, via a PR
   comment:

   ```bash
   gh pr comment <pr-number> --repo <org>/<repo> --body "@dependabot rebase"
   ```

   Wait for Dependabot to push the rebased commit(s), then re-check
   `mergeStateStatus`/checks before merging.

   If Dependabot replies that the PR "has been edited by someone other than
   Dependabot" (e.g. because this rule was violated previously, or a human
   pushed to the branch), it will refuse to rebase. Recover with:

   ```bash
   gh pr comment <pr-number> --repo <org>/<repo> --body "@dependabot recreate"
   ```

   This makes Dependabot force-push a clean recreated branch from scratch,
   discarding any manual edits/merge commits. Confirmed working: turns a
   polluted branch (`mergeable_state: blocked` after a bad merge-commit) back
   into a single clean commit with `mergeable: true`. Note this may reset
   review state (a previous approval no longer applies to the new commit) -
   re-approve after recreation if the checks/conversation gates still pass.

After processing all open dependabot PRs, report a short list: which were
approved+queued for auto-merge, and which were left alone with the reason
(failing required check / unresolved conversation).

Do not batch-merge blindly - each PR is evaluated independently, and a
passing PR earlier in the list does not imply later ones are safe.

### Notes on `gh api` usage

- Prefer `gh api -X GET ... -f key=value --jq '...'` explicitly. Omitting
  `-X GET` while combining `-f` filters with `--jq` has produced spurious
  404s in practice; pinning the method avoided it.
- An empty JSON array `[]` with exit code 0 is a valid "nothing found"
  result, not an error. A real error returns a `{"message": ...}` body and
  non-zero exit.
