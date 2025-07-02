"""
note非公式API記事自動投稿システム
Markdown形式の記事と画像を自動で下書き保存
"""

import requests
import json
import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotePoster:
    def __init__(self):
        self.cookies = None
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def get_cookies(self, email, password):
        """noteにログインしてCookieを取得"""
        driver = webdriver.Chrome()
        try:
            # ログインページにアクセス
            driver.get('https://note.com/login')
            
            # メールアドレスとパスワードを入力
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_input.send_keys(email)
            
            password_input = driver.find_element(By.NAME, "password")
            password_input.send_keys(password)
            
            # ログインボタンをクリック
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # ログイン完了を待つ
            time.sleep(5)
            
            # Cookieを取得
            cookies = driver.get_cookies()
            
            # Cookie辞書に変換
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            self.cookies = cookie_dict
            logger.info("Cookie取得成功")
            return cookie_dict
        
        except Exception as e:
            logger.error(f"Cookie取得エラー: {e}")
            return None
        finally:
            driver.quit()
    
    def markdown_to_html(self, markdown_text):
        """簡易的なMarkdown→HTML変換"""
        html = markdown_text
        
        # 見出し
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # リスト
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # 強調
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # コードブロック
        html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # 段落
        paragraphs = html.split('\n\n')
        html = '\n'.join([f'<p>{p}</p>' if not p.startswith('<') else p for p in paragraphs])
        
        return html
    
    def create_article(self, title, markdown_content):
        """新しい記事を作成"""
        if not self.cookies:
            logger.error("Cookie情報が必要です")
            return None, None
        
        # MarkdownをHTMLに変換
        html_content = self.markdown_to_html(markdown_content)
        
        data = {
            'body': html_content,
            'name': title,
            'template_key': None,
        }
        
        try:
            response = requests.post(
                'https://note.com/api/v1/text_notes',
                cookies=self.cookies,
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                article_id = result['data']['id']
                article_key = result['data']['key']
                logger.info(f"記事作成成功！ID: {article_id}")
                return article_id, article_key
            else:
                logger.error(f"記事作成失敗: {response.status_code}")
                return None, None
        
        except Exception as e:
            logger.error(f"記事作成エラー: {e}")
            return None, None
    
    def upload_image(self, image_path):
        """画像をアップロード"""
        if not self.cookies:
            logger.error("Cookie情報が必要です")
            return None, None
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    'https://note.com/api/v1/upload_image',
                    cookies=self.cookies,
                    headers=headers,
                    files=files
                )
            
            if response.status_code == 200:
                result = response.json()
                image_key = result['data']['key']
                image_url = result['data']['url']
                logger.info(f"画像アップロード成功！KEY: {image_key}")
                return image_key, image_url
            else:
                logger.error(f"画像アップロード失敗: {response.status_code}")
                return None, None
        
        except Exception as e:
            logger.error(f"画像アップロードエラー: {e}")
            return None, None
    
    def update_article_draft(self, article_id, title, markdown_content, image_key=None):
        """記事を更新して下書きとして保存"""
        if not self.cookies:
            logger.error("Cookie情報が必要です")
            return False
        
        html_content = self.markdown_to_html(markdown_content)
        
        data = {
            'body': html_content,
            'name': title,
            'status': 'draft',  # 下書きとして保存
        }
        
        # アイキャッチ画像がある場合は追加
        if image_key:
            data['eyecatch_image_key'] = image_key
        
        try:
            response = requests.put(
                f'https://note.com/api/v1/text_notes/{article_id}',
                cookies=self.cookies,
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                logger.info("記事の下書き保存成功！")
                return True
            else:
                logger.error(f"記事の更新失敗: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"記事更新エラー: {e}")
            return False
    
    def rate_limited_request(self, func, *args, **kwargs):
        """レート制限を考慮したリクエスト"""
        time.sleep(2)  # 2秒待機
        return func(*args, **kwargs)
    
    def post_to_note(self, email, password, title, markdown_content, image_path=None):
        """noteに記事を投稿する完全な関数"""
        try:
            logger.info("1. noteにログイン中...")
            cookies = self.get_cookies(email, password)
            if not cookies:
                return False
            
            logger.info("2. 記事を作成中...")
            article_id, article_key = self.create_article(title, markdown_content)
            if not article_id:
                return False
            
            image_key = None
            if image_path:
                logger.info("3. 画像をアップロード中...")
                image_key, image_url = self.upload_image(image_path)
            
            logger.info("4. 記事を下書き保存中...")
            success = self.update_article_draft(
                article_id,
                title,
                markdown_content,
                image_key
            )
            
            if success:
                logger.info(f"\n✅ 投稿完了！")
                logger.info(f"記事URL: https://note.com/your_username/n/{article_key}")
                return True
            
            return False
        
        except requests.exceptions.RequestException as e:
            logger.error(f"ネットワークエラー: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSONパースエラー: {e}")
        except Exception as e:
            logger.error(f"予期せぬエラー: {e}")
        
        return False


def main():
    """使用例"""
    # 設定（環境変数から取得することを推奨）
    EMAIL = "your-email@example.com"
    PASSWORD = "your-password"
    
    # 記事内容
    TITLE = "Pythonで自動投稿テスト"
    CONTENT = """
# はじめに
これは自動投稿のテストです。

## 特徴
- Markdown形式で書ける
- 画像も自動アップロード
- 下書きとして保存

## まとめ
便利ですね！
"""
    IMAGE_PATH = "thumbnail.png"  # オプション
    
    # 投稿実行
    poster = NotePoster()
    poster.post_to_note(EMAIL, PASSWORD, TITLE, CONTENT, IMAGE_PATH)


if __name__ == "__main__":
    main()
