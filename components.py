"""
このファイルは、画面表示に特化した関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import streamlit as st
import utils
import constants as ct


############################################################
# 関数定義
############################################################

def display_app_title():
    """
    タイトル表示
    """
    st.markdown(f"<h2 style='text-align:center'>{ct.APP_NAME}</h2>", unsafe_allow_html=True)


def display_select_mode():
    """
    回答モードのラジオボタンを表示
    """

    # 回答モードを選択する用のラジオボタンを表示
    st.session_state.mode = st.radio(
        "利用目的",
        options=[ct.ANSWER_MODE_1, ct.ANSWER_MODE_2],
        index=0,
        key="mode_radio",
    )

# PDFのときだけ「（ページNo.X）」を付けた表示文字列を返す関数
def _format_source_with_page(document):
    """
    document.metadata["source"] と document.metadata["page"] から
    PDFのときだけ「（ページNo.X）」を付けた表示文字列を返す
    """
    src = document.metadata.get("source", "")
    if not src:
        return ""

    # PDF以外はページを出さない
    if not str(src).lower().endswith(".pdf"):
        return str(src)

    page = document.metadata.get("page")
    if page is None:
        return str(src)

    # 0始まり対策
    try:
        page_no = int(page) + 1
    except Exception:
        return str(src)

    return f"{src}（ページNo.{page_no}）"


def display_initial_ai_message():
    """
    AIメッセージの初期表示（挨拶のみ）
    """
    with st.chat_message("assistant"):
        st.success(
            "こんにちは。私は社内文書の情報をもとに回答する生成AIチャットボットです。"
            "サイドバーで利用目的を選択し、画面下部のチャット欄からメッセージを送信してください。"
        )

def display_search_llm_response(llm_response):
    """
    「社内文書検索」モードにおけるLLMレスポンスを表示
    """
    display_data = {
        "mode": ct.ANSWER_MODE_1,
        "answer": llm_response.get("answer", "")
    }

    context_docs = llm_response.get("context") or []
    answer_text = llm_response.get("answer", "")

    # まず回答文
    st.markdown(answer_text)

    # 該当資料なし / context無し → 参照元は出さない
    if (not context_docs) or (answer_text == ct.NO_DOC_MATCH_ANSWER):
        display_data["no_file_path_flg"] = True
        return display_data

    # 参照元の表示
    st.divider()
    st.markdown("##### 情報源")

    items = []  # (label, src_path)
    for d in context_docs:
        src = ""
        try:
            src = d.metadata.get("source", "")
        except Exception:
            src = ""

        if not src:
            continue

        label = _format_source_with_page(d)  # ★PDFだけページ付ける
        if not label:
            continue

        items.append((label, src))

    # 重複排除（label単位で）
    seen = set()
    items_unique = []
    for label, src in items:
        if label in seen:
            continue
        seen.add(label)
        items_unique.append((label, src))

    if not items_unique:
        display_data["no_file_path_flg"] = True
        return display_data

    display_data["file_info_list"] = [label for label, _ in items_unique]
    for label, src in items_unique:
        icon = utils.get_source_icon(src)
        st.info(label, icon=icon)

    return display_data



def display_mode_description():
    """
    モードごとの説明をサイドバーに表示
    """
    st.markdown("---")

    st.markdown("【「社内文書検索」を選択した場合】")
    st.info("入力内容と関連性が高い社内文書のありかを検索できます。")
    st.code(
        "【入力例】\n社員の育成方針に関するMTGの議事録",
        wrap_lines=True,
        language=None
    )

    st.markdown("【「社内問い合わせ」を選択した場合】")
    st.info("質問・要望に対して、社内文書の情報をもとに回答を得られます。")
    st.code(
        "【入力例】\n人事部に所属している従業員情報を一覧化して",
        wrap_lines=True,
        language=None
    )


def display_conversation_log():
    """
    会話ログの一覧表示
    """
    if "messages" not in st.session_state:
        return

    for message in st.session_state.messages:

        role = message.get("role", "assistant")
        content = message.get("content")

        if role not in ("user", "assistant"):
            role = "assistant"

        with st.chat_message(role):

            # ==============================
            # ユーザー
            # ==============================
            if role == "user":
                st.markdown("" if content is None else str(content))
                continue

            # ==============================
            # assistant：辞書形式
            # ==============================
            if isinstance(content, dict):
                print(type(content))
                print(content)

                mode = content.get("mode")

                # ----------------------------------
                # 社内文書検索
                # ----------------------------------
                if mode == ct.ANSWER_MODE_1:

                    # 該当資料なし
                    if content.get("no_file_path_flg"):
                        st.markdown(content.get("answer", ""))
                        continue

                    # メイン表示
                    st.markdown(content.get("main_message", ""))

                    main_file_path = content.get("main_file_path")
                    if main_file_path:
                        icon = utils.get_source_icon(main_file_path)
                        st.success(main_file_path, icon=icon)

                    # サブ表示
                    if content.get("sub_message") and content.get("sub_choices"):
                        st.markdown(content.get("sub_message"))
                        for sub_choice in content["sub_choices"]:
                            src = sub_choice.get("source")
                            if src:
                                icon = utils.get_source_icon(src)
                                st.info(src, icon=icon)

                    continue

                # ----------------------------------
                # 社内問い合わせ
                # ----------------------------------
                if mode == ct.ANSWER_MODE_2:

                    answer = content.get("answer", "")
                    st.markdown("" if answer is None else str(answer))

                    if content.get("file_info_list"):
                        st.divider()
                        st.markdown(f"##### {content.get('message', '情報源')}")
                        for file_info in content["file_info_list"]:
                            icon = utils.get_source_icon(file_info)
                            st.info(file_info, icon=icon)

                    continue

                # 想定外フォーマット
                st.markdown(str(content))
                continue

            # ==============================
            # assistant：文字列
            # ==============================
            st.markdown("" if content is None else str(content))

def display_contact_llm_response(llm_response):

    """
    「社内問い合わせ」モードにおけるLLMレスポンスを表示

    Args:
        llm_response: LLMからの回答

    Returns:
        LLMからの回答を画面表示用に整形した辞書データ
    """
    # LLMからの回答を表示
    st.markdown(llm_response["answer"])

    # ユーザーの質問・要望に適切な回答を行うための情報が、社内文書のデータベースに存在しなかった場合
    if llm_response["answer"] != ct.INQUIRY_NO_MATCH_ANSWER:
        # 区切り線を表示
        st.divider()

        # 補足メッセージを表示
        message = "情報源"
        st.markdown(f"##### {message}")

        # 参照元のファイルパスの一覧を格納するためのリストを用意
        file_path_list = []
        file_info_list = []

        # LLMが回答生成の参照元として使ったドキュメントの一覧が「context」内のリストの中に入っているため、ループ処理
        for document in llm_response["context"]:
            # ファイルパスを取得
            file_path = document.metadata["source"]
            # ファイルパスの重複は除去
            if file_path in file_path_list:
                continue

            # ページ番号が取得できた場合のみ、ページ番号を表示（ドキュメントによっては取得できない場合がある）
            if "page" in document.metadata and str(file_path).lower().endswith(".pdf"):
                # 0始まり対策して 1始まり表示
                try:
                    page_no = int(document.metadata["page"]) + 1
                    file_info = f"{file_path}（ページNo.{page_no}）"
                except Exception:
                        file_info = f"{file_path}"            
            
            else:
                # 「ファイルパス」のみ
                file_info = f"{file_path}"

            # 参照元のありかに応じて、適したアイコンを取得
            icon = utils.get_source_icon(file_path)
            # ファイル情報を表示
            st.info(file_info, icon=icon)

            # 重複チェック用に、ファイルパスをリストに順次追加
            file_path_list.append(file_path)
            # ファイル情報をリストに順次追加
            file_info_list.append(file_info)

    # 表示用の会話ログに格納するためのデータを用意
    # - 「mode」: モード（「社内文書検索」or「社内問い合わせ」）
    # - 「answer」: LLMからの回答
    # - 「message」: 補足メッセージ
    # - 「file_path_list」: ファイルパスの一覧リスト
    content = {}
    content["mode"] = ct.ANSWER_MODE_2
    content["answer"] = llm_response["answer"]
    # 参照元のドキュメントが取得できた場合のみ
    if llm_response["answer"] != ct.INQUIRY_NO_MATCH_ANSWER:
        content["message"] = message
        content["file_info_list"] = file_info_list

    return content