# Radius Team Entry

VALORANT大会向けのDiscordチーム登録・承認システムです。

管理サイト: https://tai-fortnite-tournament.sia-rut1run.chatgpt.site

## 機能

- 大会作成、チームコード発行、人数上限の変更
- `01_チーム名` 形式でDiscordカテゴリ・ロール・チャット・VCを作成
- 入室時に未認証ロール、承認後に認証済み・チームロールを付与
- X ID、Riot ID、表示名（配信記載）、最高ランク、参加区分を登録
- 日本語タグを含むRiot IDに対応し、管理画面からTrackerを開く
- 差し戻し・再申請、チーム変更・辞退、登録解除、チーム削除
- 締切・受付停止・登録確定、人数・ポイントの不備チェック
- ランクポイント設定、チーム合計、`ゲームID,表記名,ランク` の3列CSV

## 構成

| 場所 | 内容 |
| --- | --- |
| `app/` | 管理画面とAPI |
| `lib/` | 状態管理・登録ルール・削除処理 |
| `drizzle/` | Cloudflare D1テーブル作成SQL |
| `public/bridge/` | Python Discord Bot、Docker設定、配布ZIP |
| `tests/` | API、フォーム、Discord処理のテスト |

WebはVinext + Cloudflare Workers + D1、Botはdiscord.pyを使用します。このリポジトリはソースの保存先です。GitHub Pagesは静的配信のため、このWebのAPI・DB・Discord Botを実行しません。現在の管理サイトは上記URLで動作します。

## Botの起動（Windows）

1. `public/bridge`を開きます。
2. 管理サイトの「Discord設定」から接続設定を取得し、`bot.py`と同じフォルダへ`connection.env`として保存します。
3. `DISCORD_TOKEN`にBotトークンを設定します。
4. PowerShellで実行します。

```powershell
py -m pip install -r requirements.txt
py bot.py
```

Server Members Intentを有効にし、Botのロールを管理対象ロールより上へ配置してください。起動中はPowerShellを開いたままにします。接続設定はコミットせず、実行環境だけで管理してください。`connection.env.example`は空のテンプレートです。

Dockerの場合:

```bash
cd public/bridge
docker compose up -d --build
```

## Webの開発

Node.js 22.13.0以上とpnpmを使用します。

```bash
pnpm install --frozen-lockfile
pnpm dev
pnpm build
```

`.openai/hosting.json`は現在のSitesプロジェクトとD1バインディングを宣言しています。本番Secrets・登録データはリポジトリに含めていません。
別の環境へ移す場合はD1、管理者認証、サイトのオリジン、Bot認証キーの設定が必要です。現在の管理者認証はSitesのサインイン・アクセス制限を使用します。

Web側の設定: `DB`（D1）、`SITE_ORIGIN`、`BRIDGE_KEY`（Secret）、`BRIDGE_DISPATCH_TOKEN`（Sitesサービス接続用Secret）。

## テスト

```bash
node tests/workflows.cjs
python -m pip install -r public/bridge/requirements.txt
python tests/test_rank_select.py
python tests/test_bridge_roles.py
python tests/test_team_names.py
python tests/test_removals.py
```

Discord処理のテストはモックを使用します。実際のサーバーでの接続・権限確認は別途必要です。
