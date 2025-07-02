# 🐰 note非公式API記事自動投稿システム

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

note.comの非公式APIを使用して、Markdown形式の記事と画像を自動で下書き保存するPythonシステムです。

![Demo](https://via.placeholder.com/800x400/4CAF50/FFFFFF?text=note+Auto+Poster+System)

## ⚠️ 重要な注意事項

- **非公式API**: この記事で紹介するAPIは非公式のものです
- **仕様変更リスク**: 予告なく仕様が変更されたり、使用できなくなる可能性があります
- **利用規約遵守**: noteの利用規約に違反しないよう注意してください
- **サーバー負荷**: サーバーに負荷をかけないよう適切な利用を心がけてください

## 🌟 主な機能

### ✨ 基本機能
- **Markdown自動変換**: Markdown形式からHTMLへの自動変換
- **画像自動アップロード**: PNG, JPEG, GIF対応（最大10MB）
- **下書き自動保存**: 投稿前の安全な下書き保存
- **エラーハンドリング**: 包括的なエラー処理とリトライ機能

### 🔒 セキュリティ機能
- **Headless実行**: バックグラウンドでの安全な動作
- **認証情報管理**: 環境変数による安全な認証情報管理
- **レート制限対応**: APIレート制限の自動検出と待機

### 📈 拡張機能
- **定期投稿**: スケジュール機能による自動投稿
- **複数プラットフォーム**: note以外への同時投稿（拡張可能）
- **GitHub連携**: GitHubリポジトリからの自動投稿

## 🚀 クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone https://github.com/yshimamoto/note-auto-poster.git
cd note-auto-poster

# 依存関係をインストール
pip install -r requirements.txt
```

### 2. 環境設定

```bash
# 環境変数ファイルを作成
cp .env.example .env

# .envファイルを編集
nano .env
```

```.env
NOTE_EMAIL=your-email@example.com
NOTE_PASSWORD=your-password
```

### 3. 基本的な使用方法

```python
from improved_note_poster import NotePoster

# 投稿システムを初期化
poster = NotePoster()

# 記事内容を定義
title = "Pythonで自動投稿テスト"
content = """
# はじめに
これは自動投稿のテストです。

## 特徴
- **Markdown対応**: 簡単な記法で記事作成
- **画像アップロード**: 自動でアイキャッチ設定
- **安全な投稿**: 下書きとして保存

## まとめ
効率的な記事投稿が可能になります！
"""

# 投稿実行（画像はオプション）
success = poster.post_to_note(
    email=os.getenv('NOTE_EMAIL'),
    password=os.getenv('NOTE_PASSWORD'),
    title=title,
    markdown_content=content,
    image_path="thumbnail.png"  # オプション
)

if success:
    print("✅ 投稿完了！")
else:
    print("❌ 投稿失敗")
```

## 📁 ファイル構成

```
note-auto-poster/
├── 📄 note_poster.py              # オリジナル実装
├── ⭐ improved_note_poster.py     # 改善版（推奨）
├── 🧪 test_improved_note_poster.py # 単体テスト
├── 🔧 advanced_features.py        # 拡張機能
├── 📋 requirements.txt            # 依存関係
├── 🔐 .env.example               # 環境変数サンプル
├── 📊 CODE_REVIEW_REPORT.md      # コードレビューレポート
├── 📖 README.md                  # このファイル
└── 🚫 .gitignore                # Git無視設定
```

## 🛠️ API仕様

### noteの非公式APIエンドポイント

| エンドポイント | メソッド | 機能 |
|----------------|----------|------|
| `/api/v1/text_notes` | POST | 記事作成 |
| `/api/v1/text_notes/{id}` | PUT | 記事更新 |
| `/api/v1/upload_image` | POST | 画像アップロード |
| `/api/v2/creators/{username}` | GET | ユーザー情報取得 |
| `/api/v2/creators/{username}/contents` | GET | 記事一覧取得 |

## 📚 詳細な使用方法

### 🔄 定期投稿機能

```python
from advanced_features import NoteScheduler

# スケジューラーを設定
scheduler = NoteScheduler(
    email=os.getenv('NOTE_EMAIL'),
    password=os.getenv('NOTE_PASSWORD')
)

# 毎日午前9時に投稿
scheduler.schedule_daily_posts("09:00")
```

### 🌐 複数プラットフォーム投稿

```python
from advanced_features import CrossPlatformPoster

cross_poster = CrossPlatformPoster(
    note_email=os.getenv('NOTE_EMAIL'),
    note_password=os.getenv('NOTE_PASSWORD')
)

# 複数のプラットフォームに同時投稿
results = cross_poster.cross_post(
    title="複数プラットフォーム投稿テスト",
    content="これは複数のプラットフォームに同時投稿するテストです。",
    image_path="thumbnail.png"
)

print(f"投稿結果: {results}")
```

### 📂 GitHubからの自動投稿

```python
from advanced_features import GitHubPoster

github_poster = GitHubPoster(
    note_email=os.getenv('NOTE_EMAIL'),
    note_password=os.getenv('NOTE_PASSWORD')
)

# GitHubのMarkdownファイルから投稿
success = github_poster.post_from_github(
    repo_url="https://github.com/username/repo",
    file_path="articles/sample-article.md"
)
```

#### GitHubファイルの形式例

```markdown
---
title: "GitHubからの自動投稿テスト"
image: "thumbnail.png"
---

# GitHubからの投稿

この記事はGitHubリポジトリから自動投稿されました。

## 特徴
- Front Matterでメタデータを指定
- Markdownで記事本文を記述
- 自動でnoteに投稿
```

## 🧪 テスト実行

```bash
# 単体テストを実行
python -m pytest test_improved_note_poster.py -v

# カバレッジレポート付きで実行
python -m pytest test_improved_note_poster.py --cov=improved_note_poster --cov-report=html

# 特定のテストクラスのみ実行
python -m pytest test_improved_note_poster.py::TestNotePoster -v
```

## 🔧 設定オプション

### 環境変数一覧

| 変数名 | 必須 | 説明 | デフォルト値 |
|--------|------|------|-------------|
| `NOTE_EMAIL` | ✅ | noteのメールアドレス | - |
| `NOTE_PASSWORD` | ✅ | noteのパスワード | - |
| `LOG_LEVEL` | ❌ | ログレベル | INFO |
| `TIMEOUT` | ❌ | タイムアウト秒数 | 10 |
| `MAX_RETRIES` | ❌ | 最大リトライ回数 | 3 |

### Config設定のカスタマイズ

```python
from improved_note_poster import Config

# タイムアウト時間を変更
Config.TIMEOUT = 15

# リトライ回数を変更
Config.MAX_RETRIES = 5

# ChromeOptionsを追加
Config.CHROME_OPTIONS.append('--disable-web-security')
```

## 🛡️ セキュリティベストプラクティス

### 1. 認証情報の安全な管理

```bash
# 環境変数として設定（推奨）
export NOTE_EMAIL="your-email@example.com"
export NOTE_PASSWORD="your-secure-password"

# または.envファイルを使用
echo "NOTE_EMAIL=your-email@example.com" > .env
echo "NOTE_PASSWORD=your-secure-password" >> .env
```

### 2. 本番環境での推奨設定

```python
import logging

# ログレベルを適切に設定
logging.getLogger().setLevel(logging.WARNING)

# セキュリティオプションを追加
Config.CHROME_OPTIONS.extend([
    '--disable-logging',
    '--disable-gpu',
    '--no-first-run'
])
```

## 📊 パフォーマンス最適化

### レート制限の遵守

```python
# リクエスト間隔の調整
Config.WAIT_TIME = 3  # 3秒間隔

# 最大リトライ回数の調整
Config.MAX_RETRIES = 5
```

### バッチ処理での使用

```python
import time

articles = [
    ("記事1", "内容1"),
    ("記事2", "内容2"),
    ("記事3", "内容3")
]

poster = NotePoster()

for title, content in articles:
    success = poster.post_to_note(email, password, title, content)
    if success:
        print(f"✅ {title} - 投稿完了")
    else:
        print(f"❌ {title} - 投稿失敗")
    
    # レート制限を考慮した待機
    time.sleep(10)
```

## 🔍 トラブルシューティング

### よくある問題と解決策

#### 1. 認証エラー（401）
```
ERROR: ログインタイムアウト - 認証情報を確認してください
```
**解決策**: 
- メールアドレス・パスワードを確認
- 2段階認証が有効な場合は無効化
- アカウントロックの確認

#### 2. 画像アップロードエラー
```
ERROR: ファイルサイズが大きすぎます: 15.2MB
```
**解決策**: 
- 画像サイズを10MB以下に圧縮
- 対応形式（JPEG, PNG, GIF）を確認

#### 3. レート制限エラー（429）
```
WARNING: レート制限 - 6秒待機中...
```
**解決策**: 
- 自動的にリトライされるため待機
- `Config.WAIT_TIME`を増加

#### 4. WebDriverエラー
```
ERROR: WebDriverエラー: 'chromedriver' executable needs to be in PATH
```
**解決策**: 
```bash
# macOS
brew install chromedriver

# Ubuntu
sudo apt-get install chromium-chromedriver

# Windows
# https://chromedriver.chromium.org/ からダウンロード
```

## 📈 パフォーマンス監視

### ログの確認

```python
# ログファイルの確認
tail -f note_poster.log

# エラーのみを表示
grep ERROR note_poster.log
```

### 投稿統計の取得

```python
import json
from datetime import datetime

# 投稿結果のログ記録
def log_post_result(title, success, timestamp=None):
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    result = {
        'timestamp': timestamp,
        'title': title,
        'success': success
    }
    
    with open('post_statistics.json', 'a') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')
```

## 🤝 コントリビューション

### 開発環境のセットアップ

```bash
# 開発用依存関係をインストール
pip install -r requirements.txt

# コード品質チェック
black improved_note_poster.py
flake8 improved_note_poster.py
mypy improved_note_poster.py

# テスト実行
pytest test_improved_note_poster.py
```

### プルリクエストのガイドライン

1. **機能追加前にIssueを作成**
2. **テストを追加**
3. **コード品質チェックを通過**
4. **ドキュメントを更新**

## 📋 ロードマップ

### バージョン 2.0 計画

- [ ] **Web UI追加** - ブラウザベースの管理画面
- [ ] **Docker対応** - コンテナ化による環境統一
- [ ] **CI/CD構築** - GitHub Actionsによる自動テスト
- [ ] **複数アカウント対応** - チーム利用機能
- [ ] **分析ダッシュボード** - 投稿統計とパフォーマンス分析

### バージョン 1.5 計画

- [ ] **WordPress連携** - WordPressからの自動投稿
- [ ] **Notion連携** - Notionデータベースとの同期
- [ ] **RSS対応** - RSSフィードからの自動投稿
- [ ] **予約投稿機能** - 指定時刻での自動投稿

## 📜 ライセンス

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。

## 🙏 謝辞

- **元記事作成者**: [taku_sid🐰エージェント](https://note.com/taku_sid/n/n1b1b7894e28f)
- **note.com**: 非公式APIの提供
- **オープンソースコミュニティ**: 使用しているライブラリの開発者の皆様

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/yshimamoto/note-auto-poster/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yshimamoto/note-auto-poster/discussions)
- **Code Review**: [CODE_REVIEW_REPORT.md](CODE_REVIEW_REPORT.md)

---

**注意**: このシステムは教育目的および個人利用を想定しています。商用利用や大規模運用の際は、note.comの利用規約を十分に確認し、適切な利用を心がけてください。

⭐ **このプロジェクトが役に立った場合は、GitHubスターをお願いします！**
