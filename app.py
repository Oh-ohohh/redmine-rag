import streamlit as st
from chatbot import ask

st.set_page_config(
    page_title="Redmine Q&A 챗봇",
    page_icon="🤖",
    layout="wide"
)

with st.sidebar:
    st.title("🤖 Redmine 챗봇")
    st.markdown("---")
    st.markdown("**데이터 현황**")
    st.metric("이슈", "25,534개")
    st.metric("댓글", "72,518개")
    st.markdown("---")
    st.markdown("**사용 방법**")
    st.markdown("질문을 입력하면 Redmine 이슈를 기반으로 답변해드려요")
    st.markdown("---")
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

st.title("Redmine Q&A 챗봇")
st.caption("Redmine 이슈 데이터 기반으로 답변해드립니다")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "안녕하세요! Redmine 이슈 기반 Q&A 챗봇입니다. 궁금한 점을 질문해주세요!"
    })

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "issues" in msg:
            with st.expander("참조 이슈 보기"):
                for issue in msg["issues"]:
                    st.markdown(f"- **이슈 #{issue[0]}**: {issue[1]}")

if question := st.chat_input("질문을 입력하세요..."):
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Redmine 이슈 검색 중..."):
            answer, issues = ask(question)
        st.markdown(answer)
        with st.expander("참조 이슈 보기"):
            for issue in issues:
                st.markdown(f"- **이슈 #{issue[0]}**: {issue[1]}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "issues": issues
    })