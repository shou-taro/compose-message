# CLI Specification (git-compose)

This document describes the behaviour and specification of the `git compose` command set.

> git-compose does **not** perform automatic commits.  
> It generates a draft from staged changes, and the final decision is always left to the user.

## Command Overview

- `git compose init`  
  Launches the interactive setup wizard.

- `git compose draft`  
  Generates a commit message draft from staged changes.

## `git compose init`

Runs an interactive wizard to configure how commit messages are generated.

```bash
git compose init
```

### Behaviour

- Starts an interactive setup wizard.
- Can be re-run at any time to update existing settings.
- By default, configuration is saved as **global settings**.

### Configuration Items

The wizard walks through the following items:

- Language (ja / en)
- LLM provider (currently Ollama only)
- Model to use
- Default action
- Whether to enable Conventional Commits
- Scope handling strategy
  - Auto-detect (`auto`)
  - Do not use scope (`omit`)
- Maximum diff size
- Editor to use

### Local Configuration

To configure settings per repository, use the `--local` option:

```bash
git compose init --local
```

When this option is used, configuration is stored under the repository
and takes precedence over global settings.

## `git compose draft`

Generates a structured commit message draft from staged changes.

```bash
git compose draft
```

### Input

- `git compose draft` **must be executed inside a Git repository**.
- Staged changes added via `git add` are used as input.
- If no staged changes are present, no draft is generated.

### Output

- A commit message draft is printed to standard output.
- The output **always follows the structure below**:
  - Subject line (with emoji)
  - Blank line
  - Body header line (`Changes:`)
  - Bullet-point body (at least one item)
- Output is **plain text** (not Markdown).

## Interactive Flow

The `draft` command proceeds through the following interactive flow:

```
1. 🧠 Generate
2. 👀 Preview
3. 📝 Edit / 🔁 Regenerate
4. ✅ Commit (optional)
```

- You may review the preview and choose to edit or regenerate the draft.
- Committing is **not mandatory**.

## Next Step

After previewing the draft, you can choose the next action.

### Exit (no commit)

If Exit is selected:

- No commit is performed.
- The draft is not saved.

Displayed message:

```
🚪 Exited without committing.
You can run this command again when you're ready.
```

### Commit

If Commit is selected, git-compose immediately performs the commit using the generated draft.

- Internally, `git commit -F <message-file>` is used.
- The Git commit editor is **not** launched.
- The commit message used is exactly the draft that was generated and reviewed.

git-compose does not take responsibility for the final content of the commit.