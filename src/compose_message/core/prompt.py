from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "Language",
    "PromptProfile",
    "ScopeStrategy",
    "PromptParts",
    "build_commit_message_prompt",
]

# Supported output languages for generated commit messages.
# The set is intentionally small to keep prompts predictable and reviewable.
Language = Literal["en", "ja"]

# Prompt profiles define the overall commit message style.
# - default: a plain Git commit message
# - conventional: Conventional Commits format (type(scope): subject)
# with a bullet-list body
PromptProfile = Literal["default", "conventional"]

# Scope handling strategy when using Conventional Commits.
# - auto: include a scope inferred from the staged diff
# - omit: omit the scope entirely (use `type: subject`)
ScopeStrategy = Literal["auto", "omit"]


@dataclass(frozen=True)
class PromptParts:
    """Prompt components used to construct a model request.

    The prompt is split into a system part (behaviour and constraints)
    and a user part (task description and concrete input).

    Attributes:
        system: Instructions that define how the model should behave.
        user: Task-specific input, including repository context and diff.
    """

    system: str
    user: str


def build_commit_message_prompt(
    staged_diff: str,
    *,
    status_porcelain: str | None = None,
    max_subject_length: int = 72,
    language: Language = "en",
    prompt_profile: PromptProfile = "default",
    scope_strategy: ScopeStrategy = "omit",
) -> PromptParts:
    """Build a prompt for generating a Git commit message from staged changes.

    The staged diff is treated as the source of truth. The resulting prompt is
    deterministic, minimal, and provider-agnostic.

    Args:
        staged_diff: Output of `git diff --staged`. Must not be empty.
        status_porcelain: Optional output of `git status --porcelain` for extra context.
            This is intentionally high-level and avoids duplicating the full diff.
        max_subject_length: Maximum length for the commit subject line.
        language: Output language for the commit message.
        prompt_profile: Commit message style profile.
            Use "conventional" to request the Conventional Commits format.
            The body is required as a bullet list of changes.
        scope_strategy: Scope handling strategy for Conventional Commits.
            Ignored when prompt_profile is "default".

    Returns:
        A `PromptParts` instance containing a system message and a user message.

    Raises:
        ValueError: If `staged_diff` is empty or only whitespace.
        ValueError: If `language` is not supported.
        ValueError: If `prompt_profile` is not supported.
        ValueError: If `scope_strategy` is not supported.
    """
    if not staged_diff.strip():
        raise ValueError("staged_diff is required and must not be empty.")

    # Select language-specific templates.
    templates = _TEMPLATES.get(language)
    if templates is None:
        # This should be unreachable due to the Literal type, but keep it robust
        # for runtime usage.
        raise ValueError(f"Unsupported language: {language}")

    if prompt_profile not in ("default", "conventional"):
        raise ValueError(f"Unsupported prompt_profile: {prompt_profile}")
    if scope_strategy not in ("auto", "omit"):
        raise ValueError(f"Unsupported scope_strategy: {scope_strategy}")

    # System message: defines behaviour, constraints, and output rules.
    system_lines: list[str] = [
        templates.system_role,
    ]

    if prompt_profile == "default":
        system_lines.append(templates.system_task_default)
    else:
        system_lines.append(templates.system_task_conventional)

    system_lines.append(
        templates.system_subject.format(max_subject_length=max_subject_length)
    )
    system_lines.append(templates.system_body)

    # The imperative mood is customary for English commit messages.
    if language == "en":
        system_lines.append(templates.system_imperative)

    # Additional constraints for the Conventional Commits profile.
    if prompt_profile == "conventional":
        system_lines.append(templates.system_conventional_intro)
        if scope_strategy == "auto":
            system_lines.append(templates.system_conventional_scope_auto)
        else:
            system_lines.append(templates.system_conventional_scope_omit)

    system_lines.append(templates.system_accuracy)
    system_lines.append(templates.system_no_thoughts)
    system_lines.append(templates.system_plain)
    if templates.system_output_language:
        system_lines.append(templates.system_output_language)

    system = "\n".join(system_lines)

    # User message: concrete instructions and repository context.
    # Status is included as a lightweight overview before the full diff.
    user_sections: list[str] = [
        templates.user_intro,
        "",
        templates.user_format_title,
    ]

    if prompt_profile == "default":
        user_sections.extend(templates.user_format_lines_default)
    else:
        user_sections.extend(templates.user_format_lines_conventional)

    user_sections.append("")

    if status_porcelain and status_porcelain.strip():
        user_sections += [
            templates.user_status_title,
            status_porcelain.strip(),
            "",
        ]

    user_sections += [
        templates.user_diff_title,
        staged_diff.rstrip("\n"),
    ]

    user = "\n".join(user_sections)
    return PromptParts(system=system, user=user)


@dataclass(frozen=True)
class _Template:
    """Language-specific prompt template.

    Each language uses the same structure to ensure consistent behaviour
    across profiles and providers.
    """

    system_role: str
    system_task_default: str
    system_task_conventional: str
    system_subject: str
    system_body: str
    system_imperative: str
    system_accuracy: str
    system_no_thoughts: str
    system_plain: str
    system_output_language: str
    system_conventional_intro: str
    system_conventional_scope_auto: str
    system_conventional_scope_omit: str
    user_intro: str
    user_format_title: str
    user_format_lines_default: list[str]
    user_format_lines_conventional: list[str]
    user_status_title: str
    user_diff_title: str


