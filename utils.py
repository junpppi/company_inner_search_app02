"""
このファイルは、画面表示以外の様々な関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import os
from dotenv import load_dotenv
import streamlit as st
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import constants as ct


############################################################
# 設定関連
############################################################
# 「.env」ファイルで定義した環境変数の読み込み
load_dotenv()


############################################################
# 関数定義
############################################################

def get_source_icon(source):
    """
    メッセージと一緒に表示するアイコンの種類を取得

    Args:
        source: 参照元のありか

    Returns:
        メッセージと一緒に表示するアイコンの種類
    """
    # 参照元がWebページの場合とファイルの場合で、取得するアイコンの種類を変える
    if source.startswith("http"):
        icon = ct.LINK_SOURCE_ICON
    else:
        icon = ct.DOC_SOURCE_ICON
    
    return icon


def build_error_message(message):
    """
    エラーメッセージと管理者問い合わせテンプレートの連結

    Args:
        message: 画面上に表示するエラーメッセージ

    Returns:
        エラーメッセージと管理者問い合わせテンプレートの連結テキスト
    """
    return "\n".join([message, ct.COMMON_ERROR_MESSAGE])


def get_llm_response(chat_message):
    """
    LLMからの回答取得
    """

    # LLMのオブジェクトを用意
    llm = ChatOpenAI(model_name=ct.MODEL, temperature=ct.TEMPERATURE)

    # 会話履歴なしでも理解できる入力を生成するプロンプト
    question_generator_template = ct.SYSTEM_PROMPT_CREATE_INDEPENDENT_TEXT
    question_generator_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", question_generator_template),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

    # モード分岐
    if st.session_state.mode == ct.ANSWER_MODE_1:
        question_answer_template = ct.SYSTEM_PROMPT_DOC_SEARCH
    else:
        question_answer_template = ct.SYSTEM_PROMPT_INQUIRY

    question_answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", question_answer_template),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

    # Retriever
    history_aware_retriever = create_history_aware_retriever(
        llm, st.session_state.retriever, question_generator_prompt
    )

    # Chain作成
    question_answer_chain = create_stuff_documents_chain(llm, question_answer_prompt)
    chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    # 実行
    llm_response = chain.invoke(
       {"input": chat_message, "chat_history": st.session_state.chat_history}
    )
    ctx = llm_response.get("context") or []
    print("[DEBUG] context_len =", len(ctx))
    # 追加デバッグ（先頭ドキュメントの中身確認）
    if len(ctx) > 0:
        top = ctx[0]
        top_source = (top.metadata.get("source") if hasattr(top, "metadata") else None)
        top_text = (top.page_content if hasattr(top, "page_content") else "")
        print("[DEBUG] top_source =", top_source)
        print("[DEBUG] top_text_len =", len(top_text))
        print("[DEBUG] top_text_head =", top_text[:120].replace("\n", " "))
    else:
        print("[DEBUG] top_source = (none)")
    # print("[DEBUG]", st.session_state.mode, "context_len=", len(ctx))
    # if ctx:
    #     d0 = ctx[0]
    #     src = d0.metadata.get("source", "NO_SOURCE")
    #     txt = d0.page_content or ""
    #     print("[DEBUG] top_source =", src)
    #     print("[DEBUG] top_text_len =", len(txt))
    #     print("[DEBUG] top_text_head =", txt[:120].replace("\n", " "))
    # else:
    #     print("[DEBUG] no context returned")
    
    # 会話履歴更新（ここ重要）
    from langchain.schema import AIMessage
    st.session_state.chat_history.extend([
        HumanMessage(content=chat_message),
        AIMessage(content=llm_response["answer"])

    ])

    return llm_response