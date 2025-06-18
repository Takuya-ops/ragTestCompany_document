import streamlit as st
import logging
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
import constants as ct
import pandas as pd
from pathlib import Path
import warnings
import os
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr


# PDF関連の警告を完全に抑制するためのクラス
class SilentPDFLoader:
    """PDF読み込み時の警告を完全に抑制するためのカスタムローダー"""

    @staticmethod
    def load_pdf_silently(file_path):
        """PDFファイルを警告なしで読み込む"""
        # 標準出力とエラー出力を一時的に無効化
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            # 出力を/dev/nullにリダイレクト
            with open(os.devnull, "w") as devnull:
                sys.stdout = devnull
                sys.stderr = devnull

                # 警告を抑制
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")

                    # PDFローダーのインポートと実行
                    from langchain_community.document_loaders import PyPDFLoader

                    loader = PyPDFLoader(file_path)
                    documents = loader.load()

                    return documents

        finally:
            # 標準出力とエラー出力を復元
            sys.stdout = old_stdout
            sys.stderr = old_stderr


# 警告抑制の設定
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["PYPDF_VERBOSE"] = "0"


def build_error_message(base_message):
    """
    エラーメッセージを整形

    Args:
        base_message (str): ベースとなるエラーメッセージ

    Returns:
        str: 整形されたエラーメッセージ
    """
    return f"{ct.ERROR_ICON} {base_message}\n\n管理者にお問い合わせください。"


