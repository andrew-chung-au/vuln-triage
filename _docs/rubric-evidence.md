# Rubric evidence

Status of each of the 12 criteria (24 points, 10 to pass) in `_docs/rubric.md`,
with links to evidence that exists now. Only the Rubric Evidence Auditor
(`.opencode/agents/rubric-auditor.md` and `.claude/agents/rubric-auditor.md`,
via the `update-rubric-evidence` skill) updates this file. Planned work does
not count, and the log's claims alone are not accepted without opening the
linked evidence.

- Audit date: 2026-10-17
- Commit audited: `a535ff7` (local `main`). The public repo
  (https://github.com/andrew-chung-au/vuln-triage, visibility PUBLIC) is at
  `bd616a5`; the issue #11 commits after it are not yet pushed.
- Status values: MET (top point level), PARTIAL (a lower non-zero level),
  MISSING (0 points).
- Points currently evidenced: 7 of 24 (pass mark 10).

| criterion | max points | full-marks condition | status | evidence | gap |
|---|---|---|---|---|---|
| 1. Problem Description | 2 | "The README clearly describes the problem, the system functionality, and expected behavior." | PARTIAL (1) | `README.md` lines 1-4: one-line purpose ("Ranks vulnerable dependencies and routes each fix to its owner") and a planning-phase note; the full problem and workflow are in `_docs/project-brief.md`, linked from `README.md` line 8 | The README itself must describe the problem, what the system does (ingest lockfiles, match OSV, enrich with KEV/EPSS, rank, notify, dashboard, MCP) and the expected behaviour; a link to the brief is not the README describing it |
| 2. Product Specification | 2 | "A specification exists and there's a publicly accessible task tracker. The tasks define acceptance criteria and there's evidence that the agents used the tracker." | MET (2) | Spec: `_docs/specs.md` (US-1 to US-15 with acceptance lines, edge cases E1-E6). Public tracker: `gh repo view` reports PUBLIC with issues enabled. Acceptance criteria: https://github.com/andrew-chung-au/vuln-triage/issues/1 and https://github.com/andrew-chung-au/vuln-triage/issues/2 ("## Acceptance criteria" sections). Agent use: role-labelled comments on #1 (PM https://github.com/andrew-chung-au/vuln-triage/issues/1#issuecomment-6136675116, Engineer #issuecomment-6136679351, QA FAIL #issuecomment-6136682287, QA PASS #issuecomment-6217664490, Orchestrator close #issuecomment-6217787141) and on #2 (PM #issuecomment-6218651619, QA PASS #issuecomment-6218959705) | None for the level. Note: the spec changes to US-13 to US-15 are local-only until pushed; the tracker holds process/planning issues so far, not product-feature tasks |
| 3. Agent Team Specification | 2 | "The project defines the agent team and process of how they work together." | MET (2) | `_docs/agent-kit/process.md` lines 31-46 (Roles: PM, Engineer, QA; Orchestrator), lines 68-85 (Lifecycle: groom, implement, verify, QA, assert-clean, decision point, close); role files `_docs/agent-kit/team/pm.md`, `software-engineer.md`, `qa-engineer.md`; tool definitions `.opencode/agents/*.md`, `.claude/agents/*.md`; the process is followed on #1 and #2 (comments above) | None for the level. Improvement planned in #12 (`_docs/agent-team.md`: tool/model per role, QA independence rule, Reviewer and Auditor roles) does not exist yet; `.claude/agents/rubric-auditor.md` still says "14 criteria" and tells the auditor to append to the log (#10) |
| 4. Context Management | 2 | "AGENTS.md exists and it also points to modular docs (process, teams, etc.)." | MET (2) | `AGENTS.md` line 5 describes the project; lines 8-16 "Where to read more" point to `_docs/specs.md`, `_docs/rubric.md`, `_docs/agent-kit/process.md` (line 14), `_docs/agent-kit/team/` (line 15), `_docs/agent-kit/procedures/` (line 16); `CLAUDE.md` imports `AGENTS.md` | None for the level. The line 8-16 list update (commit `4075318`) is not yet pushed |
| 5. Application | 2 | "Full-stack application works end to end: frontend talks to backend, data persists in a database. Application runs locally with a single command." | MISSING (0) | No application code at `a535ff7` (`git ls-files`); `Makefile` line 2: "install/test/run targets will be added when the project is scaffolded"; `AGENTS.md` Commands: Run `none` | Frontend, backend and database, connected end to end, started by one `make` target |
| 6. Testing | 2 | "Both unit and integration tests exist, run with a single command, and pass." | MISSING (0) | `agent-kit.conf` line 15 `TEST_CMD=""`; no test files in `git ls-files` | Unit and integration tests, one command (e.g. `make test`), passing |
| 7. Containerization | 2 | "The full system, including the database, runs via Docker or Docker Compose and starts with a single command." | MISSING (0) | No Dockerfile or Compose file in `git ls-files`; `AGENTS.md` Project gotchas: no Docker in this container | Dockerfiles plus a Compose file including the database, started by one command; needs an environment with Docker |
| 8. Deployment | 2 | "The application is deployed and reachable at a public URL, or there's a clear demo with the deployment." | MISSING (0) | No deployment config, URL or demo in the repo | A working deployment at a public URL, or a clear demo of it |
| 9. CI/CD | 3 | "CI runs tests, CD deploys to dev, and there's a manual deploy to production." | MISSING (0) | `.github/workflows/verify.yml` runs `make verify` on push and pull_request; runs succeed (e.g. https://github.com/andrew-chung-au/vuln-triage/actions/runs/38921010198 at `bd616a5`), but `make verify` runs no tests (`TEST_CMD=""`) | CI that runs real tests on every PR (1 point), CD that deploys automatically (2), deploy to dev plus a manual production deploy (3) |
| 10. Observability | 2 | "A key user journey is instrumented with metrics, traces, and structured logs that share a trace ID; no customer data or credentials are sent to telemetry; and the signals are collected, stored, and viewable in a UI." | MISSING (0) | Requirement only: `_docs/specs.md` US-13 and E6; no code or telemetry config | Instrument the scan-to-notification journey with metrics, traces and structured logs sharing a trace ID, telemetry free of customer data, collected and viewable in Grafana |
| 11. Alerting on User Impact | 1 | "At least one alert exists." | MISSING (0) | Requirement only: `_docs/specs.md` US-14; no alert rule in the repo | At least one alert rule (US-14: undelivered top-priority finding) |
| 12. On-Call Agent | 2 | "An agent wakes up on an alert and fixes the issue." | MISSING (0) | Requirement only: `_docs/specs.md` US-15; no responder agent definition or run | A responder agent triggered by the alert that fixes the defect, with its actions logged |

## Top three gaps (priority order)

1. **Application (2) and Testing (2)**: no code exists. These unlock
   Containerization, Deployment, CI/CD, Observability, Alerting and On-Call,
   which all need a running app. Finish planning review, scaffold, and add
   `make run` and `make test` with unit and integration tests.
2. **Problem Description (1 point short)**: the cheapest point available. Expand
   `README.md` to describe the problem, the system functionality and expected
   behaviour directly, not only by link to the brief.
3. **Containerization (2) and CI/CD (3)**: Docker is unavailable in this
   container (`AGENTS.md` Project gotchas), so Compose, image builds and
   deploy pipelines need a codespace or Compose-capable environment; until
   then CI runs only whitespace checks. Also push the local issue #11 commits
   so the public repo shows the final spec, AGENTS.md and rubric.
