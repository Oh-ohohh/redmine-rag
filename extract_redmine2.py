from sshtunnel import SSHTunnelForwarder
import pymysql
import psycopg2

with SSHTunnelForwarder(
    ('115.144.114.82', 22000),
    ssh_username='pharmsoft',
    ssh_password='soft6636',
    remote_bind_address=('127.0.0.1', 3306)
) as tunnel:

    redmine = pymysql.connect(
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        user='root',
        password='soft6636',
        database='bitnami_redmine',
        charset='utf8mb4'
    )

    supa = psycopg2.connect(
        host='aws-1-ap-northeast-2.pooler.supabase.com',
        port=5432,
        database='postgres',
        user='postgres.nsexfujmsfchdwvqjtsy',
        password='wlfjd223!@Q'
    )

    rc = redmine.cursor()
    sc = supa.cursor()

    rc.execute("""
        SELECT id, subject, description, done_ratio, created_on
        FROM issues
        WHERE done_ratio >= 70
        AND description IS NOT NULL
    """)

    issues = rc.fetchall()
    print(f"이슈 {len(issues)}개 발견")

    for i, issue in enumerate(issues):
        issue_id, subject, description, done_ratio, created_on = issue

        # 인코딩 처리
        subject = subject.encode('utf-8', errors='ignore').decode('utf-8') if subject else ''
        description = description.encode('utf-8', errors='ignore').decode('utf-8') if description else ''

        sc.execute("""
            INSERT INTO redmine_issues
            (issue_id, subject, description, done_ratio, created_on)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (issue_id) DO NOTHING
        """, (issue_id, subject, description, done_ratio, created_on))

        # 댓글 뽑기
        rc.execute("""
            SELECT id, notes, created_on
            FROM journals
            WHERE journalized_id = %s
            AND notes IS NOT NULL
            AND notes != ''
        """, (issue_id,))

        journals = rc.fetchall()

        for journal in journals:
            journal_id, notes, j_created_on = journal
            notes = notes.encode('utf-8', errors='ignore').decode('utf-8') if notes else ''

            sc.execute("""
                INSERT INTO redmine_journals
                (journal_id, issue_id, notes, created_on)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (journal_id) DO NOTHING
            """, (journal_id, issue_id, notes, j_created_on))

        # 100개마다 저장 + 진행상황 출력
        if (i+1) % 100 == 0:
            supa.commit()
            print(f"{i+1}/{len(issues)}개 완료...")

    supa.commit()
    print(f"전체 완료! 이슈 {len(issues)}개 저장됨")

    redmine.close()
    supa.close()