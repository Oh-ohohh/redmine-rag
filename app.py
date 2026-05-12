import streamlit as st
from chatbot import ask

st.set_page_config(
    page_title="Redmine Q&A 챗봇",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stToolbarActions"] {display: none;}
    a[href*="github"] {display: none !important;}
    [data-testid="baseButton-headerNoPadding"] {display: none;}
    
    /* 사용자 메시지 밑 이상한 거 제거 */
    .stChatMessage [data-testid="stChatMessageAvatarUser"] ~ div button {display: none;}
    [data-testid="stChatMessageContent"] .stActionButtonIcon {display: none;}

    /* 전체 배경 */
    .stApp {background-color: #0f1117;}
    
    /* 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #1a1d27;
        border-right: 1px solid #2d3148;
    }

    /* 채팅 입력창 */
    [data-testid="stChatInput"] {
        background-color: #1a1d27;
        border: 1px solid #2d3148;
        border-radius: 12px;
    }

    /* 봇 메시지 */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background-color: #1a1d27;
        border-radius: 12px;
        padding: 12px;
        border: 1px solid #2d3148;
        margin-bottom: 8px;
    }

    /* 유저 메시지 */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background-color: #1e2d4a;
        border-radius: 12px;
        padding: 12px;
        border: 1px solid #2d4a7a;
        margin-bottom: 8px;
    }

    /* expander 스타일 */
    [data-testid="stExpander"] {
        background-color: #12151f;
        border: 1px solid #2d3148;
        border-radius: 8px;
    }

    /* 제목 */
    h1 {color: #e0e6f0 !important;}
    
    /* 메트릭 */
    [data-testid="stMetric"] {
        background-color: #12151f;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #2d3148;
    }
</style>
""", unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.markdown("## 🤖 Redmine 챗봇")
    st.markdown("---")
    st.markdown("**📊 데이터 현황**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("이슈", "25,534")
    with col2:
        st.metric("댓글", "72,518")
    st.markdown("---")
    st.markdown("**💡 사용 방법**")
    st.markdown("Redmine 이슈 데이터를 기반으로 답변드립니다.")
    st.markdown("---")
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 메인
st.markdown("# 🤖 Redmine Q&A 챗봇")
st.markdown("Redmine 이슈 데이터 기반으로 답변해드립니다")
st.markdown("---")

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "안녕하세요! Redmine 이슈 기반 Q&A 챗봇입니다. 궁금한 점을 질문해주세요! 😊"
    })

# 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "issues" in msg and msg["issues"]:
            with st.expander("📎 참조 이슈 보기"):
                for issue in msg["issues"]:
                    st.markdown(f"- **이슈 #{issue[0]}**: {issue[1]}")

# 입력
if question := st.chat_input("질문을 입력하세요..."):
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("🔍 Redmine 이슈 검색 중..."):
            answer, issues = ask(question)
        st.markdown(answer)
        if issues:
            with st.expander("📎 참조 이슈 보기"):
                for issue in issues:
                    st.markdown(f"- **이슈 #{issue[0]}**: {issue[1]}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "issues": issues
    })