# Prompts

Key prompts that define a role, stage, or task are saved verbatim in this
folder and indexed below.

| file | purpose (what it got the agent to plan or build) | where executed |
|---|---|---|
| [reviewer-plan-review.md](reviewer-plan-review.md) | Defines the independent Reviewer role: review the planning documents that exist against the brief and rubric, write `_docs/reviews/<date>-plan-review.md` with a PASS/FAIL verdict | Claude Code (claude-opus-5-5), 2026-10-16; produced `_docs/reviews/2026-10-16-plan-review.md` (commit ba39c5c) |
