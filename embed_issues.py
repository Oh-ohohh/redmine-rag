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

cursor.execute("""
    SELECT issue_id, subject, description 
    FROM redmine_issues 
    WHERE embedding IS NULL
""")
rows = cursor.fetchall()
total = len(rows)
print(f"임베딩할 이슈: {total}개")

batch_size = 32
for i in range(0, total, batch_size):
    batch = rows[i:i+batch_size]
    
    texts = []
    ids = []
    for issue_id, subject, description in batch:
        text = f"제목: {subject}\n내용: {description[:500]}"
        texts.append(text)
        ids.append(issue_id)

    vectors = model.encode(texts)

    for issue_id, vector in zip(ids, vectors):
        cursor.execute("""
            UPDATE redmine_issues 
            SET embedding = %s 
            WHERE issue_id = %s
        """, (vector.tolist(), issue_id))

    conn.commit()
    done = min(i + batch_size, total)
    percent = round(done / total * 100, 1)
    print(f"진행: {done}/{total}개 ({percent}%) 완료")

print("전체 완료!")
conn.close()