# Human tasklist

**For the human only.** One place that lists every action **you** must take:
AWS applies and secrets, approvals of protected files, decisions, merges, and the
recurring sweeps. It is an **index**: each item links to the document that holds
the exact commands, so this file stays short and those docs stay the source of
truth. Where this disagrees with a linked doc, the linked doc wins; fix this file.

**What is not here.** Work a Claude Code cloud session can do without you
(Docker and network verification runs, the Terraform static check, drafts,
reviews, the re-audit) is in [`cloud-tasklist.md`](cloud-tasklist.md), with IDs
`CC1`-`CC28`. Earlier versions of this file listed those items as yours only
because the local sandbox has no Docker and no shell network. They are moved,
not dropped: see "Moved to the cloud list" at the end. Rows below that a cloud
task needs, or that follow one, name it in the *Cloud link* column; the cloud
list names these rows back. If the two lists disagree, fix both.

How the pieces fit:

| Document | What it holds | Relationship to this file |
|---|---|---|
| `_docs/cloud-tasklist.md` | What Claude Code cloud sessions do, in order, with the human step each one needs | The other half of this list. Every cross-reference runs both ways. |
| `_docs/aws-setup.md` | The ordered AWS/GitHub runbook (account, region, budget, bootstrap, secrets, SES, nightly stop, teardown). | The detail for §A. |
| `_docs/terraform-verify.md` | How to statically check and apply/verify the `terraform/` modules (§1-§6). | The detail for the Terraform items in §A. |
| `_docs/pending-verification.md` | **Per-issue** checklist of every step a sandbox can't run (Docker/network/AWS), ticked off as each passes. | The per-issue commands behind the cloud verification runs and the AWS legs. |
| `_docs/human-cheatsheet.md` | The git / review / merge workflow (branches, PRs, protected files, sweeps). | The detail for §C and §D. |

**Status key:** ☐ to do · ◐ in progress / partly done · ☑ done. Update the box
when you finish an item.

Last updated: 2026-10-25.

---

## A. One-time AWS + GitHub setup (do once, in order)

The submission deployment. Full detail and timings in `_docs/aws-setup.md` (the
"Checklist" table) and `_docs/terraform-verify.md`. **You** run every
`terraform apply` and the first deploy; no agent holds AWS credentials. The IDs
A1-A13 are kept because other documents cite them. A4 and A5 moved to the cloud
list (CC9, CC10); the gaps in the numbering are those two.

