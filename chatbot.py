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
    return SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")


model = load_model()


DB_CONFIG = {
    "host": "aws-1-ap-northeast-2.pooler.supabase.com",
    "port": 5432,
    "database": "postgres",
    "user": "postgres.nsexfujmsfchdwvqjtsy",
    "password": st.secrets.get("SUPABASE_PASSWORD")
    if hasattr(st, "secrets")
    else os.getenv("SUPABASE_PASSWORD"),
}


def get_client():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY가 설정되어 있지 않습니다.")

    return Groq(api_key=api_key)


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def search(question, fetch_k=30):
    """
    검색 개선 방향:
    1. 벡터 검색은 항상 수행
    2. 키워드 검색도 보조로 수행
    3. 두 결과를 병합
    4. 키워드만 맞는 이슈가 과도하게 우선되지 않도록 벡터 검색에 더 높은 점수 부여
    """

    vector = model.encode(question).tolist()
    keywords = [w for w in question.split() if len(w) >= 2]

    conn = get_conn()
    cursor = conn.cursor()

    merged = {}

    try:
        # =========================
        # 1. 벡터 검색 항상 수행
        # =========================
        cursor.execute(
            """
            SELECT issue_id, subject, description, created_on,
                   embedding <-> %s::vector AS distance
            FROM redmine_issues
            WHERE embedding IS NOT NULL
            ORDER BY distance
            LIMIT %s
            """,
            (str(vector), fetch_k),
        )

        vector_rows = cursor.fetchall()

        for rank, row in enumerate(vector_rows, start=1):
            issue_id, subject, description, created_on, distance = row

            merged[issue_id] = {
                "issue_id": issue_id,
                "subject": subject,
                "description": description,
                "created_on": created_on,
                "vector_rank": rank,
                "vector_distance": float(distance),
                "keyword_score": 0,
                "keyword_rank": None,
                "final_score": 0,
            }

        best_distance = vector_rows[0][4] if vector_rows else 999

        # =========================
        # 2. 키워드 검색 보조 수행
        # =========================
        if keywords:
            patterns = [f"%{k}%" for k in keywords]

            cursor.execute(
                """
                SELECT issue_id, subject, description, created_on
                FROM redmine_issues
                WHERE subject ILIKE ANY(%s)
                   OR description ILIKE ANY(%s)
                ORDER BY created_on DESC
                LIMIT %s
                """,
                (patterns, patterns, fetch_k),
            )

            keyword_rows = cursor.fetchall()

            for rank, row in enumerate(keyword_rows, start=1):
                issue_id, subject, description, created_on = row

                subject_text = subject or ""
                description_text = description or ""

                keyword_score = 0

                for k in keywords:
                    if k.lower() in subject_text.lower():
                        keyword_score += 3
                    if k.lower() in description_text.lower():
                        keyword_score += 1

                if issue_id not in merged:
                    merged[issue_id] = {
                        "issue_id": issue_id,
                        "subject": subject,
                        "description": description,
                        "created_on": created_on,
                        "vector_rank": None,
                        "vector_distance": None,
                        "keyword_score": keyword_score,
                        "keyword_rank": rank,
                        "final_score": 0,
                    }
                else:
                    merged[issue_id]["keyword_score"] = keyword_score
                    merged[issue_id]["keyword_rank"] = rank

        # =========================
        # 3. 점수 계산
        # =========================
        for issue in merged.values():
            score = 0

            # 벡터 검색 순위 가중치
            # 하드코딩 불용어 없이 의미 기반 검색을 메인으로 사용
            if issue["vector_rank"] is not None:
                score += 100 / (issue["vector_rank"] + 10)

            # 키워드 검색은 보조 점수
            if issue["keyword_score"]:
                score += min(issue["keyword_score"], 10)

            # 키워드 검색 순위 보조 가중치
            if issue["keyword_rank"] is not None:
                score += 20 / (issue["keyword_rank"] + 10)

            issue["final_score"] = score

        sorted_issues = sorted(
            merged.values(),
            key=lambda x: x["final_score"],
            reverse=True,
        )

        # 최종 10개만 사용
        selected = sorted_issues[:10]

        issues = [
            (
                i["issue_id"],
                i["subject"],
                i["description"],
                i["created_on"],
            )
            for i in selected
        ]

        # =========================
        # 4. 저널 조회
        # =========================
        issue_ids = [i[0] for i in issues]

        if not issue_ids:
            conn.close()
            return [], [], best_distance

        cursor.execute(
            """
            SELECT j.issue_id, j.notes, j.created_on
            FROM redmine_journals j
            WHERE j.issue_id = ANY(%s)
              AND j.notes IS NOT NULL
              AND j.notes != ''
            ORDER BY j.created_on DESC
            """,
            (issue_ids,),
        )

        journals = cursor.fetchall()

        conn.close()
        return issues, journals, best_distance

    except Exception as e:
        conn.close()
        print(f"검색 오류: {e}")
        return [], [], 999


