from sentence_transformers import SentenceTransformer
import psycopg2
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

print("모델 로딩 중...")
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

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
    
    # 유사한 이슈 10개 가져오고 최신순 5개
    cursor.execute("""
        SELECT issue_id, subject, description, created_on
        FROM redmine_issues
        ORDER BY embedding <-> %s::vector
        LIMIT %s
    """, (str(vector), fetch_k))
    issues_raw = cursor.fetchall()
    issues = sorted(issues_raw, key=lambda x: x[3] or '', reverse=True)[:top_k]
    
    # 유사한 댓글 10개 가져오고 최신순 5개
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
        f"[이슈 #{i[0]}] {i[1]} ({i[3]})\n{i[2][:300] if i[2] else ''}"
        for i in issues
    ])
    
    journal_text = "\n".join([
        f"[이슈 #{j[0]} 답변] ({j[2]}) {j[1][:300] if j[1] else ''}"
        for j in journals
    ])
    
    prompt = f"""
당신은 Redmine 이슈 데이터를 기반으로 답변하는 챗봇입니다.
아래 관련 데이터를 참고해서 질문에 답해주세요.
최신 데이터를 우선으로 참고하세요.
데이터에 없는 내용은 모른다고 하세요.

[관련 이슈]
{issue_text}

[관련 답변]
{journal_text}

질문: {question}

답변:"""
    
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'user', 'content': prompt}
        ]
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