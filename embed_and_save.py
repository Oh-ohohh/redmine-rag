from sentence_transformers import SentenceTransformer
import psycopg2

print("모델 로딩 중...")
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

conn = psycopg2.connect(
    host='aws-1-ap-northeast-2.pooler.supabase.com',
    port=5432,
    database='postgres',
    user='postgres.nsexfujmsfchdwvqjtsy',
    password='wlfjd223!@Q'
)
cursor = conn.cursor()

# 벡터 없는 이슈 가져오기
cursor.execute("""
    SELECT id, chunk_text FROM redmine_issues 
    WHERE embedding IS NULL
""")
rows = cursor.fetchall()
print(f"벡터 변환할 이슈: {len(rows)}개")

for i, (id, chunk_text) in enumerate(rows):
    vector = model.encode(chunk_text).tolist()
    cursor.execute("""
        UPDATE redmine_issues 
        SET embedding = %s 
        WHERE id = %s
    """, (str(vector), id))
    
    if (i+1) % 10 == 0:
        print(f"{i+1}개 완료...")

conn.commit()
print("전체 완료!")
conn.close()