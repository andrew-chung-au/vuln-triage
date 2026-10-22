#!/usr/bin/env python3
"""Count the approvals recorded in session summaries, by command pattern (issue #61).

Usage: python3 permission-report.py <SINCE>   (run as: make permission-report SINCE=<commit>)

Read-only by construction:
- reads only files under _session-summaries/ (paths come from `git log` and are
  filtered to that folder), and reads them with `git show HEAD:<path>`;
- runs only `git log`, `git show` and `git rev-parse`;
- opens no file for writing, makes no network call, prints to stdout only.

SINCE is exclusive (the range is SINCE..HEAD): pass the last-sweep commit.
SINCE must be 7 to 40 lowercase hex characters and a commit; anything else is
refused before any other command runs.
"""
import re
import subprocess
import sys

SUMMARY_DIR = "_session-summaries/"
FLOOR_COMMIT = "1b37fd1"  # 2026-10-21 rule change; older summaries used "none" differently
SINCE_RE = re.compile(r"[0-9a-f]{7,40}")
USAGE = "Usage: make permission-report SINCE=<commit>  (7 to 40 lowercase hex characters, a commit)"

GROUPS = [
    ("read-only", "Read-only", "propose allowing"),
    ("writes", "Writes to the record", "keep asking"),
    ("risky", "Risky", "propose denying"),
]
ALLOWED_GIT = {"log", "show", "rev-parse"}
SCRATCH_KEY = "python3|bash .scratch/*"
CHECK = "(read by hand) "


def git(*args):
    """Run one git command from the allowed list; return (exit code, stdout)."""
    if args[0] not in ALLOWED_GIT:
        raise SystemExit("permission-report: internal error, git %s is not allowed" % args[0])
    p = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return p.returncode, p.stdout


# ---- parsing (pure functions; the regression script imports these) ----------

