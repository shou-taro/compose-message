from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import questionary

from compose_message.core.config import Config, load_effective_config
from compose_message.core.git import (
    GitError,
    get_repo_root,
    get_staged_diff,
    get_status_porcelain,
    has_staged_changes,
    is_git_repo,
)
from compose_message.core.prompt import build_commit_message_prompt
from compose_message.providers import ollama

__all__ = ["draft_command"]


# Prompt marker used by questionary (kept consistent across commands).
QMARK = "❯"


def _print_preview(message: str) -> None:
    """Print a terminal-friendly preview of the generated commit message.

    Args:
        message: Commit message to display.
    """

    print()
    print("=" * 72)
    print("📝 Preview")
    print("-" * 72)
    print(message.rstrip())
    print("=" * 72)
    print()


def _clean_model_output(text: str) -> str:
    """Strip common meta output from model responses.

    Some models include non-message text such as "Thinking..." blocks before
    the final answer. This command expects a plain commit message, so the
    preview/editor flow uses a cleaned version of the provider output.

    Args:
        text: Raw text returned by the provider.

    Returns:
        Cleaned commit message text.
    """

    raw = text.strip()
    if not raw:
        return raw

    lines = raw.splitlines()

    # Remove a leading "Thinking..." block if present.
    if lines and lines[0].strip().lower().startswith("thinking"):
        i = 0
        while i < len(lines):
            s = lines[i].strip().lower()
            if "done thinking" in s:
                i += 1
                break
            i += 1
        lines = lines[i:]

    cleaned: list[str] = []
    for line in lines:
        s = line.strip().lower()
        if s in {"thinking...", "...done thinking.", "done thinking."}:
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def _get_current_branch(*, cwd: str | None) -> str | None:
    """Return the current Git branch name, if available.

    Args:
        cwd: Working directory to run Git commands in.

    Returns:
        Branch name (e.g. "main", "feature/x") or None if it cannot be determined
        (e.g. detached HEAD or Git error).
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return None

    branch = result.stdout.strip()
    return branch or None


def draft_command(*, cwd: str | None = None) -> int:
    """Run the `git compose draft` command.

    This command:
    1) reads staged changes,
    2) asks the configured provider to draft a commit message,
    3) shows a preview,
    4) lets the user edit/regenerate/commit/exit.

    Args:
        cwd: Working directory to run Git commands in.
            If None, uses the current directory.

    Returns:
        Process exit code (0 on success; non-zero on cancellation or error).
    """
    try:
        return _draft_command(cwd=cwd)
    except GitError as e:
        print(f"Git error: {e}")
        return 2
    except KeyboardInterrupt:
        print("Cancelled.")
        return 130


def _draft_command(*, cwd: str | None) -> int:
    """Implementation for the draft command.

    Args:
        cwd: Working directory to run Git commands in.

    Returns:
        Process exit code.
    """
    if not is_git_repo(cwd=cwd):
        print("Not a Git repository. Run this command inside a repository.")
        return 1

    repo_root = get_repo_root(cwd=cwd)
    branch = _get_current_branch(cwd=cwd)

    if not has_staged_changes(cwd=cwd):
        print("No staged changes found. Stage files first (e.g. `git add -p`).")
        return 1

    config, config_path = load_effective_config(repo_root)

    profile_label = (
        "Conventional" if config.prompt_profile == "conventional" else "Default"
    )
    scope_label = "auto" if config.scope_strategy == "auto" else "omit"

    print()
    print("=" * 72)
    print("🎼 git-compose · Draft")
    print()
    print("Turn staged diffs into a commit message draft.")
    print()
    print(f"📁 Repository: {repo_root}")
    if branch:
        print(f"🌿 Branch: {branch}")
    print(f"⚙️  Config: {config_path}")
    print("🔧 Settings:")
    print(f"   • Model: {config.model}")
    print(f"   • Profile: {profile_label}")
    print(f"   • Scope: {scope_label}")
    print()
    print("Flow:")
    print("  1. 🧠 Generate")
    print("  2. 📝 Preview")
    print("  3. ✍️  Edit / 🔄 Regenerate")
    print("  4. ✅ Commit (optional)")
    print("=" * 72)
    print()

    # Gather repository context used in the prompt.
    status = get_status_porcelain(cwd=cwd)
    staged_diff = get_staged_diff(
        cwd=cwd,
        include_stats=True,
        max_bytes=config.max_diff_bytes,
    )

    # Scope is only relevant when using the Conventional profile.

    # Build a provider-agnostic prompt (system + user parts).
    parts = build_commit_message_prompt(
        staged_diff,
        status_porcelain=status,
        language=config.language,
        prompt_profile=config.prompt_profile,
        scope_strategy=config.scope_strategy,
    )

    print("🧠 Generating a draft message...")
    message = _generate_with_provider(config, parts.system, parts.user)
    message = _clean_model_output(message)
    if not message.strip():
        print("The provider returned an empty response.")
        return 1

    # Interactive loop: preview -> choose an action -> apply it
    # -> repeat until commit/exit.
    while True:
        _print_preview(message)

        default_action = config.default_action
        action = questionary.select(
            "Next step:",
            qmark=QMARK,
            choices=[
                questionary.Choice("✍️  Edit", value="edit"),
                questionary.Choice("🔄 Regenerate", value="regen"),
                questionary.Choice("✅ Commit now", value="commit"),
                questionary.Choice("🚪 Exit (no commit)", value="exit"),
            ],
            default=default_action,
        ).ask()

        if action is None:
            print("Cancelled.")
            return 1

        if action == "regen":
            print("🧠 Regenerating...")
            message = _generate_with_provider(config, parts.system, parts.user)
            message = _clean_model_output(message)
            if not message.strip():
                print("The provider returned an empty response.")
                return 1
            continue

        if action == "edit":
            edited = _edit_message(
                message=message,
                editor=config.editor,
                repo_root=repo_root,
            )
            if not edited.strip():
                print("Commit message is empty after editing. Cancelled.")
                return 1
            message = _clean_model_output(edited)
            continue

        if action == "commit":
            break

        if action == "exit":
            print("\nDraft generated. You can commit later with:")
            print("  git commit")
            return 0

    _git_commit_message(message, cwd=cwd)
    print("✅ Commit created.")
    return 0


def _generate_with_provider(config: Config, system: str, user: str) -> str:
    """Generate a commit message draft via the configured provider.

    Args:
        config: Effective configuration.
        system: System prompt text.
        user: User prompt text.

    Returns:
        Generated draft message as plain text.

    Raises:
        RuntimeError: If the configured provider is unsupported.
    """
    if config.provider != "ollama":
        raise RuntimeError(f"Unsupported provider: {config.provider}")

    return ollama.generate(model=config.model, system=system, user=user)


def _edit_message(*, message: str, editor: str, repo_root: str) -> str:
    """Open an editor to review and edit the draft message.

    Args:
        message: Initial message draft.
        editor: Editor command name ("code", "vim", "nano").
        repo_root: Repository root path (used as the working directory).

    Returns:
        Edited message as plain text.
    """
    # Use a temporary file so the editor can edit a real file on disk.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    ) as f:
        path = Path(f.name)
        f.write(message.rstrip() + "\n")

    try:
        _open_editor(path, editor=editor, cwd=repo_root)
        return path.read_text(encoding="utf-8").strip()
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # Best-effort cleanup: do not fail the command for temp file issues.
            pass


def _open_editor(path: Path, *, editor: str, cwd: str) -> None:
    """Open the selected editor for a file path.

    Args:
        path: File to open.
        editor: Editor command name ("code", "vim", "nano").
        cwd: Working directory for the editor process.

    Raises:
        RuntimeError: If the editor fails to start.
    """
    if editor == "code":
        # `code --wait` blocks until the file is closed, which is ideal here.
        cmd = ["code", "--wait", str(path)]
    elif editor == "vim":
        cmd = ["vim", str(path)]
    elif editor == "nano":
        cmd = ["nano", str(path)]
    else:
        raise RuntimeError(f"Unsupported editor: {editor}")

    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Editor command not found: {editor}. Please install it or change config."
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Editor exited with a non-zero status: {editor}") from e


def _git_commit_message(message: str, *, cwd: str | None) -> None:
    """Create a Git commit using the provided commit message.

    Args:
        message: Final commit message.
        cwd: Working directory to run Git in.

    Raises:
        GitError: If `git commit` fails.
    """
    # Use -F with a temp file to preserve formatting.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    ) as f:
        path = Path(f.name)
        f.write(message.rstrip() + "\n")

    env = os.environ.copy()
    # Avoid prompts from Git helpers; commit should fail fast.
    env.setdefault("GIT_TERMINAL_PROMPT", "0")

    try:
        subprocess.run(
            ["git", "commit", "-F", str(path)],
            cwd=cwd,
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError("git commit failed.") from e
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
