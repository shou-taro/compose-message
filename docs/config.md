# Configuration Specification (git-compose)

This document describes the configuration files used by git-compose, their locations,
and the available configuration options.

## Configuration Scopes

git-compose supports the following two configuration scopes:

- **Global configuration**
- **Repository (local) configuration**

### Global configuration

The global configuration applies to all repositories by default.

Location:

- `~/.config/compose-message/config.toml`

### Repository configuration (local configuration)

Repository-specific configuration applies only to the corresponding repository
and takes precedence over the global configuration.

Location:

- `<repository>/.compose-message.toml`

## Configuration Resolution Order

Configuration values are resolved in the following order:

1. Repository (local) configuration
2. Global configuration

If neither a local nor a global configuration exists, git-compose exits with an error.
No fallback or built-in default values are provided.

## Configuration File Format

Configuration files are written in **TOML format**.

## Configuration Options

### `language`

Specifies the language used for generated commit messages.

- Type: string
- Allowed values: `"ja"`, `"en"`

### `provider`

Specifies the LLM provider to use.

- Type: string
- Allowed values: `"ollama"`
- Note: Currently, only Ollama is supported.

### `model`

Specifies the model name used by the selected LLM provider.

- Type: string
- Example: `"llama3"`

### `default_action`

Specifies the default action after generating a draft.

- Type: string
- Allowed values:
  - `"edit"` — proceed to the edit flow after preview
  - `"commit"` — commit immediately after generation

### `prompt_profile`

Specifies the prompt profile used for commit message generation.

- Type: string
- Allowed values:
  - `"default"` — standard commit message generation
  - `"conventional"` — prompt optimised for Conventional Commits

### `scope_strategy`

Specifies how the scope is handled when using Conventional Commits.

- Type: string
- Allowed values:
  - `"auto"` — automatically infer the scope from staged changes
  - `"omit"` — do not include a scope

### `max_diff_bytes`

Specifies the maximum size (in bytes) of the staged diff passed to the LLM.

- Type: integer
- Example: `50000`

### `editor`

Specifies the editor command used when editing drafts.

- Type: string
- Examples: `"code"`, `"vim"`, `"nano"`

## Example Configuration

```toml
language = "en"
provider = "ollama"
model = "llama3"
default_action = "commit"
prompt_profile = "default"
scope_strategy = "auto"
max_diff_bytes = 50000
editor = "code"
```

## How Configuration Is Used

- `git compose init` creates or updates configuration files interactively.
- `git compose draft` requires an existing configuration and uses it
  to control commit message generation and flow behaviour.
