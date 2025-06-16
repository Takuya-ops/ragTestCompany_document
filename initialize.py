import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader, CSVLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import constants as ct


def initialize():
    """
    アプリ起動時の初期化処理
    """

    # 環境変数の読み込み
    load_dotenv()

    # ログ設定
    setup_logging()

    # セッション状態の初期化
    initialize_session_state()

    # ベクターストアの作成・読み込み
    setup_vector_store()


def setup_logging():
    """
    ログ出力の設定
    """
    # logsフォルダの作成
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # ログファイルのパス
    log_file = log_dir / "application.log"

    # ロガーの設定
    logger = logging.getLogger(ct.LOGGER_NAME)
    logger.setLevel(logging.INFO)

    # ハンドラーがすでに設定されている場合はスキップ
    if not logger.handlers:
        # ファイルハンドラーの設定（ローテーション機能付き）
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )

        # フォーマッターの設定
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # ハンドラーをロガーに追加
        logger.addHandler(file_handler)


def initialize_session_state():
    """
    Streamlitのセッション状態を初期化
    """
    # 会話ログの初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # モード（利用目的）の初期化
    if "mode" not in st.session_state:
        st.session_state.mode = ct.ANSWER_MODE_1

    # Retrieverの初期化
    if "retriever" not in st.session_state:
        st.session_state.retriever = None


def setup_vector_store():
    """
    ベクターストアの作成・読み込み
    """
    try:
        # データフォルダのパス
        data_folder = Path("data")

        # ドキュメントの読み込み
        documents = load_documents(data_folder)

        if not documents:
            st.warning("読み込み可能なドキュメントが見つかりませんでした。")
            return

        # 読み込み状況をログ出力
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.info(f"読み込まれた文書数: {len(documents)}")

        # ファイル別の読み込み状況
        file_counts = {}
        for doc in documents:
            file_name = doc.metadata.get("source_file", "unknown")
            file_counts[file_name] = file_counts.get(file_name, 0) + 1

        for file_name, count in file_counts.items():
            logger.info(f"ファイル: {file_name}, チャンク数: {count}")

        # 【問題2対応】定数を使用してチャンク分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=ct.CHUNK_SIZE,
            chunk_overlap=ct.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

        # ドキュメントの分割
        texts = text_splitter.split_documents(documents)

        # 埋め込みモデルの初期化
        embeddings = OpenAIEmbeddings()

        # 既存のベクターストアがある場合は削除（デバッグ用）
        # import shutil
        # chroma_dir = Path(".chroma")
        # if chroma_dir.exists():
        #     shutil.rmtree(chroma_dir)

        # ベクターストアの作成
        try:
            vectorstore = Chroma.from_documents(
                documents=texts, embedding=embeddings, persist_directory=".chroma"
            )
        except Exception as e:
            logger.error(f"Chroma ベクターストア作成エラー: {type(e).__name__}: {e}")
            # 別のディレクトリで再試行
            try:
                import uuid

                temp_dir = f".chroma_{uuid.uuid4().hex[:8]}"
                logger.info(f"一時ディレクトリで再試行: {temp_dir}")
                vectorstore = Chroma.from_documents(
                    documents=texts, embedding=embeddings, persist_directory=temp_dir
                )
            except Exception as e2:
                logger.error(f"再試行も失敗: {type(e2).__name__}: {e2}")
                raise

        # 【問題1・2対応】定数を使用してRetrieverを作成
        retriever = vectorstore.as_retriever(
            search_type="similarity", search_kwargs={"k": ct.RETRIEVER_K}
        )

        # セッション状態に保存
        st.session_state.retriever = retriever

    except Exception as e:
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.error(f"ベクターストアの設定でエラー: {e}")
        raise


def load_documents(data_folder):
    """
    データフォルダからドキュメントを読み込み

    Args:
        data_folder (Path): データフォルダのパス

    Returns:
        list: 読み込んだドキュメントのリスト
    """
    documents = []

    if not data_folder.exists():
        return documents

    # 【問題5対応】txtファイルも含めて処理
    for file_path in data_folder.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ct.SUPPORTED_EXTENSIONS:
            try:
                docs = load_single_document(file_path)
                documents.extend(docs)
            except Exception as e:
                logger = logging.getLogger(ct.LOGGER_NAME)
                logger.warning(f"ファイル読み込みエラー {file_path}: {e}")

    return documents


def load_single_document(file_path):
    """
    単一ドキュメントの読み込み

    Args:
        file_path (Path): ファイルパス

    Returns:
        list: ドキュメントのリスト
    """
    file_extension = file_path.suffix.lower()

    if file_extension == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif file_extension == ".docx":
        loader = Docx2txtLoader(str(file_path))
    elif file_extension == ".csv":
        loader = CSVLoader(str(file_path), encoding="utf-8")
    elif file_extension == ".txt":
        # 【問題5対応】txtファイルローダーの実装
        loader = TextFileLoader(str(file_path))
    else:
        return []

    documents = loader.load()

    # メタデータにファイル情報を追加
    for doc in documents:
        doc.metadata["source_file"] = file_path.name
        doc.metadata["file_path"] = str(file_path)
        doc.metadata["file_type"] = file_extension

        # 【問題4対応】PDFの場合はページ番号を取得・設定
        if file_extension == ".pdf" and "page" in doc.metadata:
            doc.metadata["page_number"] = (
                doc.metadata["page"] + 1
            )  # 0ベースから1ベースに変換

    return documents


class TextFileLoader:
    """
    【問題5対応】テキストファイル用のカスタムローダー
    """

    def __init__(self, file_path, encoding="utf-8"):
        self.file_path = file_path
        self.encoding = encoding

    def load(self):
        """
        テキストファイルを読み込み、Documentオブジェクトとして返す
        """
        from langchain.schema import Document

        with open(self.file_path, "r", encoding=self.encoding) as f:
            content = f.read()

        # ファイル名からメタデータを作成
        metadata = {
            "source": self.file_path,
        }

        return [Document(page_content=content, metadata=metadata)]
