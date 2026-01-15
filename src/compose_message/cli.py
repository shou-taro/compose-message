from __future__ import annotations

import argparse
from importlib import metadata

from compose_message.commands.draft import draft_command
from compose_message.commands.init import init_wizard


# Helper to get the installed package version
def _package_version() -> str:
    """Return the installed package version.

    We resolve the version from package metadata so `--version` stays in sync
    with the project version declared in `pyproject.toml`.

    Returns:
        Version string. Falls back to "0.0.0" when metadata is unavailable
        (e.g. running from source without installation).
    """
    try:
        # Keep this in sync with the distribution name on PyPI (project.name).
        return metadata.version("compose-message")
    except metadata.PackageNotFoundError:
        return "0.0.0"


VERSION = f"git-compose {_package_version()}"


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser.

    Returns:
        An `argparse.ArgumentParser` configured with subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="git compose",
        description=(
            "Draft commit messages from staged diffs using local or remote LLMs."
        ),
        epilog=(
            "Run `git compose init` to configure defaults, then use `git compose draft`"
            " to generate commit messages."
        ),
    )

    # We use subcommands to mirror the mental model of `git <verb>`.
    subparsers = parser.add_subparsers(dest="command", required=False)

    # `init` is interactive and writes either global or repository-local config.
    init_parser = subparsers.add_parser(
        "init",
        help="Set up git-compose interactively.",
        description=(
            "Run an interactive setup wizard to configure how commit messages "
            "are generated. By default, this writes a global configuration."
        ),
    )
    init_parser.add_argument(
        "--local",
        action="store_true",
        help="Write configuration scoped to the current repository.",
    )

    _ = subparsers.add_parser(
        "draft",
        help="Draft a commit message from staged changes.",
        description=(
            "Generate a commit message draft from staged diffs and open it in your "
            "configured editor for review."
        ),
    )

    # Keep the version flag at the top level for discoverability.
    parser.add_argument(
        "--version",
        action="version",
        version=VERSION,
        help="Show version information and exit.",
    )
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Optional argument list. If None, uses `sys.argv`.

    Returns:
        Process exit code. 0 indicates success.
    """
    parser = build_parser()

    # Parse arguments and dispatch to the selected subcommand.
    args = parser.parse_args(argv)

    if args.command == "init":
        return init_wizard(local=getattr(args, "local", False))

    if args.command == "draft":
        return draft_command()

    # No subcommand provided: show help and exit successfully.
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
