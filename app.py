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
    .stChatMessage [data-testid="stChatMessageAvatarUser"] ~ div button {display: none;}
    [data-testid="stChatMessageContent"] .stActionButtonIcon {display: none;}

    /* 전체 배경 */
    .stApp {background: linear-gradient(135deg, #0d1117 0%, #0f1623 100%);}

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #0d1117 100%);
        border-right: 1px solid #1f2937;
    }

    /* 채팅 입력창 */
    [data-testid="stChatInput"] textarea {
        background-color: #1a2234 !important;
        border: 1px solid #2d3f5c !important;
        border-radius: 16px !important;
        color: #e2e8f0 !important;
        font-size: 15px !important;
    }

    /* 봇 메시지 */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: linear-gradient(135deg, #1a2234 0%, #151e2e 100%);
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #2d3f5c;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    /* 유저 메시지 */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: linear-gradient(135deg, #1a3a5c 0%, #152d4a 100%);
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #2d5a8c;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    /* expander */
    [data-testid="stExpander"] {
        background: #0d1117;
        border: 1px solid #1f2937;
        border-radius: 10px;
        margin-top: 8px;
    }

    /* 통계 카드 */
    .stat-card {
        background: linear-gradient(135deg, #1a2234 0%, #151e2e 100%);
        border: 1px solid #2d3f5c;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 8px;
    }
    .stat-number {
        font-size: 24px;
        font-weight: 700;
        background: linear-gradient(90deg, #60a5fa, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-label {
        font-size: 12px;
        color: #64748b;
        margin-top: 4px;
    }

    /* 사이드바 타이틀 */
    .sidebar-title {
        font-size: 20px;
        font-weight: 700;
        background: linear-gradient(90deg, #60a5fa, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }

    /* 구분선 */
    .custom-divider {
        border: none;
        border-top: 1px solid #1f2937;
        margin: 16px 0;
    }

    /* 메인 타이틀 */
    .main-title {
        font-size: 32px;
        font-weight: 800;
        background: linear-gradient(90deg, #60a5fa, #818cf8, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .main-subtitle {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 24px;
    }

    /* 초기화 버튼 */
    .stButton button {
        background: linear-gradient(135deg, #1e3a5f, #2d4a7a) !important;
        color: #93c5fd !important;
        border: 1px solid #2d5a8c !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #2d4a7a, #3d5a8a) !important;
        border-color: #60a5fa !important;
    }

    /* 스크롤바 */
    ::-webkit-scrollbar {width: 6px;}
    ::-webkit-scrollbar-track {background: #0d1117;}
    ::-webkit-scrollbar-thumb {background: #2d3f5c; border-radius: 3px;}
</style>
""", unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.markdown('<div class="sidebar-title">🤖 Redmine 챗봇</div>', unsafe_allow_html=True)
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    st.markdown("**📊 데이터 현황**")
    st.markdown("""
    <div class="stat-card">
        <div class="stat-number">25,534</div>
        <div class="stat-label">📋 전체 이슈</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">72,518</div>
        <div class="stat-label">💬 전체 댓글</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown("**💡 사용 방법**")
    st.markdown('<p style="color:#64748b; font-size:13px;">Redmine 이슈 데이터를 기반으로 원인과 해결방법을 안내해드립니다.</p>', unsafe_allow_html=True)
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 메인
st.markdown('<div class="main-title">🤖 Redmine Q&A 챗봇</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Redmine 이슈 25,534건 데이터 기반으로 답변해드립니다</div>', unsafe_allow_html=True)

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "안녕하세요! 👋 Redmine 이슈 기반 Q&A 챗봇입니다.\n\n오류 증상이나 문의 내용을 입력하시면 관련 이슈를 찾아 답변드릴게요!"
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
if question := st.chat_input("증상이나 오류를 입력하세요..."):
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("🔍 관련 이슈 검색 중..."):
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