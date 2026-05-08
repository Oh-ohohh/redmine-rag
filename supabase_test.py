import psycopg2

conn = psycopg2.connect(
    host='aws-1-ap-northeast-2.pooler.supabase.com',
    port=5432,
    database='postgres',
    user='postgres.nsexfujmsfchdwvqjtsy',
    password='wlfjd223!@Q'
)

cursor = conn.cursor()
cursor.execute("SELECT version();")
result = cursor.fetchone()
print(f"연결 성공! PostgreSQL 버전: {result[0]}")
conn.close()