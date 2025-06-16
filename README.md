# 社内情報特化型生成AI検索アプリ

## 概要

このアプリケーションは、社内文書をもとにユーザーからの入力に対して回答する生成AIチャットボットです。RAG（Retrieval-Augmented Generation）技術を活用し、社内の文書を効率的に検索・活用できます。

## 主な機能

### 📋 社内文書検索
- 入力内容と関連性が高い社内文書の場所を表示
- 例：「社員の育成方針に関するMTGの議事録」

### 💬 社内問い合わせ
- 社内文書をもとに質問への回答を生成
- 例：「人事部に所属している従業員情報を一覧化して」

## 技術スタック

- **フロントエンド**: Streamlit
- **LLM**: OpenAI GPT-4o-mini
- **ベクトルデータベース**: Chroma
- **文書処理**: LangChain
- **対応ファイル形式**: PDF, DOCX, CSV, TXT

## セットアップ

### 1. 環境構築

```bash
# リポジトリのクローン
git clone git@github.com:Takuya-ops/ragTestCompany_document.git
cd ragTestCompany_document

# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルを作成し、OpenAI APIキーを設定：

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. データの準備

`data/`フォルダに社内文書を配置：

```
data/
├── MTG議事録/
│   └── 開発/
│       └── 開発.pdf
├── 社員について/
│   └── 社員名簿.csv
└── 会社について/
    └── バーチャルビジョン合同会社.pdf
```

## 使用方法

### アプリケーションの起動

```bash
streamlit run main.py
```

ブラウザで `http://localhost:8501` にアクセス

### 使い分け

- **文書の場所を知りたい場合**: 「社内文書検索」モードを選択
- **内容を知りたい場合**: 「社内問い合わせ」モードを選択

## プロジェクト構成

```
├── main.py              # メインアプリケーション
├── initialize.py        # 初期化処理
├── components.py        # UI コンポーネント
├── utils.py            # ユーティリティ関数
├── constants.py        # 定数定義
├── requirements.txt    # 依存関係
├── .gitignore         # Git除外設定
├── data/              # 社内文書（除外）
├── logs/              # ログファイル（除外）
├── .chroma/           # ベクトルDB（除外）
└── venv/              # 仮想環境（除外）
```

## 実装済み機能

### ✅ 基本機能
- [x] RAGによる文書検索・回答生成
- [x] サイドバーでのモード選択
- [x] PDFファイルのページ番号表示
- [x] TXTファイル対応
- [x] CSVファイルの検索精度向上

### ✅ UI/UX改善
- [x] 見やすい回答表示形式
- [x] 重複文書の除去
- [x] スマートなモード提案機能
- [x] システム統計情報の表示

### ✅ 技術的改善
- [x] エラーハンドリングの強化
- [x] ログ機能の充実
- [x] LangChain非推奨警告の対応

## 開発者向け情報

### ログの確認

```bash
tail -f logs/application.log
```

### デバッグモード

サイドバーの「📊 システム情報を表示」をチェックすると、以下の情報が表示されます：
- 読み込み対象ファイル数
- ファイル種別ごとの統計
- 会話履歴数
- Retriever設定情報

## ライセンス

このプロジェクトは学習目的で作成されました。

## 貢献

バグ報告や機能提案は、GitHubのIssuesでお知らせください。 