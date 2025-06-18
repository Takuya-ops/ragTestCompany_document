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
import warnings


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
    ベクターストアの効率的な作成・読み込み
    既存のベクトルデータベースがある場合は再利用し、ない場合のみ新規作成
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    try:
        # 埋め込みモデルの初期化
        embeddings = OpenAIEmbeddings()

        # 強制再構築フラグの確認
        force_rebuild = os.getenv(ct.FORCE_REBUILD_ENV, "false").lower() == "true"
        chroma_dir = Path(ct.CHROMA_DIR)

        # 既存のベクトルデータベースをチェック
        if chroma_dir.exists() and not force_rebuild:
            logger.info("既存のベクトルデータベースを読み込み中...")
            try:
                # 既存のベクトルデータベースを読み込み
                vectorstore = Chroma(
                    persist_directory=str(chroma_dir), embedding_function=embeddings
                )

                # データベースが正常に読み込めるかテスト
                test_results = vectorstore.similarity_search("test", k=1)

                logger.info(
                    f"既存のベクトルデータベースを正常に読み込みました: {chroma_dir}"
                )

                # Retrieverを作成
                retriever = vectorstore.as_retriever(
                    search_type="similarity", search_kwargs={"k": ct.RETRIEVER_K}
                )

                # セッション状態に保存
                st.session_state.retriever = retriever
                return

            except Exception as e:
                logger.warning(f"既存のベクトルデータベース読み込みエラー: {e}")
                logger.info("新規にベクトルデータベースを作成します...")

        # 新規作成または再構築の場合
        if force_rebuild:
            logger.info("強制再構築モードでベクトルデータベースを作成中...")
        else:
            logger.info("新規ベクトルデータベースを作成中...")

        # ドキュメントの読み込み
        documents = load_documents()

        if not documents:
            st.warning("読み込み可能なドキュメントが見つかりませんでした。")
            return

        # 読み込み状況をログ出力
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
        logger.info(f"文書を{len(texts)}個のチャンクに分割しました")

        # 既存のディレクトリが存在する場合は削除
        if chroma_dir.exists():
            import shutil

            shutil.rmtree(chroma_dir)
            logger.info(f"既存のベクトルデータベースを削除しました: {chroma_dir}")

        # ベクターストアの作成（バッチ処理）
        try:
            logger.info("ベクトル化を実行中...")

            # バッチ処理でベクトル化を実行
            vectorstore = create_vectorstore_in_batches(
                texts, embeddings, str(chroma_dir), logger
            )

            logger.info(f"ベクトルデータベースを作成しました: {chroma_dir}")

        except Exception as e:
            logger.error(f"Chroma ベクターストア作成エラー: {type(e).__name__}: {e}")
            # 別のディレクトリで再試行
            try:
                import uuid

                temp_dir = f".chroma_{uuid.uuid4().hex[:8]}"
                logger.info(f"一時ディレクトリで再試行: {temp_dir}")

                # 一時ディレクトリでもバッチ処理を使用
                vectorstore = create_vectorstore_in_batches(
                    texts, embeddings, temp_dir, logger
                )

                logger.info(
                    f"一時ディレクトリでベクトルデータベースを作成しました: {temp_dir}"
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
        logger.info("ベクトルストアの設定が完了しました")

    except Exception as e:
        logger.error(f"ベクターストアの設定でエラー: {e}")
        raise


def load_documents():
    """
    文書を読み込む関数

    Returns:
        list: 読み込まれた文書のリスト
    """
    logger = logging.getLogger(ct.LOGGER_NAME)
    documents = []

    # dataディレクトリ内のファイルを走査
    data_dir = Path(ct.DATA_DIR)

    # 各ファイル形式に対応したローダーを使用（サブディレクトリも含む）
    for file_path in data_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ct.SUPPORTED_EXTENSIONS:
            try:
                # 警告を抑制しながらファイルを読み込み
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")

                    # ファイル形式に応じて処理を分岐
                    if file_path.suffix.lower() == ".pdf":
                        # カスタムPDFローダーを使用して警告を抑制
                        from utils import SilentPDFLoader

                        docs = SilentPDFLoader.load_pdf_silently(str(file_path))

                        # メタデータにファイル名とページ番号を追加
                        for i, doc in enumerate(docs):
                            doc.metadata["source_file"] = file_path.name
                            doc.metadata["page_number"] = i + 1
                            doc.metadata["file_type"] = "PDF"

                        documents.extend(docs)

                    elif file_path.suffix.lower() == ".docx":
                        from langchain_community.document_loaders import Docx2txtLoader

                        loader = Docx2txtLoader(str(file_path))
                        docs = loader.load()

                        # メタデータにファイル名を追加
                        for doc in docs:
                            doc.metadata["source_file"] = file_path.name
                            doc.metadata["file_type"] = "DOCX"

                        documents.extend(docs)

                    elif file_path.suffix.lower() == ".csv":
                        from langchain_community.document_loaders import CSVLoader

                        loader = CSVLoader(str(file_path))
                        docs = loader.load()

                        # メタデータにファイル名を追加
                        for doc in docs:
                            doc.metadata["source_file"] = file_path.name
                            doc.metadata["file_type"] = "CSV"

                        documents.extend(docs)

                    elif file_path.suffix.lower() == ".txt":
                        from langchain_community.document_loaders import TextLoader

                        loader = TextLoader(str(file_path), encoding="utf-8")
                        docs = loader.load()

                        # メタデータにファイル名を追加
                        for doc in docs:
                            doc.metadata["source_file"] = file_path.name
                            doc.metadata["file_type"] = "TXT"

                        documents.extend(docs)

                    logger.info(f"読み込み完了: {file_path.name}")

            except Exception as e:
                logger.error(f"ファイル読み込みエラー ({file_path.name}): {e}")
                continue

    logger.info(f"総読み込み文書数: {len(documents)}")
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


def create_vectorstore_in_batches(texts, embeddings, persist_directory, logger):
    """
    バッチ処理でベクトルストアを作成する（OpenAI APIトークン制限対策）

    Args:
        texts: 分割されたドキュメントのリスト
        embeddings: 埋め込みモデル
        persist_directory: 永続化ディレクトリ
        logger: ロガー

    Returns:
        Chroma: 作成されたベクトルストア
    """
    import math

    total_chunks = len(texts)
    batch_size = ct.EMBEDDING_BATCH_SIZE
    total_batches = math.ceil(total_chunks / batch_size)

    logger.info(
        f"総チャンク数: {total_chunks}個を{batch_size}個ずつ{total_batches}バッチで処理します"
    )

    vectorstore = None

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, total_chunks)
        batch_texts = texts[start_idx:end_idx]

        logger.info(
            f"バッチ {batch_num + 1}/{total_batches}: チャンク {start_idx + 1}-{end_idx} を処理中..."
        )

        try:
            if batch_num == 0:
                # 最初のバッチでベクトルストアを作成
                vectorstore = Chroma.from_documents(
                    documents=batch_texts,
                    embedding=embeddings,
                    persist_directory=persist_directory,
                )
            else:
                # 既存のベクトルストアに追加
                vectorstore.add_documents(batch_texts)

            logger.info(f"バッチ {batch_num + 1}/{total_batches} 完了")

        except Exception as e:
            logger.error(f"バッチ {batch_num + 1} でエラー: {e}")
            raise

    logger.info(f"全{total_batches}バッチの処理が完了しました")
    return vectorstore
