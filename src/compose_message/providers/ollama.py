from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "OllamaError",
    "OllamaCommandResult",
    "has_ollama",
    "list_models",
    "run_model",
]


class OllamaError(RuntimeError):
    """Raised when Ollama is unavailable or an Ollama command fails."""


@dataclass(frozen=True)
class OllamaCommandResult:
    """Result of running an Ollama command.

    Attributes:
        stdout: Standard output. Trailing newlines are removed for convenience.
        stderr: Standard error, stripped of leading/trailing whitespace.
        returncode: Exit status returned by Ollama.
    """

    stdout: str
    stderr: str
    returncode: int


def _run_ollama(
    args: Sequence[str],
    *,
    cwd: str | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> OllamaCommandResult:
    """Runs an Ollama command and returns its output.

    This helper keeps all subprocess handling consistent across the project:
    - Text mode is always enabled.
    - Output is captured for CLI-friendly error messages.
    - Errors are surfaced as `OllamaError`.

    Args:
        args: Ollama arguments (without the leading `ollama`).
        cwd: Working directory for the command. If None, uses the current directory.
        check: If True, non-zero exit codes raise `OllamaError`.
        env: Optional environment overrides.
        input_text: If provided, passed to stdin (useful for some commands).

    Returns:
        An `OllamaCommandResult` containing stdout/stderr and the return code.

    Raises:
        OllamaError: If Ollama is not installed, or if the command fails.
    """
    cmd = ["ollama", *args]

    # Keep behaviour predictable in CI and different shells.
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)

    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            text=True,
            input=input_text,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise OllamaError(
            "ollama command not found. Please install Ollama and ensure it is on PATH."
        ) from e

    # For stdout, we only remove trailing newlines so we do not accidentally
    # alter leading whitespace in generated text.
    stdout = (completed.stdout or "").rstrip("\n")
    stderr = (completed.stderr or "").strip()

    if check and completed.returncode != 0:
        detail = stderr or stdout or f"ollama exited with code {completed.returncode}"
        raise OllamaError(f"ollama {' '.join(args)} failed: {detail}")

    return OllamaCommandResult(
        stdout=stdout, stderr=stderr, returncode=completed.returncode
    )


def has_ollama() -> bool:
    """Checks whether the `ollama` command is available.

    Returns:
        True if `ollama` can be executed; otherwise False.
    """
    try:
        res = _run_ollama(["--version"], check=False)
        return res.returncode == 0
    except OllamaError:
        return False


def list_models() -> list[str]:
    """Lists locally installed Ollama models.

    This parses `ollama list`, which prints a simple table. We only depend on the
    first column (NAME), which is stable and is the value accepted by `ollama run`.

    Returns:
        A list of model names (e.g. `["llama3.1:8b", "qwen2.5:7b"]`).
        Returns an empty list if no models are installed.

    Raises:
        OllamaError: If `ollama list` fails (e.g. Ollama is not running).
    """
    res = _run_ollama(["list"], check=True)
    lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]

    if not lines:
        return []

    # `ollama list` usually prints a header like:
    # NAME  ID  SIZE  MODIFIED
    # We skip it defensively if detected.
    header = lines[0].lower()
    if header.startswith("name") and "id" in header:
        lines = lines[1:]

    models: list[str] = []
    for ln in lines:
        # First whitespace-separated token is the model name.
        # Example: "llama3.1:8b  123abc  4.7 GB  2 weeks ago"
        parts = ln.split()
        if parts:
            models.append(parts[0])

    return models


def run_model(
    model: str,
    prompt: str,
    *,
    max_bytes: int | None = None,
) -> str:
    """Runs an Ollama model with the given prompt and returns the generated text.

    We call `ollama run <model> <prompt>` and capture stdout. This keeps the
    integration dependency-free (no SDK), which is ideal for a small CLI tool.

    Args:
        model: The model name to run (e.g. `llama3.1:8b`).
        prompt: Prompt text to pass to the model.
        max_bytes: If set, truncate the output to at most this many bytes.
            This can protect the CLI from excessive output.

    Returns:
        The generated text (possibly truncated).

    Raises:
        OllamaError: If the model execution fails.
    """
    if not model.strip():
        raise OllamaError("Model name is required.")
    if not prompt.strip():
        raise OllamaError("Prompt is required.")

    # NOTE: Using arguments (not a shell) avoids quoting issues and is safer.
    res = _run_ollama(["run", model, prompt], check=True)
    text = res.stdout

    if max_bytes is not None:
        raw = text.encode("utf-8")
        if len(raw) > max_bytes:
            truncated = raw[:max_bytes].decode("utf-8", errors="ignore")
            text = truncated + "\n\n[output truncated]\n"

    return text
