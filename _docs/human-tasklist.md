# Human tasklist

**For the human only.** One place that lists every action **you** must take —
the things an agent cannot do: AWS applies and secrets, protected-file approvals,
Docker/live-network verification runs, and the merges and sweeps that keep the
repo moving. It is an **index**: each item links to the document that holds the
exact commands and acceptance, so this file stays short and those docs stay the
source of truth. Where this disagrees with a linked doc, the linked doc wins —
fix this file.

How the pieces fit:

| Document | What it holds | Relationship to this file |
|---|---|---|
| `_docs/aws-setup.md` | The ordered AWS/GitHub runbook (account, region, budget, bootstrap, secrets, SES, nightly stop, teardown). | The detail for §A. |
| `_docs/terraform-verify.md` | How to statically check and apply/verify the `terraform/` modules (§1-§6). | The detail for the Terraform items in §A and §B. |
| `_docs/pending-verification.md` | **Per-issue** checklist of every step the agent sandbox can't run (Docker/network/AWS), ticked off as each passes. | The per-issue detail for §B. This file is the prioritised roll-up; that file is the working checklist. |
| `_docs/human-cheatsheet.md` | The git / review / merge workflow (branches, PRs, protected files, sweeps). | The detail for §C and §D. |

**Status key:** ☐ to do · ◐ in progress / partly done · ☑ done. Update the box
when you finish an item; when an issue's `pending-verification.md` items are all
ticked, close the issue and set it ☑ here.

Last updated: 2026-10-25.

---

## A. One-time AWS + GitHub setup (do once, in order)

The submission deployment. Full detail and timings in
`_docs/aws-setup.md` (the "Checklist" table) and `_docs/terraform-verify.md`.
**You** run every `terraform apply` and the first deploy; the agent holds no AWS
credentials.

