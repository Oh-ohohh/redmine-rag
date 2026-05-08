from sshtunnel import SSHTunnelForwarder
import pymysql

with SSHTunnelForwarder(
    ('115.144.114.82', 22000),
    ssh_username='pharmsoft',
    ssh_password='soft6636',
    remote_bind_address=('127.0.0.1', 3306)
) as tunnel:
    conn = pymysql.connect(
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        user='root',
        password='soft6636',
        database='bitnami_redmine'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM issues")
    result = cursor.fetchone()
    print(f"Redmine 이슈 총 개수: {result[0]}개")
    conn.close()