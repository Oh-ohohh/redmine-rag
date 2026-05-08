from sentence_transformers import SentenceTransformer

print("모델 로딩 중... (처음에 다운로드라 1~2분 걸려요)")
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

test_text = "로그인 버튼 클릭시 오류 발생"
vector = model.encode(test_text)

print(f"임베딩 완료!")
print(f"벡터 크기: {len(vector)}")
print(f"벡터 앞 5개: {vector[:5]}")