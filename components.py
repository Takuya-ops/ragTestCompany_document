import streamlit as st
import constants as ct
import logging


def display_app_title():
    """
    アプリのタイトルを表示
    """
    st.title(ct.APP_NAME)
    st.markdown("---")


def display_select_mode():
    """
    【問題3対応】サイドバーで利用目的を選択
    """
    with st.sidebar:
        st.markdown(f"## {ct.SIDEBAR_TITLE}")
        st.markdown(ct.SIDEBAR_DESCRIPTION)

        # ラジオボタンでモード選択
        mode = st.radio(
            "利用目的",
            [ct.ANSWER_MODE_1, ct.ANSWER_MODE_2],
            index=0 if st.session_state.mode == ct.ANSWER_MODE_1 else 1,
            label_visibility="collapsed",
        )

        # セッション状態を更新
        st.session_state.mode = mode

        # 選択されたモードの説明を表示
        st.markdown("---")
        mode_info = ct.MODE_DESCRIPTIONS[mode]
        st.markdown(f"### {mode_info['title']}")
        st.markdown(mode_info["description"])
        st.markdown(f"**{mode_info['example']}**")


def display_initial_ai_message():
    """
    初期AIメッセージの表示
    """
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown(ct.INITIAL_AI_MESSAGE)


def display_conversation_log():
    """
    会話ログの表示
    """
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def display_search_llm_response(llm_response):
    """
    【問題4対応】「社内文書検索」モードでのLLM回答表示（ページ番号対応）

    Args:
        llm_response: LLMからの回答データ

    Returns:
        str: 表示されたコンテンツ
    """
    try:
        # デバッグ用：レスポンスの型と内容をログ出力
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.info(f"検索レスポンス型: {type(llm_response)}")

        # レスポンスからドキュメント情報を取得
        source_documents = []
        if isinstance(llm_response, dict):
            source_documents = llm_response.get("source_documents", [])
        elif hasattr(llm_response, "source_documents"):
            source_documents = llm_response.source_documents

        if source_documents:
            # 関連文書が見つかった場合
            content_parts = []
            content_parts.append("**📋 関連する社内文書**")
            content_parts.append("")

            # 重複を除去してユニークな文書のみ表示
            unique_docs = {}
            for doc in source_documents:
                source_key = format_document_source(doc, False)
                if source_key not in unique_docs:
                    unique_docs[source_key] = doc

            # メインの文書（最も関連性が高い）
            if unique_docs:
                main_source = list(unique_docs.keys())[0]
                content_parts.append(f"🔍 **メイン参照文書:** {main_source}")
                content_parts.append("")

                # その他の関連文書
                if len(unique_docs) > 1:
                    content_parts.append("📚 **その他の関連文書:**")
                    for i, source_name in enumerate(list(unique_docs.keys())[1:], 1):
                        content_parts.append(f"{i}. {source_name}")

            content = "\n".join(content_parts)
        else:
            # 関連文書が見つからない場合
            content = ct.NO_RELEVANT_DOCS_SEARCH

        st.markdown(content)
        return content

    except Exception as e:
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.error(f"検索結果表示エラー: {e}")
        logger.error(f"エラーの詳細: {type(e).__name__}: {e}")
        logger.error(f"レスポンスデータ: {llm_response}")
        content = "回答の表示中にエラーが発生しました。"
        st.error(content)
        return content