| # | Action | Where | Doc | Status |
|---|---|---|---|---|
| A1 | Account hygiene, pick the region, set a budget alert | AWS console | `aws-setup.md` §1-§3 | ☐ |
| A2 | Decide the hostname form and how you reach the server (SSM, no SSH) | decision | `aws-setup.md` §4-§5 | ☐ |
| A3 | GitHub: create the `dev` and `production` environments | GitHub settings | `aws-setup.md` §6 | ☐ |
| A4 | Static-check the Terraform (`fmt -check`, `init -backend=false`, `validate`) in each module | your machine / push-check image | `terraform-verify.md` §1 | ☐ |
| A5 | Pre-apply review of the module diff against the security checklist | reading the diff | `terraform-verify.md` §2 | ☐ |
| A6 | Apply in order `bootstrap/` → `deploy-roles/` → `server/`; copy the two role ARNs into the GitHub variables `AWS_DEV_ROLE_ARN` / `AWS_PROD_ROLE_ARN` and `AWS_REGION`; record the Elastic IP + hostnames | your machine (AWS) | `aws-setup.md` §6-§7, `terraform-verify.md` §3 | ☐ |
| A7 | Add the submission secrets to Secrets Manager (db password, read token, responder token, Grafana admin password) | AWS console | `aws-setup.md` §8 | ☐ |
| A8 | **Re-apply `deploy-roles/`** after task 21 (#142): the dev role gained a read-only `ec2:DescribeInstances` so the deploy can read instance state. ARN unchanged; 2nd plan shows "No changes" | your machine (AWS) | `terraform-verify.md` §6 | ☐ |
| A9 | First dev deploy; confirm `https://dev.<eip>.sslip.io` answers and the deploy log names an image digest → closes **#141** | push to `main` + AWS | `terraform-verify.md` §4 | ☐ |
| A10 | Email route: verify the SES sender identity (and the demo recipient, SES sandbox); settle the SES `VERIFY:` items. Needed before task 37 delivers on AWS | AWS console | `aws-setup.md` §9, `pending-verification.md` #156 | ☐ |
| A11 | Nightly stop on by default; switch it **off** while graders may visit; activate the `project` cost-allocation tag | AWS console / Terraform var | `aws-setup.md` §10 | ☐ |
| A12 | Add the **prod** secret `vuln-triage/prod` (at least `POSTGRES_PASSWORD`), then **promote to production** (task 18 / #143): Actions → deploy → Run workflow, approve the `production` environment, confirm `https://app.<eip>.sslip.io` answers and `dev`/`prod` share the digest; rollback = re-run with the previous tag → closes **#143** | AWS console + GitHub Actions | `aws-setup.md` §8 + "Production promotion and rollback", `terraform-verify.md` §7 | ☐ |
| A13 | **Register the pilot seed data** (task 22 / #144): fill `deploy/pilot-seed.json` with your repos (VERIFY Juice Shop's `package-lock.json`, else use the NodeGoat fallback), then `python deploy/seed-pilot.py --base-url https://dev.<eip>.sslip.io --username <security-lead>`; confirm each asset shows a scan status and ≥1 finding on the dev dashboard → closes **#144** | your machine → dev URL | `aws-setup.md` "Pilot seed data" | ☐ |

> **Dependency order:** A1-A3 need no repo code. A4-A5 are safe anywhere (no
> AWS). A6 is the first apply. A8 can be folded into A6 if you apply after #142
> is merged; otherwise it is a quick re-apply of one module. A9 is the
> end-to-end gate for the dev environment. A12 (prod promotion) needs A3's
> `production` environment, A6's `AWS_PROD_ROLE_ARN`, and the `vuln-triage/prod`
> secret; it needs **no** Terraform re-apply (task 18 adds no Terraform). A13
> (pilot seed) needs A9's dev environment up and a `security lead` account
> (the operator create-user command, #176).

## B. Per-issue verification runs (code is merged; needs a real run to close)

These issues' **code is on `main`**, but they stay **open** until you run the
step the sandbox can't (Docker, live network, or AWS) and tick it off. The
authoritative per-issue checklist — exact commands and acceptance — is
`_docs/pending-verification.md`; run the smallest capable environment (CI →
Codespace/cloud → your machine for AWS).

| Issue | Task | What you must run | Environment | Status |
|---|---|---|---|---|
| **#140** | 20 security scan | Generate fixture lockfiles, `make security-scan-selftest`, `make security-scan`, commit lockfiles so the CI `security-scan` job goes green | Codespace / cloud / CI | ☐ |
| **#155** | 24 observability stack | Bring up `observability/` and confirm the US-13 Grafana dashboard shows metric+trace+logs side by side; MailHog answers | Docker host / cloud | ☐ |
| **#156** | 37 owner delivery | `make verify` lands the core cases; then the MailHog Compose run (`I-OWNER-NOAWS`/`I-OWNER-SENDER`); the SES/AWS leg is A10 | `make verify` + Docker host | ◐ (issue closed; AWS/SES leg = A10) |
| **#157** | 25 telemetry job | `make test-compose JOB=telemetry` (`T-REFUSE`) green in CI; confirm it fails when `owner.email` is added to the allowlist | CI / Docker host | ☐ |
| **#158** | 26 US-14 rule | `make verify` lands the metric half; confirm the provisioned Grafana rule fires once / resolves / NoData-human-only on a running stack | `make verify` + Docker host | ◐ (issue closed; Grafana-rule run pending) |
| **#172** | 40 feed wiring | `T-JOURNEY-BE` + `I-OWNER-NOAWS` green on the containerized harness in the telemetry CI job | CI / Docker host | ☐ |
| **#174** | 23 OTLP log export | No separate run: the backend log-export leg is confirmed by the **#172 `T-JOURNEY-BE`** Loki assertion (and #157 `T-REFUSE`). Static-verified on `main` (commit `61837cb`); tick when that Loki leg passes | CI / Docker host (via #172) | ◐ (merged; Loki-leg run = #172) |
| **#177** | 23 journey log calls | No separate run: the `scan.finished` / `notification.deliver` log calls are confirmed by the same **#172 `T-JOURNEY-BE`** Loki assertion. Static-verified on `main` (commit `970cdbf`); tick when that Loki leg passes | CI / Docker host (via #172) | ◐ (merged; Loki-leg run = #172) |

> **Note on "closed but pending":** #156 and #158 were closed because their
> `make verify`-able half landed; the Docker/AWS half is tracked in
> `pending-verification.md` and rolled into A10 (SES) / B-#158 (Grafana rule).
> #174 and #177 are the same shape — their code is on `main` but the only
> end-to-end proof is the #172 `T-JOURNEY-BE` Loki leg, which the agent sandbox
> (no Docker) cannot run; they were closed on **static** verification, so they
> are shown ◐ here and re-opened until that Loki leg is green.
> If you want a single close gate per issue instead, re-open the others too until
> the real-run halves pass — your call.

## C. Merges and protected-file approvals (as PRs arrive)

Every piece of agent work lands as a PR you review and merge. The full method —
branches, reading the whole diff, protected-file approval with `HUMAN_APPROVED=1`,
merge-commit only — is in `_docs/human-cheatsheet.md`.

- ☐ **Open PRs awaiting you now:** #184 (task 21 auto dev deploy — includes the
  A8 Terraform re-apply note), #183 (task 27 alert job, another agent), #167
  (task 20 security scan). Review and merge in dependency order
  (`human-cheatsheet.md` §7 checklist).
- ☐ **Protected-file approvals:** any PR touching `Makefile`, `.github/`,
  `.claude/`, `AGENTS.md`, the spec, `agent-kit.conf` needs your explicit
  approval as its own `HUMAN_APPROVED=1` commit + an approval record on the issue
  (`human-cheatsheet.md` §0, §5; `_docs/agent-kit/procedures/asking-the-human.md`).
- ☐ **Merge checklist before every click:** `human-cheatsheet.md` §7.

## D. Recurring / ongoing

- ☐ **Permission sweeps:** periodically run `make permission-report SINCE=<commit>`
  and approve/reject the proposed settings changes (first sweep: #65).
  `_docs/agent-kit/procedures/permission-sweep.md`, `human-cheatsheet.md` §5.
- ☐ **Keep the nightly stop off during grading windows** and back on afterwards
  (A11). `aws-setup.md` §10.
- ☐ **Deferred spec notes (#63):** four spec notes await your decision
  (`human-cheatsheet.md` §5).
- ☐ **Dev-container rebuilds** are a human step, not mid-issue
  (`human-cheatsheet.md` §5b).

## E. Later / scheduled (not blocking submission)

- ☐ Showcase AWS steps (S1-S3) — after submission (`aws-setup.md` Showcase
  steps, `roadmap-showcase.md`).
- ☐ Teardown when you end the deployment — `aws-setup.md` §11,
  `terraform-verify.md` §5.

---

## Keeping this current

- When you finish an item, tick its box here; when an issue's
  `pending-verification.md` section is fully ticked, close the issue and set it
  ☑ in §B.
- When an agent adds a new human action (a new secret, a new `terraform apply`, a
  new verification run), it should add a row here **and** the detail in the
  linked doc — this file only indexes; the linked doc holds the commands.
- This is a roll-up, not a second source of truth: never copy commands here that
  would then drift from `aws-setup.md` / `terraform-verify.md` /
  `pending-verification.md`.
