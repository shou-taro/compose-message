from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Explicit re-exports to make the public API of this module clear and stable.
__all__ = [
    "Language",
    "Provider",
    "PromptProfile",
    "ScopeMode",
    "Config",
    "global_config_path",
    "repo_config_path",
    "load_config",
    "load_global_config",
    "load_repo_config",
    "load_effective_config",
    "save_config",
]

# Supported output languages. Keep this explicit to avoid silent fallbacks.
Language = Literal["en", "ja"]

# LLM providers supported by this tool.
Provider = Literal["ollama"]

# Prompt style profiles used when generating commit messages.
PromptProfile = Literal["default", "conventional"]

# How to handle the `scope` part of Conventional Commits
# (e.g. include it automatically or omit it entirely).
ScopeMode = Literal["auto", "none"]


# Immutable configuration object used throughout the application.
# Mutations should happen only via `git compose init`.
@dataclass(frozen=True)
class Config:
    """Repository/user configuration created by `git compose init`.

    Attributes:
        language: Output language for generated commit messages.
        provider: LLM provider identifier. v0.1 supports Ollama only.
        model: Default model name for the configured provider.
        auto_commit: Whether to commit automatically after generating a message.
        prompt_profile: Prompt style/profile name.
        scope_mode: Conventional Commits scope strategy (meaningful when using
            the conventional profile).
        max_diff_bytes: Maximum bytes of diff to include in prompts.
        editor: Editor command to use for editing commit messages.
    """

    language: Language
    provider: Provider
    model: str
    auto_commit: bool
    prompt_profile: PromptProfile
    scope_mode: ScopeMode
    max_diff_bytes: int
    editor: str


def global_config_path() -> Path:
    """Return the global configuration path.

    Returns:
        Path to the global config file.
    """
    return Path.home() / ".config" / "compose-message" / "config.toml"


def repo_config_path(repo_root: str | Path) -> Path:
    """Return the repository-local configuration path.

    Args:
        repo_root: Repository root directory.

    Returns:
        Path to `.compose-message.toml` in the repo root.
    """
    return Path(repo_root) / ".compose-message.toml"


def load_config(path: Path) -> Config:
    """Load config from a TOML file.

    Args:
        path: Path to a TOML config file.

    Returns:
        Parsed `Config`.

    Raises:
        FileNotFoundError: If `path` does not exist.
        ValueError: If the config contains invalid values.
    """
    if not path.exists():
        raise FileNotFoundError(str(path))

    import tomllib  # Python 3.11+

    # Parse TOML eagerly and validate all fields to avoid partial or implicit defaults.
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    language = data.get("language")
    provider = data.get("provider")
    model = data.get("model")
    auto_commit = data.get("auto_commit")
    prompt_profile = data.get("prompt_profile")
    scope_mode = data.get("scope_mode")
    max_diff_bytes = data.get("max_diff_bytes")
    editor = data.get("editor")

    if language not in ("en", "ja"):
        raise ValueError(f"Unsupported language: {language}")
    if provider not in ("ollama",):
        raise ValueError(f"Unsupported provider: {provider}")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")
    if not isinstance(auto_commit, bool):
        raise ValueError("auto_commit must be a boolean.")
    if prompt_profile not in ("default", "conventional"):
        raise ValueError(f"Unsupported prompt_profile: {prompt_profile}")
    if scope_mode not in ("prompt", "auto", "fixed"):
        raise ValueError(f"Unsupported scope_mode: {scope_mode}")
    if not isinstance(max_diff_bytes, int) or max_diff_bytes <= 0:
        raise ValueError("max_diff_bytes must be a positive integer.")
    if editor not in ("code", "vim", "nano"):
        raise ValueError(f"Unsupported editor: {editor}")

    return Config(
        language=language,
        provider=provider,
        model=model.strip(),
        auto_commit=auto_commit,
        prompt_profile=prompt_profile,
        scope_mode=scope_mode,
        max_diff_bytes=max_diff_bytes,
        editor=editor,
    )


def load_global_config() -> Config | None:
    """Load global config if it exists.

    Returns:
        Config if the file exists; otherwise None.

    Raises:
        ValueError: If the config exists but is invalid.
    """
    path = global_config_path()
    if not path.exists():
        return None
    return load_config(path)


def load_repo_config(repo_root: str | Path) -> Config | None:
    """Load repository-local config if it exists.

    Args:
        repo_root: Repository root directory.

    Returns:
        Config if the file exists; otherwise None.

    Raises:
        ValueError: If the config exists but is invalid.
    """
    path = repo_config_path(repo_root)
    if not path.exists():
        return None
    return load_config(path)


def load_effective_config(repo_root: str | Path) -> tuple[Config, Path]:
    """Load the effective config using repo > global precedence.

    Args:
        repo_root: Repository root directory.

    Returns:
        A tuple of (Config, Path) where Path is the source file used.

    Raises:
        FileNotFoundError: If neither repo nor global config exists.
        ValueError: If an existing config file is invalid.
    """

    # Resolve configuration with the following precedence:
    # 1. Repository-local config
    # 2. Global config
    repo_path = repo_config_path(repo_root)
    if repo_path.exists():
        return load_config(repo_path), repo_path

    global_path = global_config_path()
    if global_path.exists():
        return load_config(global_path), global_path

    raise FileNotFoundError("No configuration found. Run `git compose init` first.")


# Configuration is written in a fixed key order to keep diffs readable
# and reviews predictable when the file is checked into version control.
def save_config(path: Path, config: Config) -> Path:
    """Save config to the given path in a stable TOML format.

    Args:
        path: Target file path.
        config: Configuration to persist.

    Returns:
        The path written to.
    """
    # Ensure the directory exists (important for global config).
    path.parent.mkdir(parents=True, exist_ok=True)

    content = "\n".join(
        [
            f'language = "{config.language}"',
            f'provider = "{config.provider}"',
            f'model = "{config.model}"',
            f"auto_commit = {'true' if config.auto_commit else 'false'}",
            f'prompt_profile = "{config.prompt_profile}"',
            f'scope_mode = "{config.scope_mode}"',
            f"max_diff_bytes = {config.max_diff_bytes}",
            f'editor = "{config.editor}"',
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path