| # | Action | Where | Doc | Cloud link | Status |
|---|---|---|---|---|---|
| A1 | Account hygiene, pick the region, set a budget alert | AWS console | `aws-setup.md` §1-§3 | none | ☐ |
| A2 | Decide the hostname form and how you reach the server (SSM, no SSH) | decision | `aws-setup.md` §4-§5 | none | ☐ |
| A3 | GitHub: create the `dev` and `production` environments (you as required reviewer on `production`). **Also limit `dev` deployments to the `main` branch** (deployment branches setting): the dev role's trust policy moves from the branch to the environment (CC29, review finding F1), so this setting becomes the branch limit | GitHub settings | `aws-setup.md` §6 | **Pairs with CC29** (done) | ◐ `dev` branch limit set to `main` 2026-10-25. Still to do: create the `production` environment with you as required reviewer, if not already |
| A6 | Apply in order `bootstrap/` → `deploy-roles/` → `server/`; copy the two role ARNs into the GitHub variables `AWS_DEV_ROLE_ARN` / `AWS_PROD_ROLE_ARN` and `AWS_REGION`; record the Elastic IP + hostnames. **Read first:** the pre-apply review (CC10, done: `_docs/reviews/2026-10-25-terraform-pre-apply-review.md`) and the Terraform static check (CC9, done: `fmt` and `validate` pass on all three modules after one fix, F7). The review found two High defects (dev trust `sub` mismatch; both secrets must exist before the server apply). CC29 fixed them in the code and it is on `main` (PR 203, merged 2026-10-25). **Fresh account:** the example `terraform.tfvars` reuses an existing GitHub OIDC provider (`create_oidc_provider = false`); if your account has none (IAM → Identity providers), set it to `true` and drop the ARN line. Decide go / no-go | your machine (AWS) | `aws-setup.md` §6-§7, `terraform-verify.md` §3 | **Needs CC9, CC10 (done), CC29** | ☐ |
| A7 | Add the submission secrets to Secrets Manager: one JSON secret per environment, `vuln-triage/dev` and `vuln-triage/prod`. Dev needs only `GITHUB_READ_TOKEN` (before A13 seeding; without it GitHub allows about 60 requests an hour) because dev falls back to a throwaway database password; prod needs `POSTGRES_PASSWORD`. The Grafana and responder secrets are local-only and do **not** go in AWS (`aws-setup.md` §8). **Ordering:** the server apply (A6) no longer needs the secrets to exist (CC29 removed the lookup, 2026-10-25), so they can be created after it, before the first dev deploy (prod before the first prod deploy) | AWS console | `aws-setup.md` §8 | **Pairs with CC29** (review finding F2) | ☐ |
| A8 | **Re-apply `deploy-roles/`** after task 21 (#142): the dev role gained a read-only `ec2:DescribeInstances`. ARN unchanged; the 2nd plan shows "No changes". Can be folded into A6 | your machine (AWS) | `terraform-verify.md` §6 | none | ☐ |
| A9 | First dev deploy. **Before it:** `AWS_REGION`, `AWS_DEV_ROLE_ARN` and `AWS_PROD_ROLE_ARN` set as GitHub repository variables (`aws-setup.md` §6.2); after the first image push, set the GHCR packages (backend, frontend) to **public** (§6.3; the server pulls with no credential, so a private package fails the deploy) and re-run the failed deploy. Then confirm `https://dev.<eip>.sslip.io` answers and the deploy log names an image digest → closes **#141** | push to `main` + AWS | `terraform-verify.md` §4 | **Unblocks CC2** (URL for the README) and CC11 (seed run) | ☐ |
| A10 | Email route: verify the SES sender identity (and the demo recipient, SES sandbox); settle the SES `VERIFY:` items. Needed before task 37 delivers on AWS | AWS console | `aws-setup.md` §9, `pending-verification.md` #156 | The MailHog leg of #156 is CC14; only the SES leg is here | ☐ |
| A11 | Nightly stop on by default; switch it **off** while graders may visit; activate the `project` cost-allocation tag | AWS console / Terraform var | `aws-setup.md` §10 | none | ☐ |
| A12 | Add the **prod** secret `vuln-triage/prod` (at least `POSTGRES_PASSWORD`), then **promote to production** (task 18 / #143): Actions → deploy → Run workflow, approve the `production` environment, confirm `https://app.<eip>.sslip.io` answers and `dev`/`prod` share the digest; rollback = re-run with the previous tag → closes **#143** | AWS console + GitHub Actions | `aws-setup.md` §8 + "Production promotion and rollback", `terraform-verify.md` §7 | **Unblocks CC2** (rollback evidence for the README) | ☐ |
| A13 | **Register the pilot seed data** (task 22 / #144): confirm the repos in `deploy/pilot-seed.json`, then `python deploy/seed-pilot.py --base-url https://dev.<eip>.sslip.io/api --username <security-lead>` (**the base URL ends in `/api`**; the earlier wording without it would have hit the dashboard, not the API); confirm each asset shows a scan status and ≥1 finding on the dev dashboard → closes **#144**. The `package-lock.json` pre-check and the draft seed file are CC11 | your machine → dev URL | `aws-setup.md` "Pilot seed data" | **Needs CC11** (draft) and A9 (URL) | ☐ |
| A14 | **Create the public reviewer account on dev.** The README publishes `reviewer` / `vt-reviewer-demo` for the dev URL (decision 2026-10-25: reviewers are anonymous, so the password is public by design). Run the one command in `aws-setup.md` "Public reviewer account (A14)" from a Session Manager session; read the risks there first (keep mail off or SES in the sandbox on dev; the account can be locked by strangers; keep nothing real on dev). Then replace `<elastic-ip>` in the README's live-demo table and in Deployment with the real address. Do **not** create it on prod | AWS Session Manager (server) | `aws-setup.md` "Public reviewer account (A14)" | **Follows A9; then fills CC2's URL placeholders** | ☐ |

> **Dependency order:** A1-A3 need no repo code. A6 is the first apply and now
> waits on CC9 and CC10 (both cloud, both safe: no AWS credentials). A8 can fold
> into A6 if you apply after #142 is merged. A9 is the end-to-end gate for dev.
> A12 needs A3's `production` environment, A6's `AWS_PROD_ROLE_ARN` and the
> `vuln-triage/prod` secret; it needs **no** Terraform re-apply. A13 needs A9 and
> a `security lead` account (the operator create-user command, #176).

## B. Approvals that unblock Claude Code cloud tasks

Small human steps whose only purpose is to let a cloud task run. Each names the
cloud tasks it unblocks. Ask-before rules are in `AGENTS.md` (installs,
system changes, protected files).

| # | Action | Detail | Cloud link | Status |
|---|---|---|---|---|
| B1 | **Allow Docker in cloud sessions.** Either approve the protected `Makefile` and `AGENTS.md` change for #48 (`make docker-start` / `docker-stop`, gated on `CLAUDE_CODE_REMOTE=true`, no `sudo`; as a `HUMAN_APPROVED=1` commit and an approval record on #48), or tell the session it may run `sudo dockerd` by hand each time | `_docs/cloud-sessions.md` §5.1; `roadmap.md` item T2 | **Unblocks CC13**, then CC14-CC21 | ◐ Approved 2026-10-25 for the manual route; `dockerd` runs in the current session only (`.scratch/docker_start.sh`, undo `.scratch/docker_stop.sh`). #48's protected targets still need their exact diff approved so a new session does not need this again |
| B2 | **Approve installing Terraform** for the static check (into `.scratch/` or the session; not kept after the session), or choose the push-check image route (needs B1) | `terraform-verify.md` §1; `AGENTS.md` (installs need asking) | **Unblocks CC9** | ☑ Approved 2026-10-25. Used the pinned `hashicorp/terraform:1.17.0` image through Docker, so nothing was installed on the host |
| B3 | **Approve protected `.github/` changes** as their own `HUMAN_APPROVED=1` commits: #159's `verify.yml` change (alert job to nightly + manual), and later #67 | `human-cheatsheet.md` §0, §5 | **Unblocks CC20**, CC22 | ☐ |
| B4 | **Decide how #140's lockfiles reach PR #167.** A cloud session can push only its own `claude/*` branch, not `feat/140-security-scan`. Either merge or cherry-pick the session's lockfile commits into that branch, or start the session on it | `pending-verification.md` #140 | **Shapes CC12** | ☐ |
| B5 | **Confirm and close the issues the cloud runs verify.** After a cloud task posts its result, check it and close the issue (or say close it): #140, #155, #157, #158 (Grafana leg), #159, #172, #174, #193, #181, #199, #201 | `pending-verification.md` (each issue's section) | **Follows CC12, CC14-CC20** | ☐ |
| B6 | **Change the cloud environment's network policy** only if CC8 finds a needed host blocked (Terraform registry, `ghcr.io`, advisory sources) | `read_documentation` topic `environment.network`; Claude settings | **Follows CC8**, unblocks CC9, CC12, CC14 | ◐ Done 2026-10-25 for `registry.terraform.io` and `releases.hashicorp.com`; CC9 then ran. **Open again for the hosts below.** Still untested: the advisory sources for #140 and GitHub raw. Original ask (kept for the record):  The proxy refused `registry.terraform.io` and `checkpoint-api.hashicorp.com`. In the cloud environment's settings (title bar menu, Edit, Network access) add `registry.terraform.io` and `releases.hashicorp.com` under Allowed domains, or use a broader level. Then CC9 can run `init` and `validate`. Steps: https://code.claude.com/docs/en/cloud-environments#network-access . **New ask (2026-10-25):** add `ghcr.io` and `pkg-containers.githubusercontent.com` (GitHub's container blob host). The backend Dockerfile copies `uv` from `ghcr.io/astral-sh/uv:0.13.1`, and the proxy returned Forbidden for the blob host, so no Compose job that builds the backend image can run in the cloud (CC14, CC17, CC18, CC26). Docker Hub image pulls already work. If the image build then fails on `uv sync` or `npm ci` inside the build container, the build network cannot reach PyPI or npm and needs the same treatment; I will report it rather than guess |
| B7 | **Decide how a cloud session gets a `.env`.** `make compose-up` and the observability stack need one (`POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, and so on). The session's permission settings deny writing `.env`, and I did not work around that. Options: allow writing a throwaway `.env` in cloud sessions (a protected `.claude/` settings change), add a `make` target that creates one from `.env.example` with throwaway values (a protected `Makefile` change), or leave those two runs to your machine | `.env.example`; `AGENTS.md` ("never open `.env`") | **Unblocks CC15, CC26** | ☐ |
| B8 | **Approve `make demo`** (optional): a one-command local reviewer demo. Needs a protected `Makefile` and `AGENTS.md` change; the exact diff is in `_docs/make-demo-proposal.md`. The README already gives the same steps as plain commands, so this only makes it easier for reviewers | `_docs/make-demo-proposal.md` | **Unblocks CC32** | ☑ Approved and applied 2026-10-25 (`Makefile` `7beafd9`, `AGENTS.md` `936ca53`) |

## C. Merges and protected-file approvals (as PRs arrive)

Every piece of agent work lands as a PR you review and merge. The method (branches,
reading the whole diff, protected-file approval with `HUMAN_APPROVED=1`,
merge-commit only) is in `_docs/human-cheatsheet.md`.

| # | Action | Cloud link | Status |
|---|---|---|---|
| C1 | **Open PRs awaiting you:** #167 (task 20 security scan) at last check. Review and merge in dependency order (`human-cheatsheet.md` §7). The first-pass review is CC6; the merge click, and any protected-file approval, stay with you | **Follows CC6** | ☐ |
| C2 | **Protected-file approvals:** any PR touching `Makefile`, `.github/`, `.claude/`, `AGENTS.md`, the spec, `agent-kit.conf` needs your explicit approval as its own `HUMAN_APPROVED=1` commit plus an approval record on the issue (`human-cheatsheet.md` §0, §5; `asking-the-human.md`). Specific known ones are B1, B3, F1 | See B1, B3, F1 | ☐ |
| C3 | **Merge checklist before every click:** `human-cheatsheet.md` §7 | none | ☐ |

## D. Recurring / ongoing

| # | Action | Cloud link | Status |
|---|---|---|---|
| D1 | **Permission sweeps:** read the proposal (CC4), approve or reject the settings changes, and apply them. `settings` files are protected. `_docs/agent-kit/procedures/permission-sweep.md`, `human-cheatsheet.md` §5 | **Needs CC4** | ☐ |
| D2 | **Deferred spec notes (#63):** four spec notes await your decision. CC5 drafts the exact diffs and a recommendation; the decision and the protected spec commit are yours | **Needs CC5** | ☐ |
| D3 | **Keep the nightly stop off during grading windows** and back on afterwards (A11). `aws-setup.md` §10 | none | ☐ |
| D4 | **Dev-container rebuilds** are a human step, not mid-issue (`human-cheatsheet.md` §5b) | none | ☐ |

## E. Later / scheduled (not blocking submission)

- ☐ Showcase AWS steps (S1-S3): after submission (`aws-setup.md` Showcase steps,
  `roadmap-showcase.md`).
- ☐ Teardown when you end the deployment: `aws-setup.md` §11,
  `terraform-verify.md` §5.
- ☐ **Peer reviews:** the three peer reviews of other projects are required to
  pass; the roadmap reserves time for them in S5. Only you can do them.
- ☐ **Submit:** when to submit is yours, not an agent's (`roadmap.md`, after the
  S5 close-out and the final re-audit, CC1 then a second pass).

## F. Decisions that gate agent work

F0 shapes a Terraform fix and so the first AWS apply. F1-F3 gate the responder.

| # | Decision | Detail | Cloud link | Status |
|---|---|---|---|---|
| F0 | **Accept or fix the shared deploy policy** (Terraform review finding F5). The dev and prod roles can both run any shell command as root on the one server through `AWS-RunShellScript`, so "the dev role can run only the dev deploy" cannot be met with IAM alone on a shared server. Either accept it in writing (mitigations: `main` branch protection, `dev` limited to `main`, `production` reviewers) or have CC29 add a custom SSM document that runs only the deploy script | `_docs/reviews/2026-10-25-terraform-pre-apply-review.md` F5 | **Shapes CC29** | ☑ Decided 2026-10-25: option 1, accept for submission. The custom SSM document is parked as showcase item X10 (`roadmap-showcase.md`); `terraform-verify.md` §2 records the accepted risk |

F1-F3 are open decisions only you can make. They gate **#160** (the responder,
task 28), then #161, #182 and the recorded drill (task 39), which carry
On-Call Agent 2 and the last of the Alerting and Observability points.

| # | Decision | Detail | Cloud link | Status |
|---|---|---|---|---|
| F1 | **D4: add the US-15 false-positive rule** (on an alert with no reproducible defect the responder explains and changes nothing). `specs.md` is protected: approve a diff, then commit it as `HUMAN_APPROVED=1` | `roadmap.md` Open decisions #8 | **Needs CC5(a)** (draft diff); **gates CC7, CC21** | ☐ |
| F2 | **Responder agent runtime** (architecture Open question 9; the recorded run of task 39 uses the real one). Adding it is a new dependency, so it needs your approval | `roadmap.md` Prerequisites | **Gates CC7, CC21** | ☐ |
| F3 | **`main` branch protection** that refuses the responder's push (architecture D2 of #43) | `roadmap.md` Prerequisites | **Gates CC7, CC21** | ☐ |

---

## Moved to the cloud list

So nothing is lost: every item that used to be on this list and is now a cloud
task.

| Old row | Now |
|---|---|
| A4 Terraform static check | CC9 (needs B2) |
| A5 Pre-apply review of the module diff | CC10; you read the findings at A6 |
| §B #140 security scan | CC12 (needs B4); you close at B5 |
| §B #155 observability stack | CC15 (needs B1) |
| §B #156 owner delivery, MailHog leg | CC14; the SES leg stays A10 |
| §B #157 telemetry job | CC14 |
| §B #158 Grafana rule | CC16 |
| §B #172, #174, #177 / #193 | CC14 |
| §C "review open PRs" first pass | CC6; the merge stays C1 |
| §D permission sweep: the report and proposal | CC4; approval stays D1 |
| §D #63 spec-note drafts | CC5; the decision stays D2 |

---

## Keeping this current

- When you finish an item, tick its box here. When a cloud task it depends on or
  unblocks changes, update the cross-reference in both files.
- When an agent adds a new human action (a new secret, a new `terraform apply`, a
  new approval), it adds a row here **and** the detail in the linked doc, and names
  the cloud task it affects. This file only indexes; the linked doc holds the
  commands.
- This is a roll-up, not a second source of truth: never copy commands here that
  would then drift from `aws-setup.md` / `terraform-verify.md` /
  `pending-verification.md`.
