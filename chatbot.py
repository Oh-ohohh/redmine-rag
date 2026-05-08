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

@st.cache_resource
def load_client():
    return Groq(api_key=os.getenv('GROQ_API_KEY'))

model = load_model()
client = load_client()

DB_CONFIG = {
    'host': 'aws-1-ap-northeast-2.pooler.supabase.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres.nsexfujmsfchdwvqjtsy',
    'password': os.getenv('SUPABASE_PASSWORD')
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def search(question, top_k=5, fetch_k=10):
    vector = model.encode(question).tolist()
    
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT issue_id, subject, description, created_on
        FROM redmine_issues
        ORDER BY embedding <-> %s::vector
        LIMIT %s
    """, (str(vector), fetch_k))
    issues_raw = cursor.fetchall()
    issues = sorted(issues_raw, key=lambda x: x[3] or '', reverse=True)[:top_k]
    
    cursor.execute("""
        SELECT j.issue_id, j.notes, j.created_on
        FROM redmine_journals j
        ORDER BY j.embedding <-> %s::vector
        LIMIT %s
    """, (str(vector), fetch_k))
    journals_raw = cursor.fetchall()
    journals = sorted(journals_raw, key=lambda x: x[2] or '', reverse=True)[:top_k]
    
    conn.close()
    return issues, journals

def ask(question):
    issues, journals = search(question)
    
    issue_text = "\n".join([
        f"[이슈 #{i[0]}] {i[1]} ({i[3]})\n{i[2][:500] if i[2] else ''}"
        for i in issues
    ])
    
    journal_text = "\n".join([
        f"[이슈 #{j[0]} 답변] ({j[2]})\n{j[1][:500] if j[1] else ''}"
        for j in journals
    ])
    
    prompt = f"""당신은 팜소프트 Redmine 이슈 관리 시스템의 전문 Q&A 챗봇입니다.
아래 Redmine 이슈 데이터를 분석하여 질문에 답변해주세요.

## 답변 규칙
1. 반드시 한국어로 답변하세요
2. 관련 이슈 번호를 반드시 언급하세요 (예: 이슈 #1234 참고)
3. 답변은 아래 형식으로 작성하세요:
   - 📌 원인: 문제의 원인을 간단히 설명
   - 🔧 해결방법: 단계별로 명확하게 설명
   - 📎 참고 이슈: 관련 이슈 번호 목록
4. 비슷한 사례가 있으면 해당 이슈도 함께 언급하세요
5. 데이터에 없는 내용은 "관련 이슈를 찾지 못했습니다"라고 하세요
6. 답변은 구체적이고 실용적으로 작성하세요
7. 최신 이슈를 우선으로 참고하세요

## 관련 이슈 데이터
{issue_text}

## 관련 답변 데이터
{journal_text}

## 질문
{question}

## 답변
위 데이터를 바탕으로 실용적인 답변을 작성해주세요:"""
    
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {
                'role': 'system',
                'content': '당신은 Redmine 이슈 데이터 전문가입니다. 항상 한국어로 답변하고, 이슈 번호를 언급하며, 원인과 해결방법을 구조적으로 설명합니다.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        temperature=0.3
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