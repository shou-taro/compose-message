from __future__ import annotations

from pathlib import Path

import questionary

from compose_message.core import git as git_mod
from compose_message.core.config import (
    Config,
    DefaultAction,
    Provider,
    ScopeStrategy,
    global_config_path,
    repo_config_path,
    save_config,
)
from compose_message.providers import ollama as ollama_mod

__all__ = ["init_wizard"]


# Prompt marker shown by questionary before each question.
# Keep this short and visually distinct to fit in narrow terminals.
QMARK = "❯"


def init_wizard(*, local: bool) -> int:
    """Run the interactive setup wizard and write a config file.

    The wizard asks a fixed set of questions in a stable order and persists the
    result to a TOML file. The target file depends on the `local` flag:

    - local=False: global config
    - local=True:  repository-local config

    Args:
        local: If True, write repository-local config into the current Git
            repository root. If False, write global config under the user's
            config directory.

    Returns:
        Process exit code. 0 on success; non-zero on cancellation or error.
    """

    # Decide where to write the configuration.
    # - Global config is user-scoped and does not require a Git repository.
    # - Local config is repo-scoped and requires a Git repository.
    if local:
        if not git_mod.is_git_repo():
            print("Not a Git repository. Please run this inside a repository.")
            return 2

        # Resolve the repository root so we always write to the correct location.
        repo_root = (
            git_mod.get_repo_root() if hasattr(git_mod, "get_repo_root") else None
        )
        if repo_root is None:
            # Fall back to the current directory.
            repo_root = str(Path.cwd())

        target_path = repo_config_path(repo_root)
        target_label = "Repository"

    else:
        # Global config is stored under the user's config directory.
        target_path = global_config_path()
        target_label = "Global"

    # Ensure the destination directory exists (especially important for global config).
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Print a brief overview so users know what will be configured.
    print()
    print("=" * 72)
    print(f"git compose · Setup ({target_label})")
    if local:
        print(f"Repository root: {repo_root}")
    print("Let's configure how commit messages are generated.")
    print(f"Config file: {target_path}")
    print()
    print("We'll ask you about:")
    print("  1. 🌐 Language")
    print("  2. 🧩 Provider")
    print("  3. 🧠 Model")
    print("  4. ✅ Default action")
    print("  5. 🧾 Conventional Commits")
    print("  6. 🏷️  Scope")
    print("  7. 📦 Max diff size")
    print("  8. ✍️  Editor")
    print()
    print("Tip: You can re-run this wizard at any time to update the settings.")
    print("=" * 72)
    print()

    # Avoid accidental overwrites by confirming when a config file already exists.
    if target_path.exists():
        overwrite = questionary.confirm(
            "A configuration file already exists. Overwrite it?",
            default=False,
        ).ask()
        if overwrite is None or overwrite is False:
            print("Cancelled.")
            return 1
        print()

    # 1) Language (output locale)
    print("🌐 Language")
    language = questionary.select(
        "Select output language:",
        qmark=QMARK,
        choices=[
            questionary.Choice("English (en)", value="en"),
            questionary.Choice("日本語 (ja)", value="ja"),
        ],
    ).ask()
    if language is None:
        print("Cancelled.")
        return 1

    # 2) Provider (v0.1: Ollama only)
    print("\n🧩 Provider")
    provider: Provider = questionary.select(
        "Select provider:",
        qmark=QMARK,
        choices=[questionary.Choice("Ollama", value="ollama")],
    ).ask()
    if provider is None:
        print("Cancelled.")
        return 1

    # 3) Model (from `ollama list`)
    if provider == "ollama":
        if not ollama_mod.has_ollama():
            print(
                "Ollama is not available. "
                "Please install Ollama and ensure it is on PATH."
            )
            return 2

        models = ollama_mod.list_models()
        if not models:
            print("No Ollama models found.")
            print("Please install a model first, for example:")
            print("  ollama pull llama3.1:8b")
            return 2

        print("\n🧠 Model")
        model = questionary.select(
            "Select a default Ollama model:",
            qmark=QMARK,
            choices=[questionary.Choice(m, value=m) for m in models],
        ).ask()
        if model is None:
            print("Cancelled.")
            return 1

    else:
        print(f"Unsupported provider: {provider}")
        return 2

    # 4) Default action in the draft command's "Next step" menu
    print("\n✅ Default action")
    default_action: DefaultAction = questionary.select(
        "Select the default action in the Next step menu:",
        qmark=QMARK,
        choices=[
            questionary.Choice("✍️  Edit (recommended)", value="edit"),
            questionary.Choice("✅ Commit now", value="commit"),
        ],
        default="edit",
    ).ask()
    if default_action is None:
        print("Cancelled.")
        return 1

    # 5) Conventional Commits support
    print("\n🧾 Commit message style")
    use_conventional = questionary.confirm(
        "Use Conventional Commits format?:",
        qmark=QMARK,
        default=True,
    ).ask()
    if use_conventional is None:
        print("Cancelled.")
        return 1

    prompt_profile = "conventional" if use_conventional else "default"

    # 6) Scope handling for Conventional Commits
    if use_conventional:
        print("\n🏷️  Scope")
        scope_strategy: ScopeStrategy = questionary.select(
            "Include a scope in commit messages?:",
            qmark=QMARK,
            choices=[
                questionary.Choice(
                    "Include scope (try to infer automatically)", value="auto"
                ),
                questionary.Choice("Do not include scope", value="omit"),
            ],
            default="auto",
        ).ask()
        if scope_strategy is None:
            print("Cancelled.")
            return 1
    else:
        # Scope is only relevant when Conventional Commits are enabled.
        scope_strategy = "omit"

    # 7) Maximum diff size included in prompts
    print("\n📦 Max diff size")
    max_diff_bytes_str = questionary.text(
        "Maximum diff bytes to include in prompts:",
        qmark=QMARK,
        default="200000",
        validate=lambda s: s.isdigit() and int(s) > 0,
    ).ask()
    if max_diff_bytes_str is None:
        print("Cancelled.")
        return 1

    max_diff_bytes = int(max_diff_bytes_str)

    # 8) Editor used to edit the generated message
    print("\n✍️  Editor")
    editor = questionary.select(
        "Select editor for message editing:",
        qmark=QMARK,
        choices=[
            questionary.Choice("VS Code (code)", value="code"),
            questionary.Choice("Vim (vim)", value="vim"),
            questionary.Choice("Nano (nano)", value="nano"),
        ],
        default="code",
    ).ask()
    if editor is None:
        print("Cancelled.")
        return 1

    print("\nSummary:")
    print(f"  ✅ Language: {language!r}")
    print(f"  ✅ Provider: {provider!r}")
    print(f"  ✅ Model: {model!r}")
    print(f"  ✅ Default action: {default_action}")
    print(f"  ✅ Conventional: {'on' if use_conventional else 'off'}")
    print(f"  ✅ Scope: {scope_strategy}")
    print(f"  ✅ Max diff: {max_diff_bytes}")
    print(f"  ✅ Editor: {editor!r}")

    # Persist the configuration in a stable order to keep diffs readable.
    config = Config(
        language=language,
        provider=provider,
        model=model,
        default_action=default_action,
        prompt_profile=prompt_profile,
        scope_strategy=scope_strategy,
        max_diff_bytes=max_diff_bytes,
        editor=editor,
    )

    path = save_config(target_path, config)

    print(f"\nWrote config: {path}")
    return 0