def ask(question):
    client = get_client()
    issues, journals, best_distance = search(question)

    if not issues:
        return (
            "죄송합니다. 질문과 관련된 이슈를 찾지 못했습니다. 😅\n\n"
            "좀 더 구체적으로 입력해주시면 정확한 답변을 드릴 수 있어요!\n\n"
            "**예시:**\n"
            "- 안정성시험 일지가 이전개정으로 붙는 오류\n"
            "- 산출물 보는 방법\n"
            "- 시험성적서 출력이 안됨",
            [],
        )

    # =========================
    # 프롬프트 길이 축소
    # 기존 800자 → 400자
    # =========================
    issue_text = "\n".join(
        [
            f"[이슈 #{i[0]}] "
            f"{'⭐ 가장 관련성 높은 이슈' if idx == 0 else f'[{idx + 1}순위]'} "
            f"{i[1]} ({i[3]})\n"
            f"{i[2][:400] if i[2] else ''}"
            for idx, i in enumerate(issues)
        ]
    )

    top_issue_ids = [i[0] for i in issues[:3]]

    journal_text = ""

    # 상위 3개 이슈 댓글만 상세 반영
    for issue_id in top_issue_ids:
        issue_journals = [j for j in journals if j[0] == issue_id]

        if issue_journals:
            journal_text += f"\n=== 이슈 #{issue_id} 댓글 ===\n"

            # 기존 5개 → 3개
            # 기존 800자 → 400자
            for j in issue_journals[:3]:
                journal_text += (
                    f"({j[2]})\n"
                    f"{j[1][:400] if j[1] else ''}\n\n"
                )

    # 나머지 이슈 댓글은 너무 길어지지 않게 200자만 반영
    for j in journals:
        if j[0] not in top_issue_ids:
            journal_text += (
                f"[이슈 #{j[0]} 답변] ({j[2]})\n"
                f"{j[1][:200] if j[1] else ''}\n"
            )

    prompt = f"""당신은 팜소프트 Redmine 이슈 관리 시스템의 전문 Q&A 챗봇입니다.

## 답변 규칙
1. 반드시 한국어로 답변하세요.
2. 질문이 짧거나 구어체여도 의도를 파악해서 답변하세요.
3. ⭐ 표시된 이슈를 최우선으로 참고하세요.
4. 관련 이슈 번호를 반드시 언급하세요.
5. 답변은 아래 형식으로 작성하세요:
   - 📌 원인: 문제가 왜 발생했는지 작성
   - 🔧 해결방법:
     * 단계별로 번호 매겨서 설명
     * 실제 이슈에 나온 명령어, 설정값, 메뉴명이 있으면 그대로 작성
   - 📎 참고 이슈: 반드시 위 '관련 이슈 데이터'에 있는 이슈 번호만 언급
   - 💡 추가 팁: 재발 방지 방법이나 관련 주의사항
6. 데이터와 관련 없는 질문이면 "관련 이슈를 찾지 못했습니다. 더 구체적으로 질문해주세요"라고 하세요.
7. 이슈 데이터에 없는 내용은 추측하지 마세요.
8. 원인이나 해결방법이 명확하지 않으면 "이슈 내 확인 불가" 또는 "추가 확인 필요"라고 작성하세요.

## 관련 이슈 데이터
{issue_text}

## 관련 답변 데이터
{journal_text}

## 질문
{question}

## 답변
⭐ 표시된 이슈를 최우선으로 참고하여 실무자가 바로 따라할 수 있도록 작성해주세요:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 팜소프트 Redmine 이슈 관리 시스템의 전문 Q&A 챗봇입니다. "
                        "반드시 한국어로 답변하고, 제공된 이슈 데이터 안에서만 답변하세요. "
                        "없는 내용은 추측하지 마세요."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.3,
            max_tokens=1200,
        )

        return response.choices[0].message.content, issues

    except Exception as e:
        error_type = type(e).__name__
        status_code = getattr(e, "status_code", None)

        response_text = ""
        response_obj = getattr(e, "response", None)

        if response_obj is not None:
            try:
                response_text = response_obj.text
            except Exception:
                response_text = ""

        error_message = (
            "Groq API 호출 중 오류가 발생했습니다.\n\n"
            f"- 오류 타입: {error_type}\n"
            f"- 상태 코드: {status_code}\n"
        )

        if response_text:
            error_message += f"- 응답 내용: {response_text[:500]}\n"

        error_message += (
            "\n확인 필요 사항:\n"
            "1. Streamlit secrets에 GROQ_API_KEY가 정상 등록되어 있는지 확인\n"
            "2. Groq 모델명 llama-3.3-70b-versatile 사용 가능 여부 확인\n"
            "3. 사용량 제한 또는 Rate Limit 초과 여부 확인\n"
            "4. 요청 프롬프트 길이 초과 여부 확인"
        )

        return error_message, issues


if __name__ == "__main__":
    print("Redmine 챗봇 테스트")
    print("종료하려면 'quit' 입력\n")

    while True:
        q = input("질문: ")

        if q.lower() == "quit":
            break

        answer, issues = ask(q)

        print(f"\n답변:\n{answer}")
        print(f"\n참조 이슈: {[i[0] for i in issues]}\n")
        print("-" * 50)