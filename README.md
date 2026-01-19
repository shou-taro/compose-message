<p align="center">
  <img 
    src="docs/assets/logo.png" 
    alt="git-compose logo" 
    width="750"
  />
</p>

# 🎼 git-compose — Compose Better Commit Messages

[![CI](https://github.com/shou-taro/compose-message/actions/workflows/ruff.yml/badge.svg)](https://github.com/shou-taro/compose-message/actions)
[![PyPI](https://img.shields.io/pypi/v/compose-message)](https://pypi.org/project/compose-message/)
[![License](https://img.shields.io/pypi/l/compose-message)](./LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230)](https://github.com/astral-sh/ruff)
[![Local-first](https://img.shields.io/badge/local--first-yes-4caf50)](#)
[![LLM](https://img.shields.io/badge/LLM-Ollama-000000)](https://ollama.com)
[![Status](https://img.shields.io/badge/status-v0.1--experimental-yellow)](#)

📘 日本語版は [こちら](README.ja.md)

A CLI tool that generates **structured commit message drafts** from staged changes.

<img
  src="docs/assets/draft-preview.png"
  alt="git-compose draft command showing preview and interactive flow"
  width="800"
/>

## ❓ Why

- Commit messages remain in the history for a long time, so readability and consistency are important.
- Conventional Commits standardise the subject line, but do not define how to write the body.
- git-compose provides an environment focused on the content by fixing the body structure.

## ✨ Features

- 🧠 Generate commit messages from staged changes
- 👀 Interactive flow: preview → edit → regenerate
- 📜 Support for Conventional Commits (optional)
- 📐 Standardised body structure to prevent inconsistency
- 🔒 Local LLM execution using Ollama (no external API required)
- 🔌 Planned support for multiple LLM providers such as OpenAI, Gemini, Claude

## 🚀 Quick Start

### Installation

> ⚠️ PyPI release coming soon.  
> For now, install from source:

```bash
git clone https://github.com/shou-taro/compose-message.git
cd compose-message
pip install -e .
```

### Initial Setup

```bash
git compose init
```

Configure the following interactively:

- Language (ja / en)
- Ollama model to use
- Whether to enable Conventional Commits
- Editor to use, etc.

Settings are saved globally by default.

To configure per repository:

```bash
git compose init --local
```

### Generate a Commit Message Draft

```bash
git add .
git compose draft
```

## 🧩 Flow of the draft Command

```
1. 🧠 Generate
2. 👀 Preview
3. 📝 Edit / 🔁 Regenerate
4. ✅ Commit (optional)
```

Committing is **not mandatory**.  
You can review the generated draft and commit only when satisfied.

## 📝 Output Commit Message Format

### When Conventional Commits are Enabled

```text
✨ feat(draft): Generate message with preview

Changes:
- Generate message from staged changes
- Display preview
- Support regeneration
```

### When Conventional Commits are Disabled

```text
✨ Generate message with preview

Changes:
- Generate message from staged changes
- Display preview
- Support regeneration
```

### Notes

- Subject → blank line → body, which is standard Git structure
- Body is always a bullet list (at least one item)
- Plain text, not Markdown

## 🧠 Design Philosophy

- git-compose does **not auto-commit**
- Final decision is always left to the user
- Generated content is a "draft" intended for editing

## 🚫 Non-goals

git-compose is not intended for:

- Automated releases or version management
- CI/CD integration
- Project management tool functionality

## 📦 Current Limitations (v0.1)

- Currently only supports the Ollama LLM provider (planned to expand)
  - Ollama must be installed and running locally
- External files for commit message templates are not supported yet
- Unit tests with pytest will be added in the future

## 📄 License

MIT License