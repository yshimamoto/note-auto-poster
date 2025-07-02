"""
note自動投稿システムの拡張機能
定期投稿、複数プラットフォーム対応、GitHubからの自動投稿など
"""

import schedule
import time
from datetime import datetime
import requests
import os
from note_poster import NotePoster


class NoteScheduler:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.poster = NotePoster()
    
    def daily_post(self):
        """毎日記事を投稿"""
        today = datetime.now().strftime("%Y年%m月%d日")
        title = f"{today}の技術メモ"
        content = self.get_daily_content()  # 日次コンテンツを生成
        
        self.poster.post_to_note(self.email, self.password, title, content)
    
    def get_daily_content(self):
        """日次コンテンツを生成（サンプル実装）"""
        today = datetime.now().strftime("%Y年%m月%d日")
        return f"""
# {today}の技術メモ

## 今日学んだこと
- Python
- note API
- 自動化

## 明日の目標
- さらなる改善を続ける

## まとめ
継続的な学習が重要です。
"""
    
    def schedule_daily_posts(self, time_str="09:00"):
        """毎日指定時刻に記事を投稿するスケジュール設定"""
        schedule.every().day.at(time_str).do(self.daily_post)
        
        print(f"毎日{time_str}に記事投稿をスケジュールしました")
        
        # スケジュール実行ループ
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分間隔でチェック


class CrossPlatformPoster:
    def __init__(self, note_email, note_password):
        self.note_email = note_email
        self.note_password = note_password
        self.note_poster = NotePoster()
    
    def post_to_note(self, title, content, image_path=None):
        """noteに投稿"""
        return self.note_poster.post_to_note(
            self.note_email, 
            self.note_password, 
            title, 
            content, 
            image_path
        )
    
    def post_to_qiita(self, title, content):
        """Qiitaに投稿（仮実装）"""
        # TODO: Qiita APIの実装
        print(f"Qiitaに投稿: {title}")
        return True
    
    def post_to_zenn(self, title, content):
        """Zennに投稿（仮実装）"""
        # TODO: Zenn APIの実装
        print(f"Zennに投稿: {title}")
        return True
    
    def cross_post(self, title, content, image_path=None):
        """複数プラットフォームに同時投稿"""
        results = {}
        
        # noteに投稿
        results['note'] = self.post_to_note(title, content, image_path)
        
        # 他のプラットフォームにも投稿
        results['qiita'] = self.post_to_qiita(title, content)
        results['zenn'] = self.post_to_zenn(title, content)
        
        return results


class GitHubPoster:
    def __init__(self, note_email, note_password):
        self.note_email = note_email
        self.note_password = note_password
        self.note_poster = NotePoster()
    
    def fetch_github_content(self, repo_url, file_path):
        """GitHubからMarkdownファイルを取得"""
        # GitHub APIを使用してファイル内容を取得
        api_url = repo_url.replace('github.com', 'api.github.com/repos')
        api_url = f"{api_url}/contents/{file_path}"
        
        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                # Base64デコード
                import base64
                content = base64.b64decode(data['content']).decode('utf-8')
                return content
            else:
                print(f"GitHubからの取得失敗: {response.status_code}")
                return None
        except Exception as e:
            print(f"GitHubコンテンツ取得エラー: {e}")
            return None
    
    def extract_metadata(self, content):
        """Front MatterからメタデータとMarkdown本文を抽出"""
        import re
        
        # Front Matterパターン
        fm_pattern = r'^---\n(.*?)\n---\n(.*)$'
        match = re.match(fm_pattern, content, re.DOTALL)
        
        if match:
            frontmatter = match.group(1)
            body = match.group(2)
            
            # YAMLパース（簡易版）
            metadata = {}
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
            
            return metadata, body
        else:
            # Front Matterがない場合
            return {}, content
    
    def post_from_github(self, repo_url, file_path):
        """GitHubのMarkdownファイルから投稿"""
        # GitHubからMarkdownを取得
        content = self.fetch_github_content(repo_url, file_path)
        if not content:
            return False
        
        # メタデータを抽出
        metadata, body = self.extract_metadata(content)
        
        # noteに投稿
        title = metadata.get('title', 'GitHub自動投稿')
        image_path = metadata.get('image')
        
        return self.note_poster.post_to_note(
            self.note_email,
            self.note_password,
            title,
            body,
            image_path
        )


def example_usage():
    """使用例"""
    # 環境変数から認証情報を取得
    email = os.getenv('NOTE_EMAIL', 'your-email@example.com')
    password = os.getenv('NOTE_PASSWORD', 'your-password')
    
    # 1. 定期投稿の例
    scheduler = NoteScheduler(email, password)
    # scheduler.schedule_daily_posts("09:00")  # 毎日9時に投稿
    
    # 2. 複数プラットフォーム投稿の例
    cross_poster = CrossPlatformPoster(email, password)
    results = cross_poster.cross_post(
        "複数プラットフォーム投稿テスト",
        "これは複数のプラットフォームに同時投稿するテストです。"
    )
    print(f"投稿結果: {results}")
    
    # 3. GitHubから自動投稿の例
    github_poster = GitHubPoster(email, password)
    github_poster.post_from_github(
        "https://github.com/your-username/your-repo",
        "articles/sample-article.md"
    )


if __name__ == "__main__":
    example_usage()
