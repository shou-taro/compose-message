from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

# Public API of the Ollama provider.
# These symbols are imported by higher-level commands and the CLI.
__all__ = [
    "OllamaError",
    "OllamaCommandResult",
    "has_ollama",
    "list_models",
    "generate",
    "run_model",
]


class OllamaError(RuntimeError):
    """Error raised when Ollama is unavailable or a command fails."""


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
    """Run an Ollama CLI command and return its result.

    This helper keeps all subprocess handling consistent across the project:
    - Text mode is always enabled.
    - Output is captured for CLI-friendly error messages.
    - Failures are reported as `OllamaError`.

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

    # Merge environment variables explicitly so behaviour is consistent
    # across shells and CI environments.
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

    # Remove trailing newlines from stdout without touching leading whitespace.
    stdout = (completed.stdout or "").rstrip("\n")
    stderr = (completed.stderr or "").strip()

    if check and completed.returncode != 0:
        detail = stderr or stdout or f"ollama exited with code {completed.returncode}"
        raise OllamaError(f"ollama {' '.join(args)} failed: {detail}")

    return OllamaCommandResult(
        stdout=stdout, stderr=stderr, returncode=completed.returncode
    )


def has_ollama() -> bool:
    """Return True if the `ollama` CLI command is available."""
    try:
        res = _run_ollama(["--version"], check=False)
        return res.returncode == 0
    except OllamaError:
        return False


def list_models() -> list[str]:
    """Return a list of locally installed Ollama models.

    This function parses the output of `ollama list` and extracts the model
    names accepted by `ollama run`.

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

    # `ollama list` usually prints a header row; skip it if present.
    header = lines[0].lower()
    if header.startswith("name") and "id" in header:
        lines = lines[1:]

    models: list[str] = []
    for ln in lines:
        # Example line format:
        # llama3.1:8b  123abc  4.7 GB  2 weeks ago
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
    """Run an Ollama model with a prompt and return the generated text.

    This function invokes `ollama run` directly, without using an SDK.

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

    # Use a direct subprocess call (no shell) to avoid quoting issues.
    res = _run_ollama(["run", model, prompt], check=True)
    text = res.stdout

    if max_bytes is not None:
        raw = text.encode("utf-8")
        if len(raw) > max_bytes:
            truncated = raw[:max_bytes].decode("utf-8", errors="ignore")
            text = truncated + "\n\n[output truncated]\n"

    return text


def generate(
    *,
    model: str,
    system: str,
    user: str,
    max_bytes: int | None = None,
) -> str:
    """Generate text using separate system and user prompts.

    Ollama's CLI accepts a single prompt string. This helper combines the
    system and user prompts into a stable plain-text format before invoking
    the model.

    Args:
        model: The model name to run (e.g. `llama3.1:8b`).
        system: System prompt text (instructions and constraints).
        user: User prompt text (task input, such as staged diffs).
        max_bytes: If set, truncate the output to at most this many bytes.

    Returns:
        Generated text (possibly truncated).

    Raises:
        OllamaError: If the model execution fails.
    """

    # Combine prompts in a simple, explicit format so behaviour is reproducible.
    combined = "\n\n".join(
        [
            "[system]",
            system.strip(),
            "[user]",
            user.strip(),
        ]
    ).strip()

    return run_model(model, combined, max_bytes=max_bytes)
