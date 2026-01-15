from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Explicit re-exports to make the public API of this module clear and stable.
__all__ = [
    "Language",
    "Provider",
    "PromptProfile",
    "ScopeStrategy",
    "DefaultAction",
    "Config",
    "global_config_path",
    "repo_config_path",
    "load_config",
    "load_global_config",
    "load_repo_config",
    "load_effective_config",
    "save_config",
]

# Output language for generated commit messages.
Language = Literal["en", "ja"]

# LLM providers supported by this tool (v0.1: Ollama only).
Provider = Literal["ollama"]

# Commit message style profile.
# - default: plain Git commit message
# - conventional: Conventional Commits format
PromptProfile = Literal["default", "conventional"]

# Scope handling strategy when using the Conventional Commits profile.
# - auto: include a scope inferred from the staged diff
# - omit: omit the scope entirely
ScopeStrategy = Literal["auto", "omit"]

# Default selection in the draft command's "Next step" menu.
# - edit: start by editing the generated message
# - commit: start by committing the generated message
DefaultAction = Literal["edit", "commit"]


# Immutable configuration object used throughout the application.
# Mutations should happen only via `git compose init`.
@dataclass(frozen=True)
class Config:
    """User or repository configuration created by `git compose init`.

    The effective configuration is resolved with repository-local settings
    taking precedence over the global configuration.

    Attributes:
        language: Output language for generated commit messages.
        provider: LLM provider identifier.
        model: Default model name for the configured provider.
        default_action: Default selection in the draft command's "Next step" menu.
        prompt_profile: Commit message style profile.
        scope_strategy: Scope handling strategy for Conventional Commits.
        max_diff_bytes: Maximum size of the diff included in prompts.
        editor: Editor command used to edit the generated message.
    """

    language: Language
    provider: Provider
    model: str
    default_action: DefaultAction
    prompt_profile: PromptProfile
    scope_strategy: ScopeStrategy
    max_diff_bytes: int
    editor: str


def global_config_path() -> Path:
    """Return the path to the global configuration file."""
    return Path.home() / ".config" / "compose-message" / "config.toml"


def repo_config_path(repo_root: str | Path) -> Path:
    """Return the path to the repository-local configuration file."""
    return Path(repo_root) / ".compose-message.toml"


def load_config(path: Path) -> Config:
    """Load and validate configuration from a TOML file."""
    if not path.exists():
        raise FileNotFoundError(str(path))

    import tomllib  # Python 3.11+

    # Parse TOML eagerly and validate all fields to avoid partial or implicit defaults.
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    language = data.get("language")
    provider = data.get("provider")
    model = data.get("model")
    default_action = data.get("default_action")

    if default_action is None:
        raise ValueError("default_action is required.")

    prompt_profile = data.get("prompt_profile")
    scope_strategy = data.get("scope_strategy")

    if scope_strategy is None:
        raise ValueError("scope_strategy is required.")

    max_diff_bytes = data.get("max_diff_bytes")
    editor = data.get("editor")

    if language not in ("en", "ja"):
        raise ValueError(f"Unsupported language: {language}")
    if provider not in ("ollama",):
        raise ValueError(f"Unsupported provider: {provider}")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")
    if default_action not in ("edit", "commit"):
        raise ValueError(f"Unsupported default_action: {default_action}")
    if prompt_profile not in ("default", "conventional"):
        raise ValueError(f"Unsupported prompt_profile: {prompt_profile}")
    if scope_strategy not in ("auto", "omit"):
        raise ValueError(f"Unsupported scope_strategy: {scope_strategy}")
    if not isinstance(max_diff_bytes, int) or max_diff_bytes <= 0:
        raise ValueError("max_diff_bytes must be a positive integer.")
    if editor not in ("code", "vim", "nano"):
        raise ValueError(f"Unsupported editor: {editor}")

    return Config(
        language=language,
        provider=provider,
        model=model.strip(),
        default_action=default_action,
        prompt_profile=prompt_profile,
        scope_strategy=scope_strategy,
        max_diff_bytes=max_diff_bytes,
        editor=editor,
    )


def load_global_config() -> Config | None:
    """Load the global configuration if it exists."""
    path = global_config_path()
    if not path.exists():
        return None
    return load_config(path)


def load_repo_config(repo_root: str | Path) -> Config | None:
    """Load the repository-local configuration if it exists."""
    path = repo_config_path(repo_root)
    if not path.exists():
        return None
    return load_config(path)


def load_effective_config(repo_root: str | Path) -> tuple[Config, Path]:
    """Load the effective configuration (repository-local overrides global)."""
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
    """Write configuration to disk in a stable, human-editable TOML format."""
    # Ensure the parent directory exists before writing the file.
    path.parent.mkdir(parents=True, exist_ok=True)

    content = "\n".join(
        [
            f'language = "{config.language}"',
            f'provider = "{config.provider}"',
            f'model = "{config.model}"',
            f'default_action = "{config.default_action}"',
            f'prompt_profile = "{config.prompt_profile}"',
            f'scope_strategy = "{config.scope_strategy}"',
            f"max_diff_bytes = {config.max_diff_bytes}",
            f'editor = "{config.editor}"',
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path
