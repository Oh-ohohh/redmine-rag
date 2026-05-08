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
    SELECT journal_id, notes 
    FROM redmine_journals 
    WHERE embedding IS NULL
""")
rows = cursor.fetchall()
total = len(rows)
print(f"임베딩할 댓글: {total}개")

batch_size = 32
for i in range(0, total, batch_size):
    batch = rows[i:i+batch_size]
    
    texts = [row[1][:500] if row[1] else '' for row in batch]
    ids = [row[0] for row in batch]

    vectors = model.encode(texts)

    for journal_id, vector in zip(ids, vectors):
        cursor.execute("""
            UPDATE redmine_journals 
            SET embedding = %s 
            WHERE journal_id = %s
        """, (vector.tolist(), journal_id))

    conn.commit()
    done = min(i + batch_size, total)
    percent = round(done / total * 100, 1)
    print(f"진행: {done}/{total}개 ({percent}%) 완료")

print("댓글 임베딩 완료!")
conn.close()