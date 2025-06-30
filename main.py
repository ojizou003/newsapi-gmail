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

load_dotenv()

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
        raise ValueError("NEWS_API_KEY is not set.")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": '"AI" OR "人工知能" OR "機械学習"',
        "sortBy": "publishedAt",
        "pageSize": 5,
        "language": "jp",
        "apiKey": api_key
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

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
        return article_text
    except requests.exceptions.RequestException as e:
        print(f"記事の取得に失敗しました: {url}, Error: {e}")
        return None

def summarize_text_with_gemini(text):
    """
    Gemini APIを使ってテキストを日本語で要約する
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = f"以下のニュース記事を日本語で200字程度に要約してください。\n\n---\n{text}\n---"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Geminiでの要約に失敗しました: {e}")
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
        print(f"Message Id: {message['id']}")
        return message
    except HttpError as error:
        print(f"An error occurred: {error}")

def get_gmail_service():
    """
    Gmail APIのサービスオブジェクトを取得する
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

if __name__ == "__main__":
    try:
        print("AIニュースの取得を開始します...")
        news = get_ai_news()
        articles = news.get("articles", [])
        
        if not articles:
            print("ニュース記事が見つかりませんでした。")
            exit()

        email_body = ""
        for article in articles:
            title = article.get('title', '（タイトル不明）')
            url = article.get('url', '（URL不明）')
            print(f"\n処理中の記事: {title}")

            article_text = get_article_text(url)
            summary = "（要約の生成に失敗しました）"
            if article_text and article_text.strip():
                print("要約を生成中...")
                summary = summarize_text_with_gemini(article_text) or summary
            else:
                print("記事の本文を取得できなかったため、要約をスキップします。")

            email_body += f"■ 記事タイトル\n{title}\n\n"
            email_body += f"■ 日本語要約\n{summary}\n\n"
            email_body += f"■ 元記事へのURL\n{url}\n\n"
            email_body += "-" * 30 + "\n\n"

        if email_body:
            print("メールの送信準備をしています...")
            service = get_gmail_service()
            today = datetime.date.today().strftime("%Y-%m-%d")
            subject = f"【自動配信】本日のAIニュース ({today})"
            message = create_message(TO_EMAIL, subject, email_body)
            
            print(f"{TO_EMAIL} 宛にメールを送信します...")
            send_message(service, "me", message)
            print("メールの送信が完了しました。")
        else:
            print("送信するニュースがありませんでした。")

    except (ValueError, requests.exceptions.RequestException, HttpError) as e:
        print(f"エラーが発生しました: {e}")