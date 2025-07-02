"""
改善されたnote投稿システムの単体テスト
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import tempfile
from pathlib import Path
import logging
import builtins

# テスト対象のモジュールをインポート
from src.improved_note_poster import (
    Config, 
    NoteAuthenticator, 
    MarkdownProcessor, 
    NotePoster,
    setup_logging
)


class TestConfig(unittest.TestCase):
    """設定クラスのテスト"""
    
    def test_constants(self):
        """定数の値をテスト"""
        self.assertEqual(Config.TIMEOUT, 10)
        self.assertEqual(Config.WAIT_TIME, 2)
        self.assertEqual(Config.MAX_RETRIES, 3)
        self.assertTrue(Config.NOTE_LOGIN_URL.startswith('https://'))
        self.assertTrue(Config.NOTE_API_BASE.startswith('https://'))


class TestMarkdownProcessor(unittest.TestCase):
    """Markdown処理クラスのテスト"""
    
    def setUp(self):
        self.processor = MarkdownProcessor()
    
    def test_simple_markdown_to_html(self):
        """基本的なMarkdown→HTML変換のテスト"""
        markdown = """# 見出し1
## 見出し2
### 見出し3

これは段落です。

- リスト項目1
- リスト項目2

**太字**と*斜体*のテスト

`インラインコード`のテスト

```python
print("Hello, World!")
```

