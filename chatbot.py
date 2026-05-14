from sentence_transformers import SentenceTransformer
import psycopg2
from groq import Groq
from dotenv import load_dotenv
import os
import streamlit as st

load_dotenv()

@st.cache_resource
def load_model():
    print("모델 로딩 중...")
    return SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

model = load_model()

DB_CONFIG = {
    'host': 'aws-1-ap-northeast-2.pooler.supabase.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres.nsexfujmsfchdwvqjtsy',
    'password': st.secrets.get("SUPABASE_PASSWORD") if hasattr(st, 'secrets') else os.getenv('SUPABASE_PASSWORD')
}

def get_client():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except:
        api_key = os.getenv('GROQ_API_KEY')
    return Groq(api_key=api_key)

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def search(question, fetch_k=20):
    vector = model.encode(question).tolist()
    keywords = [w for w in question.split() if len(w) >= 2]

    conn = get_conn()
    cursor = conn.cursor()

    issues = []

    if keywords:
        # 키워드가 있으면 반드시 키워드 포함된 것만 검색
        score_cases = " + ".join([
            f"(CASE WHEN subject ILIKE '%%{k}%%' OR description ILIKE '%%{k}%%' THEN 1 ELSE 0 END)"
            for k in keywords
        ])
        # 모든 키워드 중 하나라도 포함된 것만
        or_condition = " OR ".join([
            f"(subject ILIKE '%%{k}%%' OR description ILIKE '%%{k}%%')"
            for k in keywords
        ])
        try:
            cursor.execute(f"""
                SELECT issue_id, subject, description, created_on,
                       ({score_cases}) AS score
                FROM redmine_issues
                WHERE {or_condition}
                ORDER BY score DESC, created_on DESC
                LIMIT %s
            """, (fetch_k,))
            issues = [row[:4] for row in cursor.fetchall()]
        except Exception as e:
            print(f"키워드 검색 오류: {e}")
            issues = []

    # 키워드 검색 결과 없으면 벡터 검색으로 폴백
    if not issues:
        cursor.execute("""
            SELECT issue_id, subject, description, created_on,
                   embedding <-> %s::vector AS distance
            FROM redmine_issues
            ORDER BY distance
            LIMIT %s
        """, (str(vector), fetch_k))
        issues = [r[:4] for r in cursor.fetchall()]

    issues = issues[:10]

    # 유사도 점수 (관련성 판단용)
    cursor.execute("""
        SELECT embedding <-> %s::vector AS distance
        FROM redmine_issues
        ORDER BY distance
        LIMIT 1
    """, (str(vector),))
    best_distance = cursor.fetchone()[0] if cursor.rowcount else 999

    # 찾은 이슈의 저널만 가져오기
    issue_ids = [i[0] for i in issues]
    cursor.execute("""
        SELECT j.issue_id, j.notes, j.created_on
        FROM redmine_journals j
        WHERE j.issue_id = ANY(%s)
        AND j.notes IS NOT NULL
        AND j.notes != ''
        ORDER BY j.created_on DESC
    """, (issue_ids,))
    journals = cursor.fetchall()

    conn.close()
    return issues, journals, best_distance

def ask(question):
    client = get_client()
    issues, journals, best_distance = search(question)

    if not issues:
        return "죄송합니다. 질문과 관련된 이슈를 찾지 못했습니다. 😅\n\n좀 더 구체적으로 입력해주시면 정확한 답변을 드릴 수 있어요!\n\n**예시:**\n- 안정성시험 일지가 이전개정으로 붙는 오류\n- 산출물 보는 방법\n- 시험성적서 출력이 안됨", []

    issue_text = "\n".join([
        f"[이슈 #{i[0]}] {'⭐ 가장 관련성 높은 이슈' if idx == 0 else f'[{idx+1}순위]'} {i[1]} ({i[3]})\n{i[2][:800] if i[2] else ''}"
        for idx, i in enumerate(issues)
    ])

    top_issue_ids = [i[0] for i in issues[:3]]
    journal_text = ""
    for issue_id in top_issue_ids:
        issue_journals = [j for j in journals if j[0] == issue_id]
        if issue_journals:
            journal_text += f"\n=== 이슈 #{issue_id} 댓글 ===\n"
            for j in issue_journals[:5]:
                journal_text += f"({j[2]})\n{j[1][:800] if j[1] else ''}\n\n"

    for j in journals:
        if j[0] not in top_issue_ids:
            journal_text += f"[이슈 #{j[0]} 답변] ({j[2]})\n{j[1][:300] if j[1] else ''}\n"

    prompt = f"""당신은 팜소프트 Redmine 이슈 관리 시스템의 전문 Q&A 챗봇입니다.

## 답변 규칙
1. 반드시 한국어로 답변하세요
2. 질문이 짧거나 구어체여도 의도를 파악해서 답변하세요
3. ⭐ 표시된 이슈를 최우선으로 참고하세요
4. 관련 이슈 번호를 반드시 언급하세요
5. 답변은 아래 형식으로 작성하세요:
   - 📌 원인: 문제가 왜 발생했는지 최대한 상세하게
   - 🔧 해결방법:
     * 단계별로 번호 매겨서 설명
     * 각 단계마다 구체적인 명령어나 설정값 포함
     * 주의사항도 함께 작성
   - 📎 참고 이슈: 반드시 위 '관련 이슈 데이터'에 있는 이슈 번호만 언급하세요
   - 💡 추가 팁: 재발 방지 방법이나 관련 주의사항
6. 데이터와 관련 없는 질문이면 "관련 이슈를 찾지 못했습니다. 더 구체적으로 질문해주세요" 라고 하세요
7. 답변은 최대한 구체적으로, 실무자가 바로 적용할 수 있게 작성하세요
8. 해결방법이 여러 개면 전부 나열하세요
9. 이슈에 나온 실제 설정값, 경로, 명령어는 그대로 인용하세요

## 관련 이슈 데이터
{issue_text}

## 관련 답변 데이터
{journal_text}

## 질문
{question}

## 답변
⭐ 표시된 이슈를 최우선으로 참고하여 실무자가 바로 따라할 수 있도록 상세하게 작성해주세요:"""

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {
                'role': 'system',
                'content': '당신은 팜소프트 Redmine 이슈 관리 시스템의 전문 Q&A 챗봇입니다. 사용자가 짧거나 구어체로 질문해도 의도를 파악하여 관련 이슈를 찾아 답변하세요. 항상 한국어로 답변하고 ⭐ 표시된 이슈를 최우선으로 참고하세요.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        temperature=0.3,
        max_tokens=2048
    )
    return response.choices[0].message.content, issues

if __name__ == "__main__":
    print("Redmine 챗봇 테스트")
    print("종료하려면 'quit' 입력\n")
    while True:
        q = input("질문: ")
        if q.lower() == 'quit':
            break
        answer, issues = ask(q)
        print(f"\n답변:\n{answer}")
        print(f"\n참조 이슈: {[i[0] for i in issues]}\n")
        print("-" * 50)