# Markdoor TODO

FastAPI・SQLiteで作った、起動コマンド1つで使えるTODOアプリです。
タスクの作成、一覧・単件取得、編集、完了／未完了の変更、削除に対応しています。

Markdoor面接前課題のPDFを原典とし、バックエンドを優先して実装しました。
文字数制限、ページ分割、PATCHの厳密な入力条件は、課題そのものの指定ではなく今回の設計上の選択です。

## セットアップ

必要なもの：Python **3.12 または 3.13**、[uv](https://docs.astral.sh/uv/getting-started/installation/)。
検証環境はPython 3.12.14、uv 0.12.19です。Node.jsは起動・テストに不要です。

uvをまだ導入していない場合は、上記公式手順、またはpipxがある環境なら
`pipx install uv==0.12.19` でインストールできます。

リポジトリを取得／展開し、`pyproject.toml` があるディレクトリで実行します。

```sh
git clone https://github.com/bunichi1008/markdoor-todo.git
cd markdoor-todo
uv sync --frozen
uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- 画面：<http://127.0.0.1:8000/>
- APIドキュメント：<http://127.0.0.1:8000/docs>
- 停止：`Ctrl+C`

依存関係は`pyproject.toml`で直接依存を固定し、`uv.lock`で間接依存まで固定しています。
`--frozen`でロックファイルを更新せずにインストールします。
初回起動時に`data/tasks.sqlite3`とテーブルを自動作成します。別途DBサーバーは不要です。
同じコマンドで再起動すると保存済みのデータを読み出します。

保存先を変える場合は環境変数`TASKS_DATABASE_URL`を指定します（SQLiteのみ対応）。

```sh
# macOS / Linux の例。絶対パスは sqlite://// から始まります。
TASKS_DATABASE_URL=sqlite:////tmp/my-tasks.sqlite3 uv run --frozen uvicorn app.main:app
```

PowerShellでは起動前に`$env:TASKS_DATABASE_URL = "sqlite:///./data/custom.sqlite3"`を設定します。
開発DB、仮想環境、テスト結果、`.env`はGit管理対象外です。

## 画面の使い方

1. タイトルと任意の説明を入力し「タスクを追加」。
2. タスクのタイトル・説明、または「編集」をクリックすると、その行でタイトルと説明を編集できます。
   「変更を保存」で確定、「キャンセル」またはEscで取り消します。Ctrl+Enter／Cmd+Enterでも保存できます。
   チェックボックスで完了／未完了を変更できます（編集中の行は保存・キャンセル後に操作）。
3. 「全件・未完了・完了」で絞り込み、50件ずつ「前へ・次へ」で移動。
4. 「削除」の確認ダイアログで承認すると削除。

成功時は通知を表示し、APIから一覧を再取得します。保存中は操作を無効にします。
保存失敗時は入力を保持し、エラー表示後に再操作できます。
追加フォームと行内の編集欄は独立しています。別タスクの編集やページ移動で未保存の変更を破棄する場合は確認します。
画面内の「再読み込み」では編集中の入力を保持します。
保存には成功して一覧の取得だけが失敗した場合は、その旨を表示します。
この場合は「再読み込み」で一覧を更新してください。
作成日時はAPIではUTC、画面では端末のタイムゾーンによらず日本時間（JST）です。

## テスト

```sh
# API・DB・静的ファイル配信のテスト
uv run --frozen pytest

# 静的解析とフォーマット確認
uv run --frozen ruff check app tests scripts
uv run --frozen ruff format --check app tests scripts
```

各テストは実際の一時SQLiteファイルを使います。開発DBには読み書きしません。
ブラウザテスト10件は通常実行ではスキップされます。全件実行するには：

```sh
uv sync --frozen --group browser
uv run --frozen --group browser playwright install chromium
uv run --frozen --group browser pytest --browser
```

Linuxでブラウザ用システムライブラリが足りない場合は、Playwright公式の
`uv run --frozen --group browser playwright install --with-deps chromium`を利用してください（OSパッケージの導入権限が必要です）。
既存のChromiumを使うこともできます。今回の検証では以下を使用しました。

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium uv run --frozen --group browser pytest --browser
```

ブラウザテストも専用の一時DB・ローカルHTTPサーバーを自動生成・終了します。
デスクトップ／モバイルの確認画像を`test-results/`に保存します。

検証対象：

- CRUD後の取得結果、初期状態、UTC日時、自動採番
- タイトル200／201文字、説明5,000／5,001文字、空白除去、不正型、未知の項目
- PATCHの省略値保持、説明のnull削除、空の更新拒否、作成日時の保持、双方向の状態変更・再送
- 状態別の総件数、同時刻の並び順、ページ境界、一覧クエリの不正値、存在しないIDの404
- アプリ・接続再生成後の永続化、SQL実行後の保存失敗とロールバック、内部例外のログ・非公開化
- 実ブラウザの操作、削除キャンセル、最終ページ削除、二重送信防止、通信失敗からの復旧
- HTML入力の文字表示、再読み込み後の一致、日本時間表示、狭い画面でのレイアウト
- 行内編集、保存・取消のキーボード操作、編集の切り替え確認、入力保持、保存成功後の一覧取得失敗

## API

| メソッド | パス | 成功時 |
| --- | --- | --- |
| POST | `/api/tasks` | 201・作成したタスク |
| GET | `/api/tasks` | 200・一覧と総件数 |
| GET | `/api/tasks/{id}` | 200・タスク |
| PATCH | `/api/tasks/{id}` | 200・更新したタスク |
| DELETE | `/api/tasks/{id}` | 204・本文なし |

作成例：

```json
{"title": "面接の準備", "description": "READMEを確認する"}
```

タスクのレスポンス例（ID・日時はサーバーが生成）：

```json
{
  "id": 1,
  "title": "面接の準備",
  "description": "READMEを確認する",
  "completed": false,
  "created_at": "2026-10-06T07:00:00Z",
  "updated_at": "2026-10-06T07:00:00Z"
}
```

`title`は前後空白除去後1〜200文字、`description`は最大5,000文字でnull可。
`completed`はJSONの真偽値のみ受け付け、作成時の省略値はfalseです。
文字列の`"true"`、数値の`1`などへの型変換はしません。未定義項目も拒否します。
文字数はPythonのUnicodeコードポイント数で数えます。

一覧：`GET /api/tasks?completed=false&limit=50&offset=0`

```json
{"items": [], "total": 0, "limit": 50, "offset": 0}
```

`completed`省略時は全状態。`limit`は1〜100（省略時50）、`offset`は0以上（省略時0）。
`total`は絞り込み後・ページ分割前の件数です。
DB側でフィルタ・件数取得・ページ分割を行い、`created_at DESC, id DESC`で並べます。

PATCHは変更後の値を明示します。例：`{"completed": true}`。

| PATCH入力 | 動作 |
| --- | --- |
| 項目の省略 | 現在値を保持 |
| `description: null` | 説明を削除 |
| `title: null` / `completed: null` | 422 |
| `{}` | 422 |
| 未知の項目・`id`・`created_at`・`updated_at` | 422 |

不正入力は422、存在しないIDの取得・更新・削除は404です。
内部エラーは500と一般的なメッセージを返し、詳細はサーバーのログに記録します。
保存失敗時はサービス層でロールバックします。

## 構成と設計理由

```text
app/
  main.py           # create_app(database_url)、起動時初期化、画面配信、例外応答
  db.py             # 接続、リクエスト単位のセッション、UTC変換
  models.py         # tasksテーブル、DB制約、一覧用インデックス
  schemas.py        # 入力検証、レスポンス定義
  routers/tasks.py  # HTTP受付、サービス呼び出し、HTTP応答
  services/tasks.py # 存在確認、DB操作、保存、ロールバック
  static/           # HTML / CSS / JavaScript
tests/              # API・DBテスト、browser/ に実ブラウザテスト
scripts/benchmark.py
docs/               # 性能測定結果
```

- **同期SQLAlchemy＋SQLite**：3日で作れる規模に合わせ、外部DBの運用を不要にしました。
  FastAPIの同期エンドポイントはスレッドプールで動きます。
- **アプリ生成関数**：テストごとにDBを差し替え、アプリ・接続の再生成を検証できます。
- **小さな責務分割**：Router／Service／Schema／DBを分け、Repositoryインターフェースなどは導入していません。
- **厳密な部分更新**：`model_fields_set`と`exclude_unset=True`で省略と明示的なnullを区別します。
- **日時**：サーバー側でUTCの現在時刻を生成。SQLiteにはUTCとして保存し、読み出し時にタイムゾーンを復元します。
  `created_at`は変更不可。`updated_at`は内容変更時に更新し、同じ値の再送では変わりません。
- **保存単位**：1操作＝1トランザクション。コミット失敗時にロールバックし、成功応答を返しません。
- **一覧**：作成日時＋ID、および完了状態＋作成日時＋IDの複合インデックスを用意しました。
- **画面**：追加ビルド不要のHTML／CSS／JavaScript。入力は`textContent`やフォームの`value`で扱います。

## 性能確認

一時SQLiteに1,000件を投入し、各条件でウォームアップ5回＋測定50回を実行しました。
Linux x86_64、論理CPU 5、Python 3.12.14、SQLite 3.53.1での実測です。

| 条件（各50件取得） | 中央値 | p95 |
| --- | ---: | ---: |
| 全件・先頭ページ | 3.448 ms | 8.173 ms |
| 未完了のみ | 5.338 ms | 11.273 ms |
| 完了のみ | 4.074 ms | 11.191 ms |
| 最終ページ（offset=950） | 5.072 ms | 14.990 ms |

TestClient経由のAPI応答全体（JSON生成を含む）を測定しています。
TCP通信・ブラウザ描画・同時アクセス負荷は含まず、本番環境の応答時間を保証する数値ではありません。
詳細は[測定結果](docs/performance.json)。再測定：

```sh
uv run --frozen python scripts/benchmark.py
```

## 制約と今後の拡張

- 単一利用者向け。認証、通知、カレンダー連携、インポート／エクスポートは対象外です。
- SQLiteは同時大量書き込み向けではありません。大規模化時はDB変更と負荷測定が必要です。
- スキーマの自動作成のみ実装しています。既存DBの構造変更には将来マイグレーションを導入します。
- 同時編集の競合検出やPOSTの冪等キーはありません。送信後に接続が途切れた場合は、再送前に一覧を再読み込みして保存結果を確認してください。
- Dockerは任意項目として見送り、ローカルでの再現手順とテストを優先しました。

### 将来の機能を追加する方針

課題の「拡張性」は、将来の変更箇所と責務を明確にする方針で対応しています。
以下は未実装の拡張案です。認証や通知は今回の対象外のため、ダミーのユーザーIDや未使用のテーブルは追加していません。
既存DBに列・テーブルを追加する際は、まずAlembicなどでマイグレーションを導入します。

| 機能 | データと処理の追加方針 |
| --- | --- |
| タグによる分類 | `tags`と`task_tags`の中間テーブルを追加し、1タスクに複数タグを関連付けます。タグIDの検証をSchema／Serviceに、絞り込みを一覧のDBクエリに追加します。 |
| 期日の設定 | `tasks`に任意の期日を追加し、Schemaと画面の入力・表示に反映します。日付のみか時刻付きかを先に決め、時刻付きなら既存日時と同様にUTC保存・JST表示にします。 |
| 締切通知 | 期日保存とは別に、未完了で通知時刻を迎えたタスクを探す定期実行と通知先が必要です。送信処理はリクエスト処理から分離し、送信履歴・再試行・重複送信対策を設けます。 |
| ユーザー認証 | `users`と`tasks.owner_id`を追加します。FastAPIの`Depends(get_current_user)`で認証済みユーザーを取得し、RouterからServiceへユーザーIDを渡します。 |

認証ではログイン画面を追加するだけでなく、**全操作でタスクの所有者を確認する認可**が必要です。
一覧・総件数・単件取得・更新・削除をすべて`owner_id`で制限し、作成時の所有者は認証情報から設定します。
リクエスト本文のユーザーIDは信用しません。所有者が違うタスクは404とするなど応答を統一し、
他ユーザーのデータを取得・変更できないテストを追加します。
タグもユーザー単位で管理し、既存タスクを誰に割り当てるかは認証導入時の移行方針として決めます。

現在はRouter／Service／Schema／DBを分けているため、この方針で各責務へ変更を追加できます。
認証方式そのもの（外部認証サービスの利用など）は導入時に選び、今は独自認証の骨組みを先行実装しません。
