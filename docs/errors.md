# Error Specification (git-compose)

This document defines the **error conditions**, **exit codes**, and the **user-facing message contract** for the git-compose CLI.

## Basic Principles

- On error, the CLI exits with a **non-zero exit code**.
- Error messages should be **concise** and clearly indicate the **cause and possible action**.
- Wherever possible, **exception tracebacks are not shown** to users (except for current known cases noted below).

## Exit Codes

- `0`: Successful execution
- `1`: Runtime error / external command failure
- `2`: CLI usage error
- `130`: User interruption (Ctrl+C)

## Error Conditions

### 1. Running Outside a Git Repository

Affected commands: `git compose init --local`, `git compose draft`

- Condition: The current directory is not a Git repository.

- `git compose init --local`
  - Exit code: `1`
  - Message (example):
    - `Not a Git repository. Run this command inside a repository.`

- `git compose draft`
  - Exit code: `1`
  - Message (example):
    - `Not a Git repository. Run this command inside a repository.`

### 2. No Staged Changes Found

Affected command: `git compose draft`

- Condition: `git diff --staged` is empty or contains only whitespace.
- Exit code: `1`
- Message (example):
  - `No staged changes found. Stage files first (e.g. git add -p).`

### 3. Configuration Loading Errors

Affected command: `git compose draft`

- Conditions:
  - The configuration file does not exist.
  - The configuration file contents are invalid.
- Exit code: `1`
- Message (example):
  - `Error: <details>`

> Note: At present, the exception message is displayed as-is.

### 5. Large Staged Diff Behaviour

- Condition: The staged diff size exceeds `max_diff_bytes`.
- Behaviour:
  - This is **not treated as an error**; the diff is automatically truncated.
- Exit code: Not applicable.

### 6. LLM Provider / Model Errors

Affected commands: `git compose init`, `git compose draft`

- `init`:
  - Conditions:
    - Ollama is not available.
    - No Ollama models are installed.
  - Exit code: `1`
  - Message (examples):
    - `Ollama is not available. Please install Ollama and ensure it is on PATH.`
    - `No Ollama models found.`

- `draft`:
  - Condition:
    - An exception occurs while executing the LLM provider.
  - Exit code: `1`
  - Output:
    - The Python exception message is displayed.
    - At present, the traceback is also displayed.

### 7. Git Command Failure

Affected command: `git compose draft`

- Conditions:
  - A Git subprocess exits with a non-zero status.
  - The commit operation (`git commit -F ...`) fails.
- Exit code: `1`
- Message (example):
  - `Git error: <details>`

### 8. User Interruption

Affected commands: `git compose init`, `git compose draft`

- Condition: User interruption such as Ctrl+C.
- Exit code: `130`
- Message (example):
  - `Cancelled by user`

> During interactive prompts, the message is printed by questionary.
> During non-interactive processing, the command itself prints the same message.

## Specification Status

- This document acts as a **contract between the implementation and tests**.
- Any change to error messages or exit codes **must be reflected here and in pytest tests**.
