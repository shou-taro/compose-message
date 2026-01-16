from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "GitError",
    "is_git_repo",
    "get_repo_root",
    "get_status_porcelain",
    "has_staged_changes",
    "get_staged_diff",
    "get_current_branch",
    "commit_with_message",
]


class GitError(RuntimeError):
    """Raised when Git is unavailable or a Git command fails."""


@dataclass(frozen=True)
class GitCommandResult:
    """Result of running a Git command.

    This is intentionally small and stable so it can be used throughout the
    codebase without leaking `subprocess` details.

    Attributes:
        stdout: Standard output, stripped of leading/trailing whitespace.
        stderr: Standard error, stripped of leading/trailing whitespace.
        returncode: Exit status returned by Git.
    """

    stdout: str
    stderr: str
    returncode: int


def _run_git(
    args: Sequence[str],
    *,
    cwd: str | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> GitCommandResult:
    """Runs a Git command and returns its output.

    This helper exists so all Git subprocess calls are executed consistently:
    - Text mode is always enabled.
    - Output is captured for error reporting and prompts.
    - Errors are converted into `GitError` with concise messages suitable for a CLI.

    Args:
        args: Git arguments (without the leading `git`).
        cwd: Working directory to run Git in. If None, uses the current directory.
        check: If True, non-zero exit codes raise `GitError`.
        env: Optional environment overrides.

    Returns:
        A `GitCommandResult` containing stdout/stderr and the return code.

    Raises:
        GitError: If Git is not installed, or if the command fails and `check=True`.
    """
    cmd = ["git", *args]

    # For stable, parseable output we avoid pagers and interactive prompts.
    merged_env = dict(os.environ)
    merged_env.update(
        {
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    if env:
        merged_env.update(env)

    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise GitError(
            "git command not found. Please install Git and ensure it is on PATH."
        ) from e

    stdout = (completed.stdout or "").rstrip("\n")
    stderr = (completed.stderr or "").strip()

    if check and completed.returncode != 0:
        # Prefer stderr, but fall back to stdout for commands that report there.
        detail = stderr or stdout or f"git exited with code {completed.returncode}"
        raise GitError(f"git {' '.join(args)} failed: {detail}")

    return GitCommandResult(
        stdout=stdout,
        stderr=stderr,
        returncode=completed.returncode,
    )


def is_git_repo(*, cwd: str | None = None) -> bool:
    """Checks whether the given directory is inside a Git repository.

    Args:
        cwd: Directory to check. If None, uses the current directory.

    Returns:
        True if `cwd` is inside a Git working tree; otherwise False.
    """

    try:
        res = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=cwd, check=True)
        return res.stdout.lower() == "true"
    except GitError:
        return False


def get_repo_root(*, cwd: str | None = None) -> str:
    """Return the absolute path to the repository root.

    This uses `git rev-parse --show-toplevel` to resolve the top-level directory
    of the current working tree.

    Args:
        cwd: Working directory to run Git in. If None, uses the current directory.

    Returns:
        Absolute path to the repository root.

    Raises:
        GitError: If the command fails (e.g. not a repository).
    """

    return _run_git(["rev-parse", "--show-toplevel"], cwd=cwd, check=True).stdout


def get_status_porcelain(*, cwd: str | None = None) -> str:
    """Returns `git status --porcelain` output.

    Porcelain output is designed to be machine-readable and stable. It provides
    high-level context (new/modified/deleted files) without including full diffs.

    Args:
        cwd: Working directory. If None, uses the current directory.

    Returns:
        The porcelain status output (may be an empty string).

    Raises:
        GitError: If the command fails (e.g. not a repository).
    """

    return _run_git(["status", "--porcelain"], cwd=cwd, check=True).stdout


def has_staged_changes(*, cwd: str | None = None) -> bool:
    """Returns True if there are staged changes.

    This uses `git diff --staged --quiet`, which indicates changes via exit code:
    - 0: no staged differences
    - 1: staged differences exist

    Args:
        cwd: Working directory. If None, uses the current directory.

    Returns:
        True if there are staged changes; otherwise False.

    Raises:
        GitError: If Git returns an unexpected exit code.
    """

    res = _run_git(["diff", "--staged", "--quiet"], cwd=cwd, check=False)

    if res.returncode == 0:
        return False
    if res.returncode == 1:
        return True

    # Any other exit code indicates an actual error.
    detail = res.stderr or res.stdout or f"git exited with code {res.returncode}"
    raise GitError(f"git diff --staged --quiet failed: {detail}")


def get_staged_diff(
    *,
    cwd: str | None = None,
    include_stats: bool = False,
    max_bytes: int | None = None,
) -> str:
    """Returns the staged diff (`git diff --staged`) as a string.

    Args:
        cwd: Working directory. If None, uses the current directory.
        include_stats: If True, also include a compact `--stat` summary.
        max_bytes: If set, truncate the diff to at most this many bytes.
            This is useful before sending content to an LLM.

    Returns:
        The staged diff text (possibly truncated). If there are no staged changes,
        this may be an empty string.

    Raises:
        GitError: If the command fails (e.g. not a repository).
    """

    # Always fetch the patch diff first.
    patch = _run_git(["diff", "--staged"], cwd=cwd, check=True).stdout

    # Optionally include a compact summary. We fetch this separately to avoid
    # changing the patch output format.
    if include_stats:
        stats = _run_git(["diff", "--staged", "--stat"], cwd=cwd, check=True).stdout
        if stats:
            diff_text = "\n".join(
                [
                    "[staged diff --stat]",
                    stats,
                    "",
                    "[staged diff]",
                    patch,
                ]
            )
        else:
            diff_text = patch
    else:
        diff_text = patch

    if max_bytes is not None:
        raw = diff_text.encode("utf-8")
        if len(raw) > max_bytes:
            # Truncate safely and append a marker so downstream logic can react.
            truncated = raw[:max_bytes].decode("utf-8", errors="ignore")
            diff_text = truncated + "\n\n[diff truncated]\n"

    return diff_text


def get_current_branch(*, cwd: str | None = None) -> str | None:
    """Return the current branch name, if available.

    This uses `git branch --show-current`. When HEAD is detached, Git returns an
    empty string; in that case this function returns None.

    Args:
        cwd: Working directory. If None, uses the current directory.

    Returns:
        Branch name (e.g. "main", "feat/draft") or None if it cannot be
        determined.
    """

    try:
        name = _run_git(
            ["branch", "--show-current"], cwd=cwd, check=True
        ).stdout.strip()
    except GitError:
        return None

    return name or None


def commit_with_message(message: str, *, cwd: str | None = None) -> None:
    """Create a Git commit using the given commit message.

    This writes the message to a temporary file and runs `git commit -F <file>`.
    Using `-F` avoids invoking an interactive editor and is suitable for CLI
    automation.

    Args:
        message: Commit message text.
        cwd: Working directory. If None, uses the current directory.

    Raises:
        GitError: If Git fails to create the commit.
        ValueError: If `message` is empty or whitespace only.
    """

    if not message.strip():
        raise ValueError("message must be non-empty.")

    tmp_path: str | None = None

    # NamedTemporaryFile on Windows cannot always be re-opened by another process
    # when delete=True, so we create it with delete=False and clean up ourselves.
    tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
    try:
        tmp.write(message)
        if not message.endswith("\n"):
            tmp.write("\n")
        tmp.flush()
        tmp_path = tmp.name
        tmp.close()

        _run_git(["commit", "-F", tmp_path], cwd=cwd, check=True)
    finally:
        try:
            if tmp_path:
                os.unlink(tmp_path)
        except OSError:
            # Best effort cleanup. The commit has already been created.
            pass
