# AIニュース自動要約＆メール送信アプリ

このアプリケーションは、NewsAPIを利用してAI関連の最新ニュースを自動で取得し、Google Gemini APIで内容を日本語で要約した上で、指定されたGmailアドレスへ毎日定期的に送信します。

## 機能

- NewsAPIからのAI関連ニュースの取得（キーワード: "AI", "人工知能", "機械学習"）
- 取得したニュース記事の本文抽出
- Google Gemini APIによる日本語でのニュース要約
- 要約済みニュースのGmailへの自動送信
- 毎日定時実行のためのcrontab対応
- 環境変数（.envファイル）によるAPIキー、メールアドレスの管理
- ログ出力

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/ojizou003/newsapi-gmail.git
cd newsapi-gmail
```

### 2. Python環境の準備

`uv` を使用して依存関係をインストールします。

```bash
uv pip sync
```

### 3. APIキーと認証情報の準備

#### 3.1. NewsAPIキーの取得

NewsAPI (https://newsapi.org/) でアカウントを作成し、APIキーを取得してください。

#### 3.2. Google Gemini APIキーの取得

Google AI Studio (https://aistudio.google.com/) でAPIキーを取得してください。

#### 3.3. Gmail API認証情報 (`client_secret.json`) の準備

1.  Google Cloud Console (https://console.cloud.google.com/) にアクセスします。
2.  新しいプロジェクトを作成するか、既存のプロジェクトを選択します。
3.  「APIとサービス」>「ライブラリ」に移動し、「Gmail API」を検索して有効にします。
4.  「APIとサービス」>「認証情報」に移動し、「認証情報を作成」>「OAuth クライアント ID」を選択します。
5.  アプリケーションの種類として「デスクトップアプリ」を選択し、クライアントIDを作成します。
6.  作成後、表示されるクライアントIDとクライアントシークレットを含むJSONファイルをダウンロードし、ファイル名を `client_secret.json` として、このプロジェクトのルートディレクトリに配置してください。
7.  「APIとサービス」>「OAuth同意画面」に移動し、必要に応じて「テストユーザー」に、このアプリケーションを実行するGoogleアカウントを追加してください。

### 4. 環境変数の設定 (`.env`ファイル)

プロジェクトのルートディレクトリに `.env` ファイルを作成し、以下の内容を記述してください。`YOUR_NEWS_API_KEY`, `YOUR_GEMINI_API_KEY`, `YOUR_EMAIL_ADDRESS` はそれぞれ取得したキーとメールアドレスに置き換えてください。

```
NEWS_API_KEY="YOUR_NEWS_API_KEY"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
TO_EMAIL="YOUR_EMAIL_ADDRESS"
```

## 実行方法

### 手動実行

```bash
uv run python main.py
```

初回実行時には、Gmail APIの認証のためブラウザが開き、Googleアカウントでの認証が求められます。認証が完了すると、`token.json`ファイルが生成され、次回以降の実行では認証がスキップされます。

### 自動実行 (crontab)

毎日定時に自動実行するには、`crontab`を設定します。

1.  `uv`コマンドのフルパスを確認します。
    ```bash
    which uv
    ```
2.  `crontab`の編集画面を開きます。
    ```bash
    crontab -e
    ```
3.  以下の行を追加します。`[uvコマンドのフルパス]`と`[ログファイルのフルパス]`は、ご自身の環境に合わせて置き換えてください。

    ```cron
    0 6 * * * /path/to/your/project/.venv/bin/python /path/to/your/project/main.py >> /path/to/your/project/newsapi_app.log 2>&1
    ```
    例:
    ```cron
    0 6 * * * /home/ojizou003/app/newsapi-gmail/.venv/bin/python /home/ojizou003/app/newsapi-gmail/main.py >> /home/ojizou003/app/newsapi-gmail/newsapi_app.log 2>&1
    ```

## ログファイル

アプリケーションの実行ログは、`newsapi_app.log`ファイルに記録されます。

## 開発者

[ojizou003]
