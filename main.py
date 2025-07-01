import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime
from dotenv import load_dotenv
import logging

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("newsapi_app.log"),
        logging.StreamHandler()
    ]
)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY is not set.")
    # ここではエラーを発生させず、後続の処理でチェックする
genai.configure(api_key=GEMINI_API_KEY)

# --- 設定項目 ---
# RDD 2.3.2: 送信元/送信先メールアドレス
# .envファイルから読み込む
TO_EMAIL = os.environ.get("TO_EMAIL")
# ----------------

# Gmail APIのスコープ
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def get_ai_news():
    """
    NewsAPIからAI関連のニュースを取得する
    """
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        logging.error("NEWS_API_KEY is not set.")
        raise ValueError("NEWS_API_KEY is not set.")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": '"AI" OR "人工知能" OR "機械学習"',
        "sortBy": "publishedAt",
        "pageSize": 5,
        "language": "jp",
        "apiKey": api_key
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        logging.info("NewsAPIからニュースを正常に取得しました。")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"NewsAPIからのニュース取得に失敗しました: {e}")
        raise

def get_article_text(url):
    """
    URLから記事の本文を取得する
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        article_text = '\n'.join([p.get_text() for p in paragraphs])
        logging.info(f"記事の本文を正常に取得しました: {url}")
        return article_text
    except requests.exceptions.RequestException as e:
        logging.error(f"記事の取得に失敗しました: {url}, Error: {e}")
        return None

def summarize_text_with_gemini(text):
    """
    Gemini APIを使ってテキストを日本語で要約する
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY is not set.")
        raise ValueError("GEMINI_API_KEY is not set.")
    
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = f"以下のニュース記事を日本語で200字程度に要約してください。\n\n---\n{text}\n---"
    
    try:
        response = model.generate_content(prompt)
        logging.info("Geminiで要約を正常に生成しました。")
        return response.text
    except Exception as e:
        logging.error(f"Geminiでの要約に失敗しました: {e}")
        return None

def create_message(to, subject, message_text):
    """
    メールメッセージを作成する
    """
    message = MIMEText(message_text)
    message["to"] = to
    message["subject"] = subject
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_message(service, user_id, message):
    """
    メールを送信する
    """
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        logging.info(f"メールを正常に送信しました。Message Id: {message['id']}")
        return message
    except HttpError as error:
        logging.error(f"メール送信中にエラーが発生しました: {error}")
        raise

def get_gmail_service():
    """
    Gmail APIのサービスオブジェクトを取得する
    """
    creds = None
    if os.path.exists(os.path.join(os.path.dirname(__file__), "token.json")):
        creds = Credentials.from_authorized_user_file(os.path.join(os.path.dirname(__file__), "token.json"), SCOPES)
        logging.info("既存のtoken.jsonから認証情報を読み込みました。")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logging.info("認証情報をリフレッシュしました。")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(os.path.join(os.path.dirname(__file__), "client_secret.json"), SCOPES)
            creds = flow.run_local_server(port=0)
            logging.info("新しい認証情報を取得しました。")
        with open(os.path.join(os.path.dirname(__file__), "token.json"), "w") as token:
            token.write(creds.to_json())
            logging.info("認証情報をtoken.jsonに保存しました。")
    return build("gmail", "v1", credentials=creds)

if __name__ == "__main__":
    try:
        logging.info("AIニュース自動要約＆メール送信アプリを開始します。")
        
        if not TO_EMAIL:
            logging.error("TO_EMAILが.envファイルに設定されていません。処理を終了します。")
            exit()

        news = get_ai_news()
        articles = news.get("articles", [])
        
        if not articles:
            logging.info("ニュース記事が見つかりませんでした。処理を終了します。")
            exit()

        email_body = ""
        for article in articles:
            title = article.get('title', '（タイトル不明）')
            url = article.get('url', '（URL不明）')
            logging.info(f"処理中の記事: {title}")

            article_text = get_article_text(url)
            summary = "（要約の生成に失敗しました）"
            if article_text and article_text.strip():
                logging.info("要約を生成中...")
                summary = summarize_text_with_gemini(article_text) or summary
            else:
                logging.warning("記事の本文を取得できなかったため、要約をスキップします。")

            email_body += f"■ 記事タイトル\n{title}\n\n"
            email_body += f"■ 日本語要約\n{summary}\n\n"
            email_body += f"■ 元記事へのURL\n{url}\n\n"
            email_body += "-" * 30 + "\n\n"

        if email_body:
            logging.info("メールの送信準備をしています...")
            service = get_gmail_service()
            today = datetime.date.today().strftime("%Y-%m-%d")
            subject = f"【自動配信】本日のAIニュース ({today})"
            message = create_message(TO_EMAIL, subject, email_body)
            
            logging.info(f"{TO_EMAIL} 宛にメールを送信します...")
            send_message(service, "me", message)
            logging.info("メールの送信が完了しました。")
        else:
            logging.info("送信するニュースがありませんでした。")

    except (ValueError, requests.exceptions.RequestException, HttpError) as e:
        logging.error(f"アプリケーション実行中にエラーが発生しました: {e}", exc_info=True)
    except Exception as e:
        logging.critical(f"予期せぬ致命的なエラーが発生しました: {e}", exc_info=True)
    finally:
        logging.info("AIニュース自動要約＆メール送信アプリを終了します。")