# 設定仕様 (git-compose)

このドキュメントでは、git-compose が使用する設定ファイルの種類、保存場所、および利用可能な設定項目について説明します。


## 設定ファイルの種類

git-compose は、以下の 2 種類の設定スコープをサポートしています。

- **グローバル設定**
- **リポジトリ (ローカル) 設定**

### グローバル設定

グローバル設定は、すべてのリポジトリに対してデフォルトで適用されます。

保存場所：

- `~/.config/compose-message/config.toml`

### リポジトリ設定 (ローカル設定)

リポジトリ固有の設定は、該当リポジトリに対してのみ適用され、
グローバル設定よりも優先されます。

保存場所：

- `<repository>/.compose-message.toml`


## 設定の優先順位

設定値は、以下の順序で解決されます。

1. リポジトリ (ローカル) 設定
2. グローバル設定

※ ローカル設定・グローバル設定のいずれも存在しない場合、git-compose はエラーになります（フォールバック用の既定値は用意していません）。


## 設定ファイル形式

設定ファイルは **TOML 形式** で記述されます。


## 設定項目一覧

### `language`

生成されるコミットメッセージの言語を指定します。

- 型: string
- 許可される値: `"ja"`, `"en"`

### `provider`

使用する LLM プロバイダを指定します。

- 型: string
- 許可される値: `"ollama"`
- 補足: 現在は Ollama のみ対応しています。

### `model`

選択した LLM プロバイダで使用するモデル名を指定します。

- 型: string
- 例: `"llama3"`

### `default_action`

下書き生成後のデフォルトアクションを指定します。

- 型: string
- 許可される値:
  - `"edit"` — プレビュー後に編集フローへ進む
  - `"commit"` — 生成後に即コミットする

### `prompt_profile`

コミットメッセージ生成時に使用するプロンプトプロファイルを指定します。

- 型: string
- 許可される値:
  - `"default"` — 通常のコミットメッセージ生成
  - `"conventional"` — Conventional Commits 向けプロンプト

### `scope_strategy`

Conventional Commits における scope の扱い方を指定します。

- 型: string
- 許可される値:
  - `"auto"` — 差分内容から scope を自動推定する
  - `"omit"` — scope を使用しない

### `max_diff_bytes`

LLM に渡すステージ済み差分の最大サイズ (バイト数) を指定します。

- 型: integer
- 例: `50000`

### `editor`

下書きを編集する際に使用するエディタコマンドを指定します。

- 型: string
- 例: `"code"`, `"vim"`, `"nano"`


## 設定ファイル例

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


## 設定の利用方法

- `git compose init` は、対話形式で設定を作成・更新します。
- `git compose draft` を実行する前に、少なくとも一度 `git compose init` を実行して設定を作成してください。
- `git compose draft` は、設定ファイルを読み込み、コミットメッセージ生成およびフロー制御に使用します。
