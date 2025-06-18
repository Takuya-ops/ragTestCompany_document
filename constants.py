# ==============================================
# 定数管理ファイル
# ==============================================

# アプリケーション設定
APP_NAME = "社内情報特化型生成AI検索アプリ"
LOGGER_NAME = "company_inner_search_app"

# ディレクトリ設定
DATA_DIR = "data"  # 社内文書を格納するディレクトリ
CHROMA_DIR = ".chroma"  # Chromaベクトルデータベースのディレクトリ
FORCE_REBUILD_ENV = "FORCE_REBUILD_VECTORDB"  # 強制再構築の環境変数名

# 回答モード
ANSWER_MODE_1 = "社内文書検索"
ANSWER_MODE_2 = "社内問い合わせ"

# RAG設定
# 【問題1・2対応】ベクターストアから取得する関連ドキュメント数を3から5に変更し、変数化
RETRIEVER_K = 5  # ベクターストアから取り出すドキュメント数

# 【問題2対応】チャンク分割設定をマジックナンバーから変数化
CHUNK_SIZE = 800  # ドキュメントのチャンクサイズ（トークン制限対策で縮小）
CHUNK_OVERLAP = 150  # チャンクのオーバーラップサイズ

# ベクトル化バッチ処理設定
EMBEDDING_BATCH_SIZE = 50  # 一度にベクトル化するチャンク数（トークン制限対策）

# UI表示設定
CHAT_INPUT_HELPER_TEXT = "メッセージを入力してください"
SPINNER_TEXT = "回答を生成中..."

# アイコン設定
ERROR_ICON = "🚨"
SUCCESS_ICON = "✅"
SEARCH_ICON = "🔍"
QUESTION_ICON = "❓"

# エラーメッセージ
INITIALIZE_ERROR_MESSAGE = "初期化処理でエラーが発生しました"
CONVERSATION_LOG_ERROR_MESSAGE = "会話ログの表示でエラーが発生しました"
GET_LLM_RESPONSE_ERROR_MESSAGE = "LLMからの回答取得でエラーが発生しました"
DISP_ANSWER_ERROR_MESSAGE = "回答の表示でエラーが発生しました"

# ログメッセージ
APP_BOOT_MESSAGE = "アプリケーションが起動されました"

# 【問題5対応】対応ファイル拡張子にtxtを追加
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".csv", ".txt"]

# ページ番号表示用の設定（問題4対応）
PAGE_DISPLAY_FORMAT = "（{page}ページ目）"

# サイドバー設定（問題3対応）
SIDEBAR_TITLE = "🔧 利用目的を選択"
SIDEBAR_DESCRIPTION = "以下から利用目的を選択してください："

# モード説明
MODE_DESCRIPTIONS = {
    ANSWER_MODE_1: {
        "title": "📋 社内文書検索",
        "description": "入力内容と関連性が高い社内文書のありかを表示します。",
        "example": "例：「社員の育成方針に関するMTGの議事録」",
    },
    ANSWER_MODE_2: {
        "title": "💬 社内問い合わせ",
        "description": "社内文書をもとに質問への回答を生成します。",
        "example": "例：「人事部に所属している従業員情報を一覧化して」",
    },
}

# 初期AIメッセージ
INITIAL_AI_MESSAGE = """
こんにちは！社内情報特化型の生成AI検索アプリです。

**📋 社内文書検索**: 「○○に関する資料はどこにある？」など、文書の場所を知りたい場合
**💬 社内問い合わせ**: 「○○について教えて」「○○を要約して」など、内容を知りたい場合

サイドバーから利用目的を選択して、お気軽にご質問ください。
"""

# 関連文書が見つからない場合のメッセージ
NO_RELEVANT_DOCS_SEARCH = "入力内容と関連する社内文書が見つかりませんでした。"
NO_RELEVANT_DOCS_CONTACT = "回答に必要な情報が見つかりませんでした。"
