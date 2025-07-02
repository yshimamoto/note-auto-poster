"""
改善されたnote投稿システムの単体テスト
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import tempfile
from pathlib import Path

# テスト対象のモジュールをインポート
from improved_note_poster import (
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
        with patch('improved_note_poster.markdown', side_effect=ImportError):
            processor = MarkdownProcessor()
            html = processor.to_html("# テスト見出し")
            self.assertIn('<h1>テスト見出し</h1>', html)


class TestNoteAuthenticator(unittest.TestCase):
    """認証クラスのテスト"""
    
    def setUp(self):
        self.logger = setup_logging()
        self.authenticator = NoteAuthenticator(self.logger)
    
    @patch('improved_note_poster.webdriver.Chrome')
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
        with patch('improved_note_poster.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = mock_email_input
            
            # Cookieのモックを設定
            mock_driver.get_cookies.return_value = [
                {'name': 'session', 'value': 'test_session_value'},
                {'name': 'csrf', 'value': 'test_csrf_value'}
            ]
            
            # 認証実行
            cookies = self.authenticator.get_cookies('test@example.com', 'password')
            
            # 結果確認
            self.assertIsNotNone(cookies)
            self.assertEqual(cookies['session'], 'test_session_value')
            self.assertEqual(cookies['csrf'], 'test_csrf_value')
            
            # WebDriverの操作確認
            mock_driver.get.assert_called_once_with(Config.NOTE_LOGIN_URL)
            mock_email_input.send_keys.assert_called_once_with('test@example.com')
            mock_password_input.send_keys.assert_called_once_with('password')
            mock_login_button.click.assert_called_once()
            mock_driver.quit.assert_called_once()
    
    @patch('improved_note_poster.webdriver.Chrome')
    def test_authentication_timeout(self, mock_chrome):
        """認証タイムアウトのテスト"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # TimeoutExceptionを発生させる
        with patch('improved_note_poster.WebDriverWait') as mock_wait:
            from selenium.common.exceptions import TimeoutException
            mock_wait.return_value.until.side_effect = TimeoutException()
            
            cookies = self.authenticator.get_cookies('test@example.com', 'password')
            
            self.assertIsNone(cookies)
            mock_driver.quit.assert_called_once()