[リンク](https://example.com)のテスト
"""
        
        html = self.processor._simple_markdown_to_html(markdown)
        
        # 見出しの変換確認
        self.assertIn('<h1>見出し1</h1>', html)
        self.assertIn('<h2>見出し2</h2>', html)
        self.assertIn('<h3>見出し3</h3>', html)
        
        # リストの変換確認
        self.assertIn('<li>リスト項目1</li>', html)
        self.assertIn('<li>リスト項目2</li>', html)
        
        # 強調の変換確認
        self.assertIn('<strong>太字</strong>', html)
        self.assertIn('<em>斜体</em>', html)
        
        # コードの変換確認
        self.assertIn('<code>インラインコード</code>', html)
        self.assertIn('<pre><code>', html)
        
        # リンクの変換確認
        self.assertIn('<a href="https://example.com">リンク</a>', html)
    
    def test_empty_content(self):
        """空コンテンツのテスト"""
        html = self.processor.to_html("")
        self.assertEqual(html, "")
    
    def test_fallback_implementation(self):
        """markdownライブラリがない場合のフォールバック実装テスト"""
        # markdownライブラリのインポートを失敗させる
        original_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == 'markdown':
                raise ImportError("Mocked import error")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            processor = MarkdownProcessor()
            markdown_text = "# Title\n\n- list"
            html = processor.to_html(markdown_text)
            self.assertIn("<h1>Title</h1>", html)
            self.assertIn("<li>list</li>", html)


class TestNoteAuthenticator(unittest.TestCase):
    """認証クラスのテスト"""
    
    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self.authenticator = NoteAuthenticator(self.logger)
        self.email = 'test@example.com'
        self.password = 'password'
    
    @patch('src.improved_note_poster.webdriver.Chrome')
    def test_successful_authentication(self, mock_chrome):
        """正常な認証のテスト"""
        # WebDriverのモックを設定
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # 要素のモックを設定
        mock_email_input = Mock()
        mock_password_input = Mock()
        mock_login_button = Mock()
        
        mock_driver.find_element.side_effect = [mock_password_input, mock_login_button]
        
        # WebDriverWaitのモックを設定
        with patch('src.improved_note_poster.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = mock_email_input
            
            # Cookieのモックを設定
            mock_driver.get_cookies.return_value = [
                {'name': 'session', 'value': 'test_session_value'},
                {'name': 'csrf', 'value': 'test_csrf_value'}
            ]
            
            # 認証実行
            cookies = self.authenticator.get_cookies(self.email, self.password)
            
            # 結果確認
            self.assertIsNotNone(cookies)
            self.assertEqual(cookies['session'], 'test_session_value')
            self.assertEqual(cookies['csrf'], 'test_csrf_value')
            
            # WebDriverの操作確認
            mock_driver.get.assert_called_once_with(Config.NOTE_LOGIN_URL)
            mock_email_input.send_keys.assert_called_once_with(self.email)
            mock_password_input.send_keys.assert_called_once_with(self.password)
            mock_login_button.click.assert_called_once()
            mock_driver.quit.assert_called_once()
    
    @patch('src.improved_note_poster.webdriver.Chrome')
    def test_authentication_timeout(self, mock_chrome):
        """認証タイムアウトのテスト"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # TimeoutExceptionを発生させる
        with patch('src.improved_note_poster.WebDriverWait') as mock_wait:
            from selenium.common.exceptions import TimeoutException
            mock_wait.return_value.until.side_effect = TimeoutException()
            
            cookies = self.authenticator.get_cookies(self.email, self.password)
            
            self.assertIsNone(cookies)
            mock_driver.quit.assert_called_once()


class TestNotePoster(unittest.TestCase):
    """メイン投稿クラスのテスト"""
    
    def setUp(self):
        self.poster = NotePoster()
        self.test_cookies = {'session': 'test_session', 'csrf': 'test_csrf'}
    
    @patch('src.improved_note_poster.requests.Session')
    def test_make_request_success(self, mock_session_class):
        """HTTPリクエスト成功のテスト"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        self.poster.session = mock_session
        
        # 成功レスポンスのモック
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        
        response = self.poster._make_request('GET', 'https://example.com')
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
    
    @patch('src.improved_note_poster.requests.Session')
    def test_make_request_rate_limit(self, mock_session_class):
        """レート制限のテスト"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        self.poster.session = mock_session
        
        # レート制限レスポンスのモック
        mock_response = Mock()
        mock_response.status_code = 429
        mock_session.request.return_value = mock_response
        
        with patch('src.improved_note_poster.time.sleep') as mock_sleep:
            response = self.poster._make_request('GET', 'https://example.com')
            
            # レート制限で複数回リトライされることを確認
            self.assertEqual(mock_session.request.call_count, Config.MAX_RETRIES)
            self.assertEqual(mock_sleep.call_count, Config.MAX_RETRIES)
    
    @patch('src.improved_note_poster.requests.Session.request')
    def test_create_article_success(self, mock_request):
        """記事作成成功のテスト"""
        # 成功レスポンスのモック
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'id': 'test_article_id',
                'key': 'test_article_key'
            }
        }
        mock_request.return_value = mock_response
        
        article_id, article_key = self.poster.create_article(
            'テストタイトル', 
            '# テスト内容', 
            self.test_cookies
        )
        
        self.assertEqual(article_id, 'test_article_id')
        self.assertEqual(article_key, 'test_article_key')
    
    def test_create_article_no_cookies(self):
        """Cookie なしでの記事作成のテスト"""
        article_id, article_key = self.poster.create_article(
            'テストタイトル', 
            '# テスト内容', 
            {}
        )
        
        self.assertIsNone(article_id)
        self.assertIsNone(article_key)
    
    def test_upload_image_file_not_found(self):
        """画像ファイルが見つからない場合のテスト"""
        with patch('src.improved_note_poster.Path.exists', return_value=False):
            image_key, image_url = self.poster.upload_image(
                'non_existent_file.png', 
                self.test_cookies
            )
            
            self.assertIsNone(image_key)
            self.assertIsNone(image_url)

    @patch('src.improved_note_poster.requests.Session.request')
    def test_upload_image_success(self, mock_request):
        """画像アップロード成功のテスト"""
        # 成功レスポンスのモック
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'id': 'test_image_id',
                'key': 'test_image_key',
                'url': 'https://example.com/image.png'
            }
        }
        mock_request.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            temp_path = temp.name
        
        try:
            with patch('src.improved_note_poster.Path.open'), \
                 patch('src.improved_note_poster.Path.exists', return_value=True), \
                 patch('src.improved_note_poster.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 1000 # 1KB
                
                image_key, image_url = self.poster.upload_image(
                    temp_path, 
                    self.test_cookies
                )
                
                self.assertEqual(image_key, 'test_image_key')
                self.assertEqual(image_url, 'https://example.com/image.png')
        finally:
            os.unlink(temp_path)
    
    @patch('src.improved_note_poster.Path')
    def test_upload_image_too_large(self, mock_path):
        """大きすぎるファイルのアップロードテスト"""
        # 大きなファイルのサイズをモック
        mock_stat = Mock()
        mock_stat.st_size = 11 * 1024 * 1024  # 11MB
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.stat.return_value = mock_stat
        
        image_key, image_url = self.poster.upload_image(
            'large_file.png', 
            self.test_cookies
        )
        
        self.assertIsNone(image_key)
        self.assertIsNone(image_url)


class TestIntegration(unittest.TestCase):
    """結合テスト"""

    def setUp(self):
        self.poster = NotePoster()
        self.email = 'test@example.com'
        self.password = 'test_password'
        self.title = 'Test Title'
        self.content = '# Test Content'
        self.image_path = 'test_image.png'
    
    @patch.object(NotePoster, 'update_article_draft')
    @patch.object(NotePoster, 'upload_image')
    @patch.object(NotePoster, 'create_article')
    @patch.object(NoteAuthenticator, 'get_cookies')
    def test_full_posting_flow(self, mock_get_cookies, mock_create_article, 
                              mock_upload_image, mock_update_article):
        """画像付き投稿の全体フローテスト"""
        # モックの戻り値を設定
        mock_get_cookies.return_value = {'session': 'dummy_session'}
        mock_create_article.return_value = ('article_123', 'key_123')
        mock_upload_image.return_value = ('image_key_456', 'image_url_456')
        mock_update_article.return_value = True
        
        # 実行
        success = self.poster.post_to_note(
            self.email, self.password, self.title, self.content, self.image_path
        )
        
        # 検証
        self.assertTrue(success)
        mock_get_cookies.assert_called_once_with(self.email, self.password)
        mock_create_article.assert_called_once()
        mock_upload_image.assert_called_once_with(self.image_path, {'session': 'dummy_session'})
        mock_update_article.assert_called_once()

    @patch.object(NoteAuthenticator, 'get_cookies')
    def test_authentication_failure(self, mock_get_cookies):
        """認証失敗時のフローテスト"""
        # 認証失敗をモック
        mock_get_cookies.return_value = None
        
        # 実行
        success = self.poster.post_to_note(
            self.email, self.password, self.title, self.content
        )
        
        # 検証
        self.assertFalse(success)


class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングのテスト"""

    def setUp(self):
        self.poster = NotePoster()

    @patch('src.improved_note_poster.NotePoster._make_request')
    def test_json_decode_error(self, mock_request):
        """JSONデコードエラーのテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        # 不正なJSONを返すように設定
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_request.return_value = mock_response

        article_id, article_key = self.poster.create_article(
            "title", "content", {"cookie": "test"}
        )
        self.assertIsNone(article_id)
        self.assertIsNone(article_key)

    @patch('src.improved_note_poster.NoteAuthenticator.get_cookies', return_value=None)
    def test_network_error_handling(self, mock_get_cookies):
        """ネットワークエラーのテスト"""
        success = self.poster.post_to_note(
            "email", "password", "title", "content"
        )
        # 認証の段階で失敗するのでFalseになる
        self.assertFalse(success)


class TestPerformance(unittest.TestCase):
    """パフォーマンスに関するテスト"""

    def test_markdown_processing_performance(self):
        """Markdown処理のパフォーマンス"""
        processor = MarkdownProcessor()
        long_markdown = "# Test\n" * 1000
        
        import time
        start_time = time.time()
        processor.to_html(long_markdown)
        end_time = time.time()
        
        # 非常に緩い基準だが、極端に遅くないことを確認
        self.assertLess(end_time - start_time, 1.0)

if __name__ == '__main__':
    unittest.main()
