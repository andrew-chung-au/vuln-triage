"""#260 QA findings 1a to 1d: the runner's gate and push against REAL git on local temp repositories.

The checkout is a throwaway repository, the "remote" a local bare repository (the real
``SubprocessPublishGit`` is pointed at it instead of github.com). Nothing here touches the network, a token or
the owner's git configuration: the tests' own git calls run with an empty global config and a temporary HOME.
The pull request client is the in-memory fake.
"""

from __future__ import annotations

import os
import shutil
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


# -- 1a: swapping a directory for a symlink after the last commit ----------------------------------

@pytest.mark.parametrize("committed,directory,reason", [
    (".github/workflows/evil.yml", ".github", "diff_path_github_dir"),
    ("responder/vt_responder/policy.py", "responder/vt_responder", "diff_path_guard_module"),
])
def test_a_directory_swapped_for_a_symlink_after_the_commit_does_not_change_the_verdict(rig, committed, directory,
                                                                                         reason):
    """The gate judges the path the commit contains, never where the working tree would resolve it today."""
    rig.commit({committed: "evil\n"})
    shutil.rmtree(rig.work / directory)
    (rig.work / directory).symlink_to(rig.work / "backend")
    rig.refused(reason)


# -- QA round 3, F2: an untracked .gitmodules must not hide a committed gitlink ----------------------

@pytest.mark.parametrize("hide", [False, True])
def test_a_committed_gitlink_is_refused_even_with_an_untracked_gitmodules_that_ignores_it(rig, hide):
    """``git diff`` reads ``.gitmodules`` from the WORKING TREE: ``ignore = all`` there makes a plain diff skip the
    gitlink (mode 160000). The agent's code can write that file without committing it; the gate must still see it."""
    git(rig.work, "update-index", "--add", "--cacheinfo", f"160000,{rig.base},backend/sub")
    write(rig.work, "backend/app/service.py", "fixed\n")
    git(rig.work, "add", "--", "backend/app/service.py")
    git(rig.work, "commit", "-m", "agent")
    if hide:
        write(rig.work, ".gitmodules", '[submodule "backend/sub"]\n\tpath = backend/sub\n\turl = ./x\n\tignore = all\n')
    rig.refused("diff_submodule")


# -- 1b: intermediate commits ----------------------------------------------------------------------

def test_files_added_then_removed_in_intermediate_commits_never_reach_the_remote(rig):
    """The net diff is clean, so the gate passes it; what is pushed must be ONE commit the runner builds from
    the checked tree, so the history of the agent's commits (a workflow, a leak, an executable) stays local."""
    write(rig.work, "backend/run.sh", "#!/bin/sh\n")
    (rig.work / "backend/run.sh").chmod(0o755)
    rig.commit({".github/workflows/evil.yml": "on: push\n", "leak.txt": "SECRET-IN-HISTORY\n",
                "backend/run.sh": "#!/bin/sh\n"}, "one")
    rig.commit({".github/workflows/evil.yml": None, "leak.txt": None, "backend/run.sh": None}, "two")
    rig.commit({"backend/app/service.py": "fixed\n"}, "three")
    rig.publish()
    assert git(rig.remote, "rev-list", "--count", f"{rig.base}..refs/heads/{BRANCH}") == "1"
    pushed = git(rig.remote, "rev-list", "--objects", f"{rig.base}..refs/heads/{BRANCH}")
    assert "evil.yml" not in pushed and "leak.txt" not in pushed and "run.sh" not in pushed
    assert git(rig.remote, "show", f"refs/heads/{BRANCH}:backend/app/service.py") == "fixed"
    assert git(rig.remote, "rev-parse", f"refs/heads/{BRANCH}^") == rig.base
    assert git(rig.remote, "log", "-1", "--format=%an|%s", f"refs/heads/{BRANCH}").startswith("VulnTriage responder|")


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


# -- 1d (round 2): git directory indirection and a config edit between the check and the push -------

def _evil_remote(tmp_path: Path) -> Path:
    evil = tmp_path / "evil.git"
    evil.mkdir()
    git(evil, "init", "--bare", "-b", "main")
    return evil


def _plant_commondir(rig: Rig, evil: Path, *, relative: bool = False) -> None:
    """A copy of ``.git`` outside the checkout with a ``url.insteadOf``; ``.git/commondir`` points at it.
    ``.git/config`` itself is untouched, so its digest still matches."""
    copy = rig.work.parent / "git-copy"
    shutil.copytree(rig.work / ".git", copy)
    with (copy / "config").open("a") as handle:
        handle.write(f'[url "{evil}"]\n\tinsteadOf = {rig.remote}\n')
    target = os.path.relpath(copy, rig.work / ".git") if relative else str(copy)
    (rig.work / ".git" / "commondir").write_text(target + "\n")