def section(text):
    """Return the lines of '## Permission review', or None when it is absent."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "## Permission review":
            out = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("## "):
                    break
                out.append(nxt)
            return out
    return None


def group_of(head):
    h = head.lower()
    if h.startswith("read-only"):
        return "read-only"
    if h.startswith("writes to the record"):
        return "writes"
    if h.startswith("risky"):
        return "risky"
    return None


def bullets(lines):
    """Yield (group, text) pairs: one per item bullet of each group.

    A group bullet is a top-level '- Read-only ...', '- Writes ...' or
    '- Risky ...' line. Its own text after the first ':' and any nested bullets
    under it are items. Text starting with 'none' is no item. Other top-level
    bullets (Proposed ..., Sources ...) and prose are not approvals.
    """
    group = None
    result = []
    for line in lines:
        if not line.strip():
            continue
        m = re.match(r"^- (.*)$", line)
        if m:
            group = group_of(m.group(1))
            if group is None:
                continue
            _, _, rest = m.group(1).partition(":")
            rest = rest.strip()
            if rest and not rest.lower().startswith("none"):
                result.append((group, rest))
            elif rest and "`" in rest:
                # "none" followed by a backticked command: could be a refused or
                # blocked action, so show it for a human to read.
                result.append((group, CHECK + rest))
            continue
        m = re.match(r"^\s+[-*] (.*)$", line)
        if m and group is not None:
            result.append((group, m.group(1).strip()))
            continue
        if line.startswith(" ") and group is not None and result and result[-1][0] == group:
            # continuation line of the previous bullet
            result[-1] = (group, result[-1][1] + " " + line.strip())
    return result


def keys_of(text):
    """Normalised pattern keys for one bullet (a set; may be empty)."""
    if text.startswith(CHECK):
        return set()
    low = text.lower()
    keys = set()
    if low.startswith("editing "):
        return {"Edit protected path"}
    spans = re.findall(r"`([^`]+)`", text)
    bare = set()
    for raw in spans:
        s = raw.strip()
        if s.startswith("HUMAN_APPROVED=1 git commit"):
            keys.add("HUMAN_APPROVED=1 git commit")
        elif s.startswith("git commit") and "HUMAN_APPROVED=1" in text:
            keys.add("HUMAN_APPROVED=1 git commit")
        elif s.startswith("git push"):
            if "HEAD:" in s:
                keys.add("git push origin HEAD:*")
            elif "claude/" in s:
                keys.add("git push -u origin claude/*")
            else:
                keys.add("git push")
        elif s.startswith("gh issue"):
            sub = s.split()[2].rstrip("*") if len(s.split()) > 2 else ""
            if sub in ("comment",):
                keys.add("gh issue comment | make issue-comment")
            elif sub:
                keys.add("gh issue " + sub)
        elif s.startswith("make issue-comment"):
            keys.add("gh issue comment | make issue-comment")
        elif s.startswith("make "):
            parts = s.split()
            if len(parts) > 1 and parts[1] != "*":
                keys.add("make " + parts[1])
        elif s.startswith("gh api"):
            keys.add("gh api")
        elif s.startswith("sed -n"):
            keys.add("sed -n")
        elif s == "issue_write" or s.startswith("issue_write"):
            keys.add("GitHub MCP issue_write")
        elif ".scratch/" in s or re.match(r"^(python3|bash) .*\.(py|sh)$", s):
            keys.add(SCRATCH_KEY)
        elif s in ("python3", "bash", "node"):
            bare.add(s)
        elif s.startswith("ls "):
            keys.add("ls")
    if "github mcp" in low and "GitHub MCP issue_write" not in keys and "issue_write" in low:
        keys.add("GitHub MCP issue_write")
    if bare & {"python3", "bash", "node"} and "scratch" in low:
        keys.add(SCRATCH_KEY)
    elif bare and not keys:
        keys.update(bare)
    return keys


def label_for(group, key, count):
    if key == SCRATCH_KEY:
        return "make target, never allow"
    if group == "read-only":
        return "allow candidate (3+ sessions)" if count >= 3 else "below the 3-session threshold"
    if group == "writes":
        return "keep asking"
    return "deny proposal"


def analyse(named_texts, floor_excluded=()):
    """named_texts: {name: text}. Return a dict describing the counts."""
    counts = {g[0]: {} for g in GROUPS}
    uncategorised = []
    no_section, none_only, excluded = [], [], []
    for name in sorted(named_texts):
        if name in floor_excluded:
            excluded.append(name)
            continue
        sec = section(named_texts[name])
        if sec is None:
            no_section.append(name)
            continue
        items = bullets(sec)
        if not items:
            none_only.append(name)
            continue
        for group, text in items:
            keys = keys_of(text)
            if not keys:
                uncategorised.append((name, group, text))
                continue
            for k in keys:
                counts[group].setdefault(k, set()).add(name)
    return {
        "counts": counts,
        "uncategorised": uncategorised,
        "no_section": no_section,
        "none_only": none_only,
        "excluded": excluded,
    }


def render(result, since, total):
    out = ["Permission report: %d summaries changed in %s..HEAD" % (total, since), ""]
    for gid, title, disp in GROUPS:
        out.append("%s (%s)" % (title, disp))
        rows = sorted(result["counts"][gid].items(), key=lambda kv: (-len(kv[1]), kv[0]))
        if not rows:
            out.append("  (none)")
        for key, names in rows:
            out.append("  %d  %s  [%s]" % (len(names), key, label_for(gid, key, len(names))))
            out.append("      " + ", ".join(sorted(names)))
        out.append("")
    out.append("Uncategorised or to read by hand (raw text)")
    if not result["uncategorised"]:
        out.append("  (none)")
    for name, group, text in result["uncategorised"]:
        out.append("  %s [%s]: %s" % (name, group, text))
    out.append("")
    for title, names in (
        ("No ## Permission review section", result["no_section"]),
        ("Section says none only (nothing needed approval)", result["none_only"]),
        ("Excluded, older meaning of none (added before %s)" % FLOOR_COMMIT, result["excluded"]),
    ):
        out.append("%s: %d" % (title, len(names)))
        for n in names:
            out.append("  " + n)
    return "\n".join(out)


# ---- git side ----------------------------------------------------------------

def summaries_in_range(since):
    code, text = git("log", "--no-renames", "--name-only", "--diff-filter=AM", "--format=", since + "..HEAD", "--", SUMMARY_DIR)
    names = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(SUMMARY_DIR) and line.endswith(".md") and ".." not in line:
            names.add(line)
    return sorted(names)


def floor_excluded(names):
    """Summaries whose adding commit is an ancestor of FLOOR_COMMIT (or is it)."""
    code, floor_hash = git("rev-parse", "--verify", "--quiet", FLOOR_COMMIT + "^{commit}")
    if code != 0:
        print("note: floor commit %s not found in this repository; nothing is excluded" % FLOOR_COMMIT)
        return set()
    floor_hash = floor_hash.strip()
    _, anc = git("log", "--format=%H", FLOOR_COMMIT)
    ancestors = set(anc.split()) - {floor_hash}
    wanted = set(names)
    _, added = git("log", "--no-renames", "--diff-filter=A", "--name-only", "--format=@%H", "HEAD", "--", SUMMARY_DIR)
    cur, result = None, set()
    for line in added.splitlines():
        line = line.strip()
        if line.startswith("@"):
            cur = line[1:]
        elif line in wanted and cur in ancestors:
            result.add(line)
    return result


def main(argv):
    if len(argv) != 2 or not SINCE_RE.fullmatch(argv[1]):
        print("permission-report: bad SINCE: %r" % (argv[1] if len(argv) > 1 else ""), file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    since = argv[1]
    code, _ = git("rev-parse", "--verify", "--quiet", since + "^{commit}")
    if code != 0:
        print("permission-report: SINCE is not a commit in this repository: %s" % since, file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    names = summaries_in_range(since)
    if not names:
        print("no summaries changed since %s" % since)
        return 0
    excluded = floor_excluded(names)
    texts = {}
    for path in names:
        code, text = git("show", "HEAD:" + path)
        if code == 0:
            texts[path[len(SUMMARY_DIR):]] = text
    excluded_short = {p[len(SUMMARY_DIR):] for p in excluded}
    print(render(analyse(texts, excluded_short), since, len(texts)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
