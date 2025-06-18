# ==============================================
# 社内情報特化型生成AI検索アプリ - メイン処理
# ==============================================

# 「.env」ファイルから環境変数を読み込むための関数
from dotenv import load_dotenv

# ログ出力を行うためのモジュール
import logging

# 警告の抑制
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*wrong pointing object.*")
warnings.filterwarnings("ignore", message=".*custom sys.excepthook.*")

# streamlitアプリの表示を担当するモジュール
import streamlit as st

# （自作）画面表示以外の様々な関数が定義されているモジュール
import utils

# （自作）アプリ起動時に実行される初期化処理が記述された関数
from initialize import initialize

# （自作）画面表示系の関数が定義されているモジュール
import components as cn

# （自作）変数（定数）がまとめて定義・管理されているモジュール
import constants as ct

# ==============================================
# 2. 設定関連
# ==============================================

# ブラウザタブの表示文言を設定
st.set_page_config(
    page_title=ct.APP_NAME,
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ログ出力を行うためのロガーの設定
logger = logging.getLogger(ct.LOGGER_NAME)

# ==============================================
# 3. 初期化処理
# ==============================================

try:
    # 初期化処理（「initialize.py」の「initialize」関数を実行）
    initialize()

except Exception as e:
    # エラーログの出力
    logger.error(f"{ct.INITIALIZE_ERROR_MESSAGE}\n{e}")

    # エラーメッセージの画面表示
    st.error(utils.build_error_message(ct.INITIALIZE_ERROR_MESSAGE), icon=ct.ERROR_ICON)

    # 後続の処理を中断
    st.stop()

# アプリ起動時のログファイルへの出力
if not "initialized" in st.session_state:
    st.session_state.initialized = True
    logger.info(ct.APP_BOOT_MESSAGE)

# 環境検証
if not utils.validate_environment():
    st.stop()

# ==============================================
# 4. 初期表示
# ==============================================

# タイトル表示
cn.display_app_title()

# 【問題3対応】サイドバーでモード表示
cn.display_select_mode()

# AIメッセージの初期表示
cn.display_initial_ai_message()

# ==============================================
# 5. 会話ログの表示
# ==============================================

try:
    # 会話ログの表示
    cn.display_conversation_log()

except Exception as e:
    # エラーログの出力
    logger.error(f"{ct.CONVERSATION_LOG_ERROR_MESSAGE}\n{e}")

    # エラーメッセージの画面表示
    st.error(
        utils.build_error_message(ct.CONVERSATION_LOG_ERROR_MESSAGE), icon=ct.ERROR_ICON
    )

    # 後続の処理を中断
    st.stop()

# ==============================================
# 6. チャット入力の受け付け
# ==============================================

chat_message = st.chat_input(ct.CHAT_INPUT_HELPER_TEXT)

# ==============================================
# 7. チャット送信時の処理
# ==============================================

if chat_message:

    # ==============================================
    # 7-1. ユーザーメッセージの処理
    # ==============================================

    # ユーザーメッセージのログ出力
    logger.info({"message": chat_message, "application_mode": st.session_state.mode})

    # ユーザーメッセージを表示
    with st.chat_message("user"):
        st.markdown(chat_message)

    # ==============================================
    # 7-2. LLMからの回答取得
    # ==============================================

    # 「st.spinner」でグルグル回っている間、表示の不具合が発生しないよう空のエリアを表示
    res_box = st.empty()

    # LLMによる回答生成（回答生成が完了するまでグルグル回す）
    with st.spinner(ct.SPINNER_TEXT):

        try:

            # 画面読み込み時に作成したRetrieverを使い、Chainを実行
            llm_response = utils.get_llm_response(chat_message)

        except Exception as e:

            # エラーログの出力
            logger.error(f"{ct.GET_LLM_RESPONSE_ERROR_MESSAGE}\n{e}")

            # エラーメッセージの画面表示
            st.error(
                utils.build_error_message(ct.GET_LLM_RESPONSE_ERROR_MESSAGE),
                icon=ct.ERROR_ICON,
            )

            # 後続の処理を中断
            st.stop()

    # ==============================================
    # 7-3. LLMからの回答表示
    # ==============================================

    with st.chat_message("assistant"):

        try:

            # ==========================================
            # モードが「社内文書検索」の場合
            # ==========================================
            if st.session_state.mode == ct.ANSWER_MODE_1:

                # 【問題4対応】入力内容と関連性が高い社内文書のありかを表示（ページ番号付き）
                content = cn.display_search_llm_response(llm_response)

            # ==========================================
            # モードが「社内問い合わせ」の場合
            # ==========================================
            elif st.session_state.mode == ct.ANSWER_MODE_2:

                # 【問題4対応】入力に対しての回答と、参照した文書のありかを表示（ページ番号付き）
                content = cn.display_contact_llm_response(llm_response)

            # AIメッセージのログ出力
            logger.info({"message": content, "application_mode": st.session_state.mode})

            # インタラクションログの記録
            utils.log_user_interaction(
                chat_message, llm_response, st.session_state.mode
            )

        except Exception as e:

            # エラーログの出力
            logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}")

            # エラーメッセージの画面表示
            st.error(
                utils.build_error_message(ct.DISP_ANSWER_ERROR_MESSAGE),
                icon=ct.ERROR_ICON,
            )

            # 後続の処理を中断
            st.stop()

    # ==============================================
    # 7-4. 会話ログへの追加
    # ==============================================

    # 表示用の会話ログにユーザーメッセージを追加
    st.session_state.messages.append({"role": "user", "content": chat_message})

    # 表示用の会話ログにAIメッセージを追加
    st.session_state.messages.append({"role": "assistant", "content": content})

# ==============================================
# サイドバーに統計情報を表示（開発・デバッグ用）
# ==============================================

if st.sidebar.checkbox("📊 システム情報を表示", value=False):
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 システム統計")

        # ファイル統計
        stats = utils.get_file_statistics()
        st.markdown(f"**読み込み対象ファイル数:** {stats['total_files']}")

        for file_type, count in stats["file_types"].items():
            st.markdown(f"- {file_type.upper()}ファイル: {count}個")

        # セッション情報
        st.markdown(f"**会話履歴:** {len(st.session_state.messages)}件")
        st.markdown(f"**現在のモード:** {st.session_state.mode}")

        # Retriever設定情報
        if st.session_state.retriever:
            st.markdown(f"**検索設定:** 上位{ct.RETRIEVER_K}件取得")
            st.markdown(f"**チャンクサイズ:** {ct.CHUNK_SIZE}")
            st.markdown(f"**オーバーラップ:** {ct.CHUNK_OVERLAP}")

        st.markdown("---")

        # セッションリセット機能
        if st.button(
            "🔄 セッションリセット", help="会話履歴とキャッシュをクリアします"
        ):
            # セッション状態をクリア
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # キャッシュをクリア
            st.cache_data.clear()
            st.rerun()