@pytest.mark.parametrize("relative", [False, True])
def test_a_commondir_file_in_dot_git_is_refused_and_nothing_is_pushed(rig, tmp_path, relative):
    evil = _evil_remote(tmp_path)
    rig.commit({"backend/app/service.py": "fixed\n"})
    _plant_commondir(rig, evil, relative=relative)
    with pytest.raises(PublishError) as err:
        rig.publish()
    assert err.value.reason == "git_dir_unexpected"
    assert git(evil, "for-each-ref") == ""
    assert rig.remote_branch() is None


def test_the_runner_pushes_with_an_explicit_git_dir_so_a_commondir_file_is_ignored(rig, tmp_path):
    """Defence in depth: even if the refusal were skipped, GIT_DIR and GIT_COMMON_DIR name the checkout's own
    ``.git``, so git does not follow ``commondir`` to the planted copy."""
    evil = _evil_remote(tmp_path)
    head = rig.commit({"backend/app/service.py": "fixed\n"})
    _plant_commondir(rig, evil)
    sha = rig.seam.squash(rig.work, rig.base, head, "title")
    rig.seam.push(rig.work, sha, BRANCH)
    assert rig.remote_branch() == sha
    assert git(evil, "for-each-ref") == ""


@pytest.mark.parametrize("entry", ["gitdir", "config.worktree", "info/grafts", "objects/info/alternates"])
def test_other_unexpected_entries_in_dot_git_are_refused(rig, entry):
    rig.commit({"backend/app/service.py": "fixed\n"})
    write(rig.work / ".git", entry, "/somewhere\n")
    rig.refused("git_dir_unexpected")


def test_dot_git_replaced_by_a_symlink_is_refused(rig, tmp_path):
    rig.commit({"backend/app/service.py": "fixed\n"})
    moved = tmp_path / "moved-git"
    shutil.move(str(rig.work / ".git"), moved)
    (rig.work / ".git").symlink_to(moved)
    rig.refused("git_dir_unexpected")


def test_a_config_edit_between_the_check_and_the_push_is_refused(rig, tmp_path):
    """A straggler process can edit ``.git/config`` after the first check. The digest is read again right before
    the push, after the commit is built."""
    evil = _evil_remote(tmp_path)
    rig.commit({"backend/app/service.py": "fixed\n"})
    work = rig.work

    class Racing(SubprocessPublishGit):
        def squash(self, *args, **kwargs):
            sha = super().squash(*args, **kwargs)
            with (work / ".git" / "config").open("a") as handle:
                handle.write(f'[url "{evil}"]\n\tinsteadOf = {rig.remote}\n')
            return sha

    racing = Racing("o/r", "TOK")
    racing._url = str(rig.remote)
    publisher = GitPublisher(racing, rig.pulls)
    with pytest.raises(PublishError) as err:
        publisher.publish(rig.work, rig.snapshot, "fp1", "42", "fixed")
    assert err.value.reason == "git_config_modified"
    assert git(evil, "for-each-ref") == ""
    assert rig.remote_branch() is None


# -- 1d (round 2): the runner's CLONE ignores the global git config --------------------------------

def test_the_clone_ignores_the_global_git_config_the_agent_could_have_written(tmp_path, monkeypatch):
    """The clone has the token in its environment and runs with the owner's HOME, where a previous run's agent could
    have written ``~/.gitconfig``. A ``url.insteadOf`` there must not redirect it."""
    from vt_responder.checkout import SubprocessGit

    def make_repo(name: str, content: str) -> Path:
        repo = tmp_path / name
        repo.mkdir()
        git(repo, "init", "-b", "main")
        write(repo, "WHO", content)
        git(repo, "add", "--", "WHO")
        git(repo, "commit", "-m", "c")
        return repo

    real = make_repo("real", "REAL\n")
    evil = make_repo("evil", "EVIL\n")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(f'[url "{evil}"]\n\tinsteadOf = {real}\n')
    monkeypatch.setenv("HOME", str(home))
    seam = SubprocessGit("o/r", "TOK")
    seam._url = str(real)
    dest = tmp_path / "dest"
    seam.clone(dest)
    assert (dest / "WHO").read_text() == "REAL\n"
