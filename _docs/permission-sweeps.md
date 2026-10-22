# Permission sweeps

One line per sweep: date, the commit the sweep counted up to, outcome. The next sweep starts from the last commit listed here (`make permission-report SINCE=<commit>`). Procedure: `_docs/agent-kit/procedures/permission-sweep.md`.

No sweep yet; first sweep: see issue #65 (start from `SINCE=1b37fd1`).

Cloud sessions run file edits without asking in every mode, so the `Edit` ask rules only protect local sessions (see the live check on #60, comment 6330923566). The agent cannot see permission prompts: a live check needs the human to record what appeared on screen.
