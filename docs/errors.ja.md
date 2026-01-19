# エラー仕様 (git-compose)

このドキュメントでは、git-compose の CLI における **エラー条件**、**終了コード**、および **ユーザーに表示されるメッセージの契約** を定義します。


## 基本方針

- エラー時は **非ゼロの終了コード** で終了します。
- エラーメッセージは **簡潔** かつ **原因と対処が分かる** 内容にします。
- 可能な限り、例外トレースバックをユーザーに表示しません (開発用のデバッグ出力を除く)。


## 終了コード

- `0`: 正常終了
- `1`: 実行時エラー / 外部コマンド失敗
- `2`: CLI の使い方エラー
- `130`: ユーザーによる中断（Ctrl+C）


## エラー条件一覧

### 1. Git リポジトリ外で実行した

対象コマンド: `git compose init --local`, `git compose draft`

- 条件: 現在ディレクトリが Git リポジトリではない

- `git compose init --local`
  - 終了コード: `1`
  - 表示メッセージ (例):
    - `Not a Git repository. Run this command inside a repository.`

- `git compose draft`
  - 終了コード: `1`
  - 表示メッセージ (例):
    - `Not a Git repository. Run this command inside a repository.`

### 2. ステージ済み差分が存在しない

対象コマンド: `git compose draft`

- 条件: `git diff --staged` が空、または空白のみ
- 終了コード: `1`
- 表示メッセージ (例):
  - `No staged changes found. Stage files first (e.g. git add -p).`

### 3. 設定読み込み時のエラー

対象コマンド: `git compose draft`

- 条件:
  - 設定ファイルが存在しない
  - 設定ファイルの内容が不正
- 終了コード: `1`
- 表示メッセージ (例):
  - `Error: <details>`

※ 現在は例外内容がそのまま表示されます。

### 5. ステージ差分が大きい場合の挙動

- 条件: 差分サイズが `max_diff_bytes` を超える
- 挙動:
  - エラーにはならず、差分は自動的に切り詰められます
- 終了コード: 該当なし

### 6. LLM プロバイダ / モデル関連エラー

対象コマンド: `git compose init`, `git compose draft`

- `init`:
  - 条件:
    - Ollama が利用できない
    - Ollama モデルが 1 つも存在しない
  - 終了コード: `1`
  - 表示メッセージ (例):
    - `Ollama is not available. Please install Ollama and ensure it is on PATH.`
    - `No Ollama models found.`

- `draft`:
  - 条件:
    - LLM プロバイダ実行中の例外
  - 終了コード: `1`
  - 表示メッセージ:
    - Python の例外メッセージが表示されます
    - 現在はトレースバックもそのまま表示されます

### 7. Git コマンドが失敗した

対象コマンド: `git compose draft`

- 条件:
  - Git サブプロセスが非ゼロで終了した
  - コミット処理 (`git commit -F ...`) が失敗した
- 終了コード: `1`
- 表示メッセージ (例):
  - `Git error: <details>`

### 8. ユーザーが中断した

対象コマンド: `git compose init`, `git compose draft`

- 条件: Ctrl+C などの割り込み
- 終了コード: `130`
- 表示メッセージ (例):
  - `Cancelled by user`

※ 対話中は questionary がメッセージを表示し、非対話処理中はコマンド側が同一文言を表示します。


## 仕様の位置づけ

- 本仕様は **実装とテストの契約書** です。
- エラーメッセージや終了コードを変更する場合は、必ず本ドキュメントと pytest を同時に更新してください。