def get_llm_response(user_message):
    """
    LLMからの回答を取得

    Args:
        user_message (str): ユーザーからのメッセージ

    Returns:
        object: LLMからの回答
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    try:
        # Retrieverが設定されているかチェック
        if not st.session_state.retriever:
            raise ValueError("Retrieverが初期化されていません")

        # LLMの初期化（警告抑制）
        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

        # モードに応じてプロンプトを変更
        if st.session_state.mode == ct.ANSWER_MODE_1:
            # 社内文書検索モード
            template = """
            あなたは社内文書検索アシスタントです。以下の社内文書の中から、ユーザーの入力に関連する文書を見つけて、その内容を簡潔に説明してください。
            
            社内文書: {context}
            
            ユーザーの入力: {question}
            
            指示:
            1. 提供された社内文書の内容を必ず確認してください
            2. ユーザーの入力に関連する文書があれば、その文書の内容を簡潔に説明してください
            3. 複数の関連文書がある場合は、最も関連性の高いものを中心に回答してください
            4. 本当に関連する情報が全く見つからない場合のみ、「入力内容と関連する社内文書が見つかりませんでした。」と回答してください
            
            回答:
            """
        else:
            # 社内問い合わせモード
            template = """
            あなたは社内問い合わせアシスタントです。以下の社内文書をもとに、ユーザーの質問に詳しく回答してください。
            
            社内文書: {context}
            
            質問: {question}
            
            指示:
            1. 提供された社内文書の内容を必ず確認し、活用してください
            2. 文書の内容から質問に答えられる情報を抽出してください
            3. 具体的で実用的な回答を提供してください
            4. 関連する情報が文書に含まれている場合は、必ずそれを活用してください
            5. 本当に回答に必要な情報が全く見つからない場合のみ、「回答に必要な情報が見つかりませんでした。」と回答してください
            
            回答:
            """

        # RetrievalQAチェーンの作成
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=st.session_state.retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": create_custom_prompt(template)},
        )

        # モード提案機能：質問内容に応じて適切なモードを提案
        suggest_mode_if_needed(user_message)

        # 【問題6対応】CSVファイルの統合処理
        enhanced_message = enhance_message_for_csv(user_message)

        # クエリの実行
        response = qa_chain.invoke({"query": enhanced_message})

        # デバッグ用：取得された文書の情報をログ出力
        if hasattr(response, "source_documents") and response.source_documents:
            logger.info(f"取得された文書数: {len(response.source_documents)}")
            for i, doc in enumerate(response.source_documents[:3]):  # 最初の3つのみ
                doc_info = {
                    "index": i,
                    "source": doc.metadata.get("source_file", "unknown"),
                    "content_preview": (
                        doc.page_content[:200] + "..."
                        if len(doc.page_content) > 200
                        else doc.page_content
                    ),
                }
                logger.info(f"文書{i+1}: {doc_info}")

        logger.info(f"LLM回答生成完了: {user_message}")
        return response

    except Exception as e:
        logger.error(f"LLM回答取得エラー: {e}")
        raise


def create_custom_prompt(template):
    """
    カスタムプロンプトテンプレートを作成

    Args:
        template (str): プロンプトテンプレート

    Returns:
        PromptTemplate: プロンプトテンプレートオブジェクト
    """
    from langchain.prompts import PromptTemplate

    return PromptTemplate(template=template, input_variables=["context", "question"])


def enhance_message_for_csv(user_message):
    """
    【問題6対応】CSVファイル検索の精度向上のためメッセージを強化

    Args:
        user_message (str): 元のユーザーメッセージ

    Returns:
        str: 強化されたメッセージ
    """
    # 人事部関連の検索を検知
    if any(
        keyword in user_message.lower()
        for keyword in ["人事部", "従業員", "社員名簿", "一覧"]
    ):
        # CSVデータの統合情報を追加
        enhanced_message = f"""
        {user_message}
        
        なお、社員名簿の情報は以下の統合データを参照してください：
        {get_consolidated_employee_data()}
        """
        return enhanced_message

    return user_message


def suggest_mode_if_needed(user_message):
    """
    質問内容に応じて適切なモードを提案

    Args:
        user_message (str): ユーザーメッセージ
    """
    # 内容を求める質問のキーワード
    content_keywords = [
        "要約",
        "教えて",
        "説明",
        "内容",
        "どんな",
        "何について",
        "詳細",
        "情報",
        "について",
        "とは",
        "どのような",
    ]

    # 場所を求める質問のキーワード
    location_keywords = ["どこ", "ありか", "場所", "ファイル", "資料", "文書", "見つけ"]

    current_mode = st.session_state.mode

    # 内容を求める質問なのに検索モードの場合
    if current_mode == ct.ANSWER_MODE_1 and any(
        keyword in user_message for keyword in content_keywords
    ):
        st.info(
            f"💡 **モード提案**: 「{user_message}」のような質問には、"
            f"サイドバーで「**{ct.ANSWER_MODE_2}**」を選択すると、"
            f"文書の内容に基づいた詳しい回答が得られます。"
        )

    # 場所を求める質問なのに問い合わせモードの場合
    elif current_mode == ct.ANSWER_MODE_2 and any(
        keyword in user_message for keyword in location_keywords
    ):
        st.info(
            f"💡 **モード提案**: 「{user_message}」のような質問には、"
            f"サイドバーで「**{ct.ANSWER_MODE_1}**」を選択すると、"
            f"関連文書の場所が表示されます。"
        )


def get_consolidated_employee_data():
    """
    【問題6対応】社員名簿CSVの統合データを取得

    Returns:
        str: 統合された社員データのテキスト
    """
    try:
        # 社員名簿ファイルのパス
        csv_file_path = Path("data/社員について/社員名簿.csv")

        if not csv_file_path.exists():
            return "社員名簿ファイルが見つかりません。"

        # CSVファイルを読み込み
        df = pd.read_csv(csv_file_path, encoding="utf-8")

        # 人事部の従業員のみを抽出
        hr_employees = df[df["部署"] == "人事部"]

        if hr_employees.empty:
            return "人事部の従業員情報が見つかりません。"

        # 統合データとしてフォーマット
        consolidated_data = "【人事部所属従業員一覧】\n"
        for index, row in hr_employees.iterrows():
            consolidated_data += f"- {row['名前']} (ID: {row['社員ID']}, 役職: {row['役職']}, 入社年: {row['入社年']})\n"

        # 全社員数との比較情報も追加
        total_employees = len(df)
        hr_count = len(hr_employees)
        consolidated_data += (
            f"\n人事部従業員数: {hr_count}人 / 全社員数: {total_employees}人"
        )

        return consolidated_data

    except Exception as e:
        return f"社員名簿の処理中にエラーが発生しました: {e}"


def validate_environment():
    """
    環境設定を検証

    Returns:
        bool: 環境が正しく設定されている場合True
    """
    try:
        # 必要なセッション状態の確認
        if not hasattr(st.session_state, "retriever"):
            st.error("Retrieverが初期化されていません。")
            return False

        if not hasattr(st.session_state, "mode"):
            st.error("モードが設定されていません。")
            return False

        if not hasattr(st.session_state, "messages"):
            st.error("メッセージログが初期化されていません。")
            return False

        return True

    except Exception as e:
        st.error(f"環境検証中にエラーが発生しました: {e}")
        return False


def log_user_interaction(user_message, llm_response, mode):
    """
    ユーザーとのインタラクションをログに記録

    Args:
        user_message (str): ユーザーメッセージ
        llm_response (object): LLMからの回答
        mode (str): 現在のモード
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    try:
        interaction_log = {
            "user_message": user_message,
            "ai_response": (
                llm_response.get("result", "")
                if isinstance(llm_response, dict)
                else str(llm_response)
            ),
            "mode": mode,
            "timestamp": pd.Timestamp.now().isoformat(),
            "source_documents_count": (
                len(llm_response.get("source_documents", []))
                if isinstance(llm_response, dict)
                else 0
            ),
        }

        logger.info(f"User interaction logged: {interaction_log}")

    except Exception as e:
        logger.error(f"インタラクションログ記録エラー: {e}")