def display_contact_llm_response(llm_response):
    """
    【問題4対応】「社内問い合わせ」モードでのLLM回答表示（ページ番号対応）

    Args:
        llm_response: LLMからの回答データ

    Returns:
        str: 表示されたコンテンツ
    """
    try:
        # デバッグ用：レスポンスの型と内容をログ出力
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.info(f"レスポンス型: {type(llm_response)}")
        logger.info(f"レスポンス属性: {dir(llm_response)}")

        # 辞書形式のレスポンスの場合
        if isinstance(llm_response, dict):
            answer_text = llm_response.get(
                "result", llm_response.get("answer", "回答が見つかりませんでした")
            )
            source_documents = llm_response.get("source_documents", [])
        # オブジェクト形式のレスポンスの場合
        elif hasattr(llm_response, "result") and llm_response.result:
            answer_text = llm_response.result
            source_documents = getattr(llm_response, "source_documents", [])
        elif hasattr(llm_response, "answer") and llm_response.answer:
            answer_text = llm_response.answer
            source_documents = getattr(llm_response, "source_documents", [])
        else:
            # 生のJSONが来た場合は警告を出して、適切に処理
            logger.warning(f"予期しないレスポンス形式: {llm_response}")
            st.warning("⚠️ システム内部で予期しない形式のレスポンスが発生しました。")
            st.json(llm_response)  # デバッグ用にJSONを表示
            return "予期しないレスポンス形式"

        # 関連文書情報が見つからない場合のチェック
        if ct.NO_RELEVANT_DOCS_CONTACT.lower() in answer_text.lower():
            content = ct.NO_RELEVANT_DOCS_CONTACT
            st.markdown(content)
            return content

        # 回答テキストを表示
        st.markdown("💬 **回答:**")
        st.markdown(answer_text)
        st.markdown("")

        # 参照文書の表示
        if source_documents:
            st.markdown("📚 **参照した社内文書:**")

            # 重複を除去してユニークな文書のみ表示
            unique_docs = {}
            for doc in source_documents:
                source_key = format_document_source(doc, False)
                if source_key not in unique_docs:
                    unique_docs[source_key] = doc

            for i, (source_name, doc) in enumerate(unique_docs.items(), 1):
                st.markdown(f"{i}. {source_name}")

        # 返却用のコンテンツを作成
        content_parts = [f"💬 **回答:** {answer_text}"]
        if source_documents and len(unique_docs) > 0:
            content_parts.append("\n📚 **参照した社内文書:**")
            for i, source_name in enumerate(unique_docs.keys(), 1):
                content_parts.append(f"{i}. {source_name}")

        content = "\n".join(content_parts)
        return content

    except Exception as e:
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.error(f"問い合わせ結果表示エラー: {e}")
        logger.error(f"エラーの詳細: {type(e).__name__}: {e}")
        logger.error(f"レスポンスデータ: {llm_response}")
        content = "回答の表示中にエラーが発生しました。"
        st.error(content)
        return content


def format_document_source(document, is_main=False):
    """
    【問題4対応】ドキュメントのソース情報をフォーマット（ページ番号対応）

    Args:
        document: ドキュメントオブジェクト
        is_main (bool): メイン文書かどうか

    Returns:
        str: フォーマットされたソース情報
    """
    try:
        # ファイル名を取得
        if "source_file" in document.metadata:
            file_name = document.metadata["source_file"]
        elif "source" in document.metadata:
            file_name = document.metadata["source"].split("/")[-1]
        else:
            file_name = "不明なファイル"

        # 【問題4対応】PDFファイルの場合はページ番号を追加
        if file_name.lower().endswith(".pdf"):
            page_info = ""
            if "page_number" in document.metadata:
                page_num = document.metadata["page_number"]
                page_info = ct.PAGE_DISPLAY_FORMAT.format(page=page_num)
            elif "page" in document.metadata:
                # 0ベースの場合は1を足す
                page_num = document.metadata["page"] + 1
                page_info = ct.PAGE_DISPLAY_FORMAT.format(page=page_num)

            return f"{file_name}{page_info}"
        else:
            return file_name

    except Exception as e:
        logger = logging.getLogger(ct.LOGGER_NAME)
        logger.warning(f"ソース情報フォーマットエラー: {e}")
        return "ソース情報取得エラー"


def display_error_message(message):
    """
    エラーメッセージの表示

    Args:
        message (str): エラーメッセージ
    """
    st.error(message, icon=ct.ERROR_ICON)


def display_success_message(message):
    """
    成功メッセージの表示

    Args:
        message (str): 成功メッセージ
    """
    st.success(message, icon=ct.SUCCESS_ICON)