# Language-specific prompt templates.
# The structure is kept identical across languages to ensure consistent behaviour.
_TEMPLATES: dict[Language, _Template] = {
    "en": _Template(
        system_role="You are a senior software engineer.",
        system_task_default=(
            "Write a Git commit message that accurately reflects the staged changes."
        ),
        system_task_conventional=(
            "Write a Conventional Commits message with an emoji prefix "
            "that accurately reflects the staged changes."
        ),
        system_subject=(
            "The first line (subject) must be <= {max_subject_length} characters."
        ),
        system_body=(
            "After the subject line, add a blank line. "
            "Then output the line 'Changes:' and a bullet list of changes using '- '. "
            "The body must contain at least one bullet."
        ),
        system_imperative="Use the imperative mood (e.g. 'Add', 'Fix', 'Refactor').",
        system_accuracy="Avoid mentioning details not present in the diff.",
        system_no_thoughts=(
            "Do not include analysis, reasoning, or self-talk (e.g. 'Thinking...'). "
            "Output the commit message only."
        ),
        system_plain="Output plain text only. Do not include Markdown code fences.",
        system_output_language="",
        system_conventional_intro=(
            "The subject line must start with an emoji "
            "and follow Conventional Commits: '<emoji> type(scope): subject' "
            "or '<emoji> type: subject'. The emoji must be the first token."
        ),
        system_conventional_scope_auto=(
            "Include a scope and infer it from the diff "
            "(choose a short, meaningful scope)."
        ),
        system_conventional_scope_omit="Do not include a scope (use 'type: subject').",
        user_intro="Generate a commit message for the following staged changes.",
        user_format_title="Output format:",
        user_format_lines_default=[
            "1) Subject line starting with an emoji: <emoji> Subject",
            "2) Blank line",
            "3) Body starting with 'Changes:' followed by a bullet list of changes "
            "using '- ' (at least one bullet)",
        ],
        user_format_lines_conventional=[
            "1) Subject line in Conventional Commits format starting "
            "with an emoji: <emoji> type(scope): subject or <emoji> type: subject",
            "2) Blank line",
            "3) Body starting with 'Changes:' followed by a bullet list of changes "
            "using '- ' (at least one bullet)",
            "Types: feat, fix, docs, style, refactor, perf, test, build, ci, "
            "chore, revert",
        ],
        user_status_title="Repository status (porcelain):",
        user_diff_title="Staged diff:",
    ),
    "ja": _Template(
        system_role="あなたは経験豊富なソフトウェアエンジニアです。",
        system_task_default=(
            "以下のステージ差分に基づき、"
            "適切な Git のコミットメッセージを作成してください。"
        ),
        system_task_conventional=(
            "以下のステージ差分に基づき、"
            "絵文字 (emoji) を先頭に付けた Conventional Commits 形式の"
            "コミットメッセージを作成してください。"
        ),
        system_subject=(
            "1行目（件名）は {max_subject_length} 文字以内を目安に簡潔にしてください。"
        ),
        system_body=(
            "件名の後に必ず空行を入れ、その次の行に「変更内容:」と書いてください。"
            "その後に「- 」で始まる箇条書きで変更内容を記載してください。"
            "本文は最低1つの箇条書きを含めてください。"
        ),
        system_imperative="",  # Not used for Japanese.
        system_accuracy="差分に含まれない内容を推測して断定しないでください。",
        system_no_thoughts=(
            "思考過程 (分析・推論) や独り言 (例: 'Thinking...') は出力せず、"
            "コミットメッセージ本文のみを出力してください。"
        ),
        system_plain=(
            "出力はプレーンテキストのみとし、"
            "Markdown のコードブロック (```) は使わないでください。"
        ),
        system_output_language="コミットメッセージは日本語で書いて下さい。",
        system_conventional_intro=(
            "件名は絵文字（emoji）を先頭に付けた形式で、"
            "「<emoji> type(scope): subject」または「<emoji> type: subject」の"
            "いずれかにしてください。"
            "絵文字は件名の最初に必ず配置してください。"
        ),
        system_conventional_scope_auto=(
            "scope を含め、差分から短く意味のある scope を推測してください。"
        ),
        system_conventional_scope_omit=(
            "scope は含めず、type: subject の形式にしてください。"
        ),
        user_intro="以下のステージされた変更に対するコミットメッセージを生成してください。",
        user_format_title="出力形式:",
        user_format_lines_default=[
            "1) 件名行は絵文字を先頭に付けてください: <emoji> タイプ(スコープ): 件名 "
            "または <emoji> タイプ: 件名",
            "2) 空行",
            "3) 本文は「変更内容:」の行から始め、その後に「- 」で始まる箇条書きで"
            "変更内容を記載してください (最低1つ)",
        ],
        user_format_lines_conventional=[
            "1) 件名行は絵文字を先頭に付けた "
            "Conventional Commits 形式: <emoji> type(scope): subject "
            "または <emoji> type: subject",
            "2) 空行",
            "3) 本文は「変更内容:」の行から始め、その後に「- 」で始まる箇条書きで"
            "変更内容を記載してください (最低1つ)",
            "type の例: feat, fix, docs, style, refactor, perf, test, build, ci, "
            "chore, revert",
        ],
        user_status_title="リポジトリ状態 (porcelain):",
        user_diff_title="ステージ差分:",
    ),
}