class TestNotePoster(unittest.TestCase):
    """メイン投稿クラスのテスト"""
    
    def setUp(self):
        self.poster = NotePoster()
        self.test_cookies = {'session': 'test_session', 'csrf': 'test_csrf'}
    
    @patch('improved_note_poster.requests.Session')
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
    
    @patch('improved_note_poster.requests.Session')
    def test_make_request_rate_limit(self, mock_session_class):
        """レート制限のテスト"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        self.poster.session = mock_session
        
        # レート制限レスポンスのモック
        mock_response = Mock()
        mock_response.status_code = 429
        mock_session.request.return_value = mock_response
        
        with patch('improved_note_poster.time.sleep') as mock_sleep:
            response = self.poster._make_request('GET', 'https://example.com')
            
            # レート制限で複数回リトライされることを確認
            self.assertEqual(mock_session.request.call_count, Config.MAX_RETRIES)
            self.assertEqual(mock_sleep.call_count, Config.MAX_RETRIES)
    
    def test_create_article_success(self):
        """記事作成成功のテスト"""
        with patch.object(self.poster, '_make_request') as mock_request:
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
        """存在しないファイルのアップロードテスト"""
        image_key, image_url = self.poster.upload_image(
            'nonexistent_file.png', 
            self.test_cookies
        )
        
        self.assertIsNone(image_key)
        self.assertIsNone(image_url)
    
    def test_upload_image_success(self):
        """画像アップロード成功のテスト"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(b'fake image data')
            temp_path = temp_file.name
        
        try:
            with patch.object(self.poster, '_make_request') as mock_request:
                # 成功レスポンスのモック
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'data': {
                        'key': 'test_image_key',
                        'url': 'https://example.com/image.png'
                    }
                }
                mock_request.return_value = mock_response
                
                image_key, image_url = self.poster.upload_image(temp_path, self.test_cookies)
                
                self.assertEqual(image_key, 'test_image_key')
                self.assertEqual(image_url, 'https://example.com/image.png')
        finally:
            # 一時ファイルを削除
            os.unlink(temp_path)
    
    def test_upload_image_too_large(self):
        """大きすぎるファイルのアップロードテスト"""
        # 大きなファイルのサイズをモック
        with patch('improved_note_poster.Path') as mock_path:
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
    """統合テスト"""
    
    def setUp(self):
        self.poster = NotePoster()
    
    @patch.object(NotePoster, 'update_article_draft')
    @patch.object(NotePoster, 'upload_image')
    @patch.object(NotePoster, 'create_article')
    @patch.object(NoteAuthenticator, 'get_cookies')
    def test_full_posting_flow(self, mock_get_cookies, mock_create_article, 
                              mock_upload_image, mock_update_article):
        """完全な投稿フローのテスト"""
        # モックの設定
        mock_get_cookies.return_value = {'session': 'test_session'}
        mock_create_article.return_value = ('test_id', 'test_key')
        mock_upload_image.return_value = ('img_key', 'img_url')
        mock_update_article.return_value = True
        
        # 投稿実行
        result = self.poster.post_to_note(
            'test@example.com', 
            'password', 
            'テストタイトル', 
            '# テスト内容',
            'test_image.png'
        )
        
        # 結果確認
        self.assertTrue(result)
        
        # 各メソッドが正しく呼ばれたことを確認
        mock_get_cookies.assert_called_once_with('test@example.com', 'password')
        mock_create_article.assert_called_once()
        mock_upload_image.assert_called_once_with('test_image.png', {'session': 'test_session'})
        mock_update_article.assert_called_once()
    
    @patch.object(NoteAuthenticator, 'get_cookies')
    def test_authentication_failure(self, mock_get_cookies):
        """認証失敗時のテスト"""
        # 認証失敗をモック
        mock_get_cookies.return_value = None
        
        result = self.poster.post_to_note(
            'invalid@example.com', 
            'wrong_password', 
            'テストタイトル', 
            '# テスト内容'
        )
        
        self.assertFalse(result)


class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングのテスト"""
    
    def setUp(self):
        self.poster = NotePoster()
    
    def test_json_decode_error(self):
        """JSONデコードエラーのテスト"""
        with patch.object(self.poster, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
            mock_request.return_value = mock_response
            
            article_id, article_key = self.poster.create_article(
                'テストタイトル', 
                '# テスト内容', 
                {'session': 'test'}
            )
            
            self.assertIsNone(article_id)
            self.assertIsNone(article_key)
    
    def test_network_error_handling(self):
        """ネットワークエラーのテスト"""
        with patch.object(self.poster, '_make_request') as mock_request:
            mock_request.return_value = None  # ネットワークエラーをシミュレート
            
            article_id, article_key = self.poster.create_article(
                'テストタイトル', 
                '# テスト内容', 
                {'session': 'test'}
            )
            
            self.assertIsNone(article_id)
            self.assertIsNone(article_key)


class TestPerformance(unittest.TestCase):
    """パフォーマンステスト"""
    
    def test_markdown_processing_performance(self):
        """Markdown処理のパフォーマンステスト"""
        processor = MarkdownProcessor()
        
        # 大きなMarkdownコンテンツを生成
        large_content = "\n".join([
            f"# 見出し{i}\n\nこれは段落{i}です。**太字**と*斜体*を含みます。\n\n- リスト項目1\n- リスト項目2\n"
            for i in range(100)
        ])
        
        import time
        start_time = time.time()
        html = processor.to_html(large_content)
        end_time = time.time()
        
        # 処理時間が合理的な範囲内であることを確認（5秒以内）
        processing_time = end_time - start_time
        self.assertLess(processing_time, 5.0, f"処理時間が長すぎます: {processing_time}秒")
        
        # HTMLが正しく生成されていることを確認
        self.assertIn('<h1>見出し0</h1>', html)
        self.assertIn('<h1>見出し99</h1>', html)
        self.assertIn('<strong>太字</strong>', html)


if __name__ == '__main__':
    # テストスイートの実行
    unittest.main(verbosity=2)
