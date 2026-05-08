from sshtunnel import SSHTunnelForwarder
import pymysql
import psycopg2
import re

# SSH 터널로 Redmine 연결
with SSHTunnelForwarder(
    ('115.144.114.82', 22000),
    ssh_username='pharmsoft',
    ssh_password='soft6636',
    remote_bind_address=('127.0.0.1', 3306)
) as tunnel:

    # Redmine DB 접속
    redmine_conn = pymysql.connect(
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        user='root',
        password='soft6636',
        database='bitnami_redmine',
        charset='utf8mb4'
    )

    # Supabase 접속
    supa_conn = psycopg2.connect(
        host='aws-1-ap-northeast-2.pooler.supabase.com',
        port=5432,
        database='postgres',
        user='postgres.nsexfujmsfchdwvqjtsy',
        password='wlfjd223!@Q'
    )

    cursor = redmine_conn.cursor()
    supa_cursor = supa_conn.cursor()

    # 이슈 데이터 뽑기
    cursor.execute("""
        SELECT i.id, i.subject, i.description
        FROM issues i
        WHERE i.description IS NOT NULL
        LIMIT 100
    """)

    rows = cursor.fetchall()
    count = 0

    for row in rows:
        issue_id, subject, description = row

        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', str(description))
        chunk_text = f"제목: {subject}\n내용: {clean_text[:500]}"

        # Supabase에 저장
        supa_cursor.execute("""
            INSERT INTO redmine_issues 
            (issue_id, subject, description, chunk_text)
            VALUES (%s, %s, %s, %s)
        """, (issue_id, subject, description, chunk_text))

        count += 1

    supa_conn.commit()
    print(f"완료! {count}개 이슈 저장됨")

    redmine_conn.close()
    supa_conn.close()