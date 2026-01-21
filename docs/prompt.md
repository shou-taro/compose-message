# Prompt Specification (git-compose)

This document describes the **prompt and output format specification** used by git-compose
when generating draft commit messages.

This specification is defined as an **output contract**, independent of the LLM provider.

## Basic Principles

- git-compose always generates **structured commit messages**.
- The output format has a consistent structure regardless of user settings or providers.

## Overall Output Structure

A generated commit message must always follow this structure:

```
<subject line>

<body header>
- <bullet item 1>
- <bullet item 2>
...
```

### Structural Constraints

- There must be **exactly one blank line** between the subject and the body.
- The body must always be a **bullet list**.
- The body must contain **at least one bullet item**.
- Output must be **plain text**, not Markdown.

## Subject Line

### Mandatory Requirements

- The subject line must **start with an emoji**.
- The subject must consist of **a single line only**.
- The subject must not contain newline characters.
- The subject line must be **72 characters or fewer**.

### When Conventional Commits Are Enabled

If Conventional Commits are enabled, the subject line follows this format:

```
<emoji> <type>(<scope>): <summary>
```

- `<type>` is a Conventional Commits type (e.g. `feat`, `fix`)
- `<scope>` is either inferred automatically or omitted, depending on configuration
- `<summary>` is a concise description of the change

### When Conventional Commits Are Disabled

When Conventional Commits are disabled, a **typed subject line** is still used.
The subject line follows this format for both English and Japanese:

```
<emoji> <type>: <summary>
```

- `<type>` is a concise classification of the change (e.g. `feat`, `fix`)
- `<summary>` is a concise description of the change

This behaviour is **language-independent** and fixed by the prompt specification.

## Body Header

### Mandatory Requirements

The first line of the body must always be a header line.

- For English:
  ```
  Changes:
  ```
- For Japanese:
  ```
  変更内容:
  ```

This header line must not be omitted.

## Body

### Mandatory Requirements

- The body starts immediately after the body header.
- Each line must start with `- ` (hyphen + single space).
- Each bullet item represents **one concrete change**.

### Content Guidelines

- Content must be based strictly on the staged diff.
- Implementation, behaviour, or structural changes should be stated explicitly.
- Do not include background explanations or opinions.

## Language Switching

The generated natural language follows the configured output language.

| Language | Body Header |
| :--: | :-- |
| `en` | `Changes:` |
| `ja` | `変更内容:` |

## Prohibited Content

The following must **not** appear in the generated output:

- Markdown syntax (`*`, `**`, code fences, etc.)
- An empty body
- A non-bulleted body
- Explanations about the LLM or the prompt itself
- Introductory phrases such as “The following changes were made”

## Role of This Document

- This specification serves both as **user-facing documentation**
  and as a **contract between implementation and tests**.
- Any change to the output format must be accompanied by an update to this document.