def get_file_statistics():
    """
    ファイル統計情報を取得

    Returns:
        dict: ファイル統計情報
    """
    try:
        data_path = Path("data")
        stats = {"total_files": 0, "file_types": {}}

        if data_path.exists():
            for file_path in data_path.rglob("*"):
                if file_path.is_file():
                    stats["total_files"] += 1
                    file_ext = file_path.suffix.lower()
                    if file_ext:
                        file_ext = file_ext[1:]  # Remove the dot
                        stats["file_types"][file_ext] = (
                            stats["file_types"].get(file_ext, 0) + 1
                        )
                    else:
                        stats["file_types"]["その他"] = (
                            stats["file_types"].get("その他", 0) + 1
                        )

        return stats

    except Exception as e:
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.error(f"ファイル統計取得エラー: {e}")
        return {"total_files": 0, "file_types": {}}


def force_rebuild_vectordb():
    """
    ベクトルデータベースの強制再構築を実行
    """
    import shutil
    from pathlib import Path
    import constants as ct

    logger = logging.getLogger(ct.LOGGER_NAME)

    try:
        # 既存のベクトルデータベースを削除
        chroma_dir = Path(ct.CHROMA_DIR)
        if chroma_dir.exists():
            shutil.rmtree(chroma_dir)
            logger.info(f"ベクトルデータベースを削除しました: {chroma_dir}")

        # 一時ディレクトリも削除
        for temp_dir in Path(".").glob(".chroma_*"):
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir)
                logger.info(f"一時ディレクトリを削除しました: {temp_dir}")

        st.success("ベクトルデータベースを削除しました。アプリを再起動してください。")

    except Exception as e:
        logger.error(f"ベクトルデータベース削除エラー: {e}")
        st.error(f"削除に失敗しました: {e}")


def get_vectordb_info():
    """
    ベクトルデータベースの情報を取得
    """
    from pathlib import Path
    import constants as ct

    info = {"exists": False, "size": 0, "path": ct.CHROMA_DIR, "temp_dirs": []}

    # メインディレクトリの確認
    chroma_dir = Path(ct.CHROMA_DIR)
    if chroma_dir.exists():
        info["exists"] = True
        info["size"] = sum(
            f.stat().st_size for f in chroma_dir.rglob("*") if f.is_file()
        )

    # 一時ディレクトリの確認
    for temp_dir in Path(".").glob(".chroma_*"):
        if temp_dir.is_dir():
            temp_size = sum(
                f.stat().st_size for f in temp_dir.rglob("*") if f.is_file()
            )
            info["temp_dirs"].append({"path": str(temp_dir), "size": temp_size})

    return info


def format_file_size(size_bytes):
    """
    ファイルサイズを人間が読みやすい形式に変換
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"
