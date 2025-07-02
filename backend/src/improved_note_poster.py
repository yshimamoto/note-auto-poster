"""
改善されたnote投稿システム - セキュリティとエラーハンドリングを強化
"""

import os
import json
import time
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# 設定クラス
class Config:
    """設定値を管理するクラス"""
    TIMEOUT = 10
    WAIT_TIME = 2
    MAX_RETRIES = 3
    
    NOTE_LOGIN_URL = "https://note.com/login"
    NOTE_API_BASE = "https://note.com/api/v1"
    
    CHROME_OPTIONS = [
        '--headless',
        '--no-sandbox', 
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080'
    ]
    
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


# ログ設定
def setup_logging(level: str = "INFO"):
    """構造化ログの設定"""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('note_poster.log')
        ]
    )
    return logging.getLogger(__name__)


# 認証管理クラス
class NoteAuthenticator:
    """Note認証を管理するクラス"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.cookies: Optional[Dict[str, str]] = None
    
    def get_cookies(self, email: str, password: str) -> Optional[Dict[str, str]]:
        """安全にCookieを取得"""
        driver = None
        try:
            # WebDriverオプション設定
            chrome_options = Options()
            for option in Config.CHROME_OPTIONS:
                chrome_options.add_argument(option)
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(Config.TIMEOUT)
            
            # ログインページアクセス
            self.logger.info("ログインページにアクセス中...")
            driver.get(Config.NOTE_LOGIN_URL)
            
            # メールアドレス入力
            email_input = WebDriverWait(driver, Config.TIMEOUT).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_input.clear()
            email_input.send_keys(email)
            
            # パスワード入力
            password_input = driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(password)
            
            # ログインボタンクリック
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # ログイン完了を動的に待機
            WebDriverWait(driver, Config.TIMEOUT).until(
                EC.url_contains('note.com')
            )
            
            # Cookie取得
            cookies = driver.get_cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            self.cookies = cookie_dict
            self.logger.info("認証成功 - Cookie取得完了")
            return cookie_dict
            
        except TimeoutException:
            self.logger.error("ログインタイムアウト - 認証情報を確認してください")
            return None
        except WebDriverException as e:
            self.logger.error(f"WebDriverエラー: {e}")
            return None
        except Exception as e:
            self.logger.error(f"予期しないログインエラー: {e}")
            return None
        finally:
            if driver:
                driver.quit()


# HTML変換クラス
class MarkdownProcessor:
    """Markdown処理を担当するクラス"""
    
    def __init__(self):
        # markdownライブラリがない場合の簡易実装
        pass
    
    def to_html(self, markdown_text: str) -> str:
        """MarkdownをHTMLに変換（改善版）"""
        try:
            # markdownライブラリがある場合
            import markdown
            return markdown.markdown(
                markdown_text, 
                extensions=['tables', 'fenced_code', 'nl2br']
            )
        except ImportError:
            # フォールバック実装
            return self._simple_markdown_to_html(markdown_text)
    
    def _simple_markdown_to_html(self, text: str) -> str:
        """簡易Markdown→HTML変換"""
        import re
        
        html = text
        
        # コードブロック（先に処理）
        html = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # 見出し
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)  
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # リスト
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # 強調
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # リンク
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
        # 段落処理（改善版）
        paragraphs = []
        for para in html.split('\n\n'):
            para = para.strip()
            if para and not para.startswith('<'):
                para = f'<p>{para}</p>'
            if para:
                paragraphs.append(para)
        
        return '\n'.join(paragraphs)


# メインのNote投稿クラス
class NotePoster:
    """改善されたNote投稿クラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or setup_logging()
        self.authenticator = NoteAuthenticator(self.logger)
        self.markdown_processor = MarkdownProcessor()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """リトライ機能付きHTTPリクエスト"""
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.session.request(method, url, timeout=Config.TIMEOUT, **kwargs)
                
                if response.status_code == 429:  # レート制限
                    wait_time = Config.WAIT_TIME * (attempt + 1)
                    self.logger.warning(f"レート制限 - {wait_time}秒待機中...")
                    time.sleep(wait_time)
                    continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"リクエスト失敗 (試行 {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.WAIT_TIME)
                    
        return None
    
    def create_article(self, title: str, markdown_content: str, cookies: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """記事作成（エラーハンドリング強化版）"""
        if not cookies:
            self.logger.error("認証Cookie情報が必要です")
            return None, None
        
        html_content = self.markdown_processor.to_html(markdown_content)
        
        data = {
            'body': html_content,
            'name': title,
            'template_key': None,
        }
        
        response = self._make_request(
            'POST', 
            f"{Config.NOTE_API_BASE}/text_notes",
            cookies=cookies,
            json=data
        )
        
        if not response:
            self.logger.error("記事作成リクエストが失敗しました")
            return None, None
            
        if response.status_code == 200:
            try:
                result = response.json()
                article_id = result['data']['id']
                article_key = result['data']['key']
                self.logger.info(f"記事作成成功 - ID: {article_id}")
                return article_id, article_key
            except (KeyError, json.JSONDecodeError) as e:
                self.logger.error(f"レスポンス解析エラー: {e}")
                return None, None
        else:
            self.logger.error(f"記事作成失敗 - ステータス: {response.status_code}, レスポンス: {response.text}")
            return None, None
    
    def upload_image(self, image_path: str, cookies: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """画像アップロード（エラーハンドリング強化版）"""
        if not cookies:
            self.logger.error("認証Cookie情報が必要です")
            return None, None
        
        # ファイル存在確認
        if not Path(image_path).exists():
            self.logger.error(f"画像ファイルが見つかりません: {image_path}")
            return None, None
        
        # ファイルサイズ確認（10MB制限）
        file_size = Path(image_path).stat().st_size
        if file_size > 10 * 1024 * 1024:
            self.logger.error(f"ファイルサイズが大きすぎます: {file_size / 1024 / 1024:.1f}MB")
            return None, None
        
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                # Content-Typeヘッダーを削除してmultipart/form-dataを使用
                headers = {'User-Agent': Config.USER_AGENT}
                
                response = self._make_request(
                    'POST',
                    f"{Config.NOTE_API_BASE}/upload_image",
                    cookies=cookies,
                    headers=headers,
                    files=files
                )
            
            if not response:
                return None, None
                
            if response.status_code == 200:
                try:
                    result = response.json()
                    image_key = result['data']['key']
                    image_url = result['data']['url']
                    self.logger.info(f"画像アップロード成功 - KEY: {image_key}")
                    return image_key, image_url
                except (KeyError, json.JSONDecodeError) as e:
                    self.logger.error(f"画像アップロードレスポンス解析エラー: {e}")
                    return None, None
            else:
                self.logger.error(f"画像アップロード失敗 - ステータス: {response.status_code}")
                return None, None
                
        except IOError as e:
            self.logger.error(f"ファイル読み込みエラー: {e}")
            return None, None
    
    def update_article_draft(self, article_id: str, title: str, markdown_content: str, 
                           cookies: Dict[str, str], image_key: Optional[str] = None) -> bool:
        """記事更新（下書き保存）"""
        if not cookies:
            self.logger.error("認証Cookie情報が必要です")
            return False
        
        html_content = self.markdown_processor.to_html(markdown_content)
        
        data = {
            'body': html_content,
            'name': title,
            'status': 'draft',
        }
        
        if image_key:
            data['eyecatch_image_key'] = image_key
        
        response = self._make_request(
            'PUT',
            f"{Config.NOTE_API_BASE}/text_notes/{article_id}",
            cookies=cookies,
            json=data
        )
        
        if not response:
            return False
            
        if response.status_code == 200:
            self.logger.info("記事の下書き保存成功")
            return True
        else:
            self.logger.error(f"記事更新失敗 - ステータス: {response.status_code}")
            return False
    
    def post_to_note(self, email: str, password: str, title: str, 
                    markdown_content: str, image_path: Optional[str] = None) -> bool:
        """メイン投稿関数（改善版）"""
        try:
            # 認証
            self.logger.info("認証処理開始...")
            cookies = self.authenticator.get_cookies(email, password)
            if not cookies:
                return False
            
            # 記事作成
            self.logger.info("記事作成中...")
            article_id, article_key = self.create_article(title, markdown_content, cookies)
            if not article_id:
                return False
            
            # 画像アップロード（オプション）
            image_key = None
            if image_path:
                self.logger.info("画像アップロード中...")
                image_key, _ = self.upload_image(image_path, cookies)
            
            # 記事更新（下書き保存）
            self.logger.info("記事を下書き保存中...")
            success = self.update_article_draft(
                article_id, title, markdown_content, cookies, image_key
            )
            
            if success:
                self.logger.info("✅ 投稿完了!")
                self.logger.info(f"記事URL: https://note.com/your_username/n/{article_key}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"投稿処理でエラーが発生: {e}")
            return False


def main():
    """使用例（環境変数対応版）"""
    # 環境変数から認証情報を取得
    email = os.getenv('NOTE_EMAIL')
    password = os.getenv('NOTE_PASSWORD')
    
    if not email or not password:
        print("ERROR: NOTE_EMAIL と NOTE_PASSWORD 環境変数を設定してください")
        print("例: export NOTE_EMAIL=your-email@example.com")
        print("例: export NOTE_PASSWORD=your-password")
        return
    
    # 記事内容
    title = "改良されたPython自動投稿システム"
    content = """
# はじめに
このシステムは安全性とエラーハンドリングを強化しました。

## 改善点
- **セキュリティ強化**: Headlessモード、適切な待機条件
- **エラーハンドリング**: 詳細なエラー情報、リトライ機能
- **ログ管理**: 構造化ログ、ファイル出力
- **型安全性**: 型ヒント追加

## 使用方法
環境変数を設定してから実行してください：

```bash
export NOTE_EMAIL=your-email@example.com
export NOTE_PASSWORD=your-password
python improved_note_poster.py
```

## まとめ
プロダクションレベルでの使用により適したシステムに改善されました。
"""
    
    # 投稿実行
    poster = NotePoster()
    success = poster.post_to_note(email, password, title, content)
    
    if success:
        print("✨ 記事の投稿が正常に完了しました！")
    else:
        print("❌ 記事の投稿に失敗しました。ログを確認してください。")


if __name__ == "__main__":
    main()
