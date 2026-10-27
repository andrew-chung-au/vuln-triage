"""#260 QA findings 1a to 1d: the runner's gate and push against REAL git on local temp repositories.

The checkout is a throwaway repository, the "remote" a local bare repository (the real
``SubprocessPublishGit`` is pointed at it instead of github.com). Nothing here touches the network, a token or
the owner's git configuration: the tests' own git calls run with an empty global config and a temporary HOME.
The pull request client is the in-memory fake.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from vt_responder.fakes import FakeBranchClient
from vt_responder.publisher import GitPublisher, PublishError, SubprocessPublishGit

pytestmark = pytest.mark.unit

IDENTITY = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
BRANCH = "responder/fp1"


def git(cwd: Path, *args: str, check: bool = True) -> str:
    """The TEST's own git call: no global or system config, so the owner's settings never matter."""
    env = {"PATH": os.environ["PATH"], "HOME": str(cwd), "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", **IDENTITY}
    done = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=check)
    return done.stdout.strip()


def write(root: Path, rel: str, text: str = "x\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class Rig:
    """A checkout cloned from a local bare remote, the real git seam, and a publisher over them."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, max_commits: int = 5) -> None:
        self.home = tmp_path / "home"
        self.home.mkdir()
        monkeypatch.setenv("HOME", str(self.home))  # what the runner's git would read a global config from
        self.remote = tmp_path / "remote.git"
        self.work = tmp_path / "work"
        self.remote.mkdir()
        self.work.mkdir()
        git(self.remote, "init", "--bare", "-b", "main")
        git(self.work, "init", "-b", "main")
        for rel in ("backend/app/service.py", "tests/test_service.py", ".github/workflows/verify.yml",
                    "responder/vt_responder/policy.py", "README.md"):
            write(self.work, rel)
        git(self.work, "add", "--", ".")
        git(self.work, "commit", "-m", "base")
        git(self.work, "push", str(self.remote), "main")
        self.base = git(self.work, "rev-parse", "HEAD")
        self.seam = SubprocessPublishGit("o/r", "TOK")
        self.seam._url = str(self.remote)  # the one test-only seam: a local path instead of github.com
        self.pulls = FakeBranchClient()
        self.publisher = GitPublisher(self.seam, self.pulls, max_commits=max_commits)
        self.snapshot = self.publisher.snapshot(self.work)

    def commit(self, files: dict[str, str | None], message: str = "agent") -> str:
        for rel, text in files.items():
            if text is None:
                git(self.work, "rm", "-q", "--", rel)
            else:
                write(self.work, rel, text)
                git(self.work, "add", "--", rel)
        git(self.work, "commit", "-m", message)
        return git(self.work, "rev-parse", "HEAD")

    def publish(self) -> str:
        return self.publisher.publish(self.work, self.snapshot, "fp1", "42", "fixed the retry")

    def refused(self, reason: str) -> None:
        with pytest.raises(PublishError) as err:
            self.publish()
        assert err.value.reason == reason
        assert self.remote_branch() is None  # nothing left the machine

    def remote_branch(self) -> str | None:
        out = git(self.remote, "rev-parse", "--verify", "-q", f"refs/heads/{BRANCH}", check=False)
        return out or None


@pytest.fixture
def rig(tmp_path, monkeypatch) -> Rig:
    return Rig(tmp_path, monkeypatch)


def test_a_clean_fix_is_pushed_to_the_responder_branch_of_the_local_remote(rig):
    rig.commit({"backend/app/service.py": "fixed\n"})
    assert rig.publish().endswith("/pull/100")
    assert rig.remote_branch() is not None


# -- 1c: git replace ------------------------------------------------------------------------------

def test_a_replace_ref_cannot_make_the_gate_see_a_benign_tree(rig):
    """``git replace evil benign`` makes ``git diff base evil`` show the benign tree. The runner reads objects
    as they are, so the real (protected) change is seen and refused."""
    evil = rig.commit({".github/workflows/evil.yml": "on: push\n"})
    git(rig.work, "checkout", "-q", "-b", "benign", rig.base)
    benign = rig.commit({"backend/app/service.py": "fine\n"})
    git(rig.work, "checkout", "-q", "main")
    git(rig.work, "replace", evil, benign)
    assert git(rig.work, "rev-parse", "HEAD") == evil
    rig.refused("diff_path_github_dir")


# -- 1d: the owner's global git configuration -----------------------------------------------------

def test_the_push_ignores_the_global_git_config_the_agent_could_have_written(rig, tmp_path):
    """The agent runs with the owner's real HOME, so it can write ~/.gitconfig. A ``url.insteadOf`` there would
    send the runner's push (with the token) to another host; ``http.sslVerify=false`` would weaken TLS."""
    evil = tmp_path / "evil.git"
    evil.mkdir()
    git(evil, "init", "--bare", "-b", "main")
    (rig.home / ".gitconfig").write_text(f'[url "{evil}"]\n\tinsteadOf = {rig.remote}\n')
    xdg = rig.home / ".config" / "git"
    xdg.mkdir(parents=True)
    (xdg / "config").write_text(f'[url "{evil}"]\n\tinsteadOf = {rig.remote}\n')
    rig.commit({"backend/app/service.py": "fixed\n"})
    rig.publish()
    assert rig.remote_branch() is not None  # went where the runner said
    assert git(evil, "for-each-ref") == ""  # and nowhere else
