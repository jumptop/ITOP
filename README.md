# 정보처리기능사 시험 준비 웹 애플리케이션

이 프로젝트는 정보처리기능사 시험을 준비하는 사용자를 위한 웹 애플리케이션입니다.

## 주요 기능

- 문제 풀이 및 자동 채점
- ChatGPT API를 활용한 답변 평가
- 키워드 추출 및 분석
- 사용자 답변 검증

## 기술 스택

- Python
- FastAPI
- OpenAI API
- SQLite

## 설치 방법

1. 저장소 클론
```bash
git clone [repository-url]
cd [repository-name]
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
.\venv\Scripts\activate  # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
`.env` 파일을 생성하고 필요한 환경 변수를 설정합니다.

5. 애플리케이션 실행
```bash
uvicorn app.main:app --reload
```

## API 문서

애플리케이션 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 