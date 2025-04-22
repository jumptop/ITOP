# 정보처리기능사 시험 앱 백엔드

정보처리기능사 시험 문제를 출제하고 사용자가 문제를 풀 수 있는 앱의 백엔드 API 서버입니다.

## 기술 스택

- **언어**: Python 3.9+
- **웹 프레임워크**: FastAPI
- **ORM**: SQLAlchemy
- **데이터베이스**: AWS RDS (MySQL)
- **인증**: AWS Cognito
- **텍스트 분석**: AWS Comprehend
- **답변 검증**: OpenAI GPT API
- **마이그레이션**: Alembic

## 주요 기능

1. **사용자 인증**
   - AWS Cognito를 이용한 회원가입, 로그인, 로그아웃
   - 토큰 기반 인증 시스템

2. **문제 관리**
   - 9개 카테고리별 문제 저장 및 조회 (OS, DB, Network, Algorithm, Program, AppTest, AppDefect, BaseSQL, HardSQL)
   - 문제 난이도 설정
   - 관리자 문제 관리 (추가, 수정, 삭제)

3. **답변 검증 및 채점**
   - ChatGPT API를 사용한 답변 유사도 분석
   - 정확한 채점을 위한 자연어 처리

4. **오답 관리**
   - 사용자별 오답 저장
   - AWS Comprehend를 이용한 오답 키워드 추출
   - 유사 문제 추천 시스템

## 키워드 추출 기능 고도화

프로젝트는 두 가지 방식으로 키워드를 추출합니다:

1. **AWS Comprehend**: 자연어 텍스트에서 기본 키워드를 추출합니다.
2. **AWS Bedrock (Claude 3 Sonnet)**: Comprehend로 추출한 키워드를 한번 더 정제하여 더 높은 품질의 전문 키워드만 남깁니다.

이 이중 처리 방식은 '의', '주요', '역할', '무엇' 같은 불필요한 단어는 제외하고 실제 중요한 기술 용어와 개념만 키워드로 선택할 수 있게 합니다.

### 키워드 추출 테스트 방법

```bash
# 테스트 스크립트 실행
python test_keyword_extraction.py

# 모든 문제의 키워드 업데이트
python update_all_keywords.py
```

### 환경 설정

키워드 추출을 위해 다음 환경 변수 설정이 필요합니다:

```
# .env 파일
# AWS 설정
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY

# AWS Bedrock 설정
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_REGION=ap-northeast-2
```

### API 사용 예시

```python
from app.services.keyword_extraction import extract_keywords_from_answer

# 사용자 답변에서 키워드 추출
answer_text = "운영체제는 컴퓨터 하드웨어를 관리하고 응용 프로그램에 서비스를 제공하는 시스템 소프트웨어입니다."
keywords = extract_keywords_from_answer(answer_text)
print(keywords)  # ['운영체제', '하드웨어', '시스템 소프트웨어', '응용 프로그램']
```

## 시작하기

### 설치 및 설정

1. 저장소 클론하기
```
git clone https://github.com/jumptop/ITOP.git
cd ITOP
```

2. 가상환경 생성 및 활성화
```
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치
```
pip install -r requirements.txt
```

4. 환경 변수 설정
`.env` 파일을 루트 디렉토리에 생성하고 다음 변수를 설정하세요:
```
# 데이터베이스 설정
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=your-password
DB_NAME=exam_db

# AWS 설정
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Cognito 설정
COGNITO_USER_POOL_ID=your-user-pool-id
COGNITO_APP_CLIENT_ID=your-app-client-id

# OpenAI 설정
OPENAI_API_KEY=your-openai-api-key
```

5. 데이터베이스 마이그레이션
```
alembic upgrade head
```

### 서버 실행

개발 모드로 실행:
```
python run.py
```

또는 uvicorn으로 직접 실행:
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 문서

서버가 실행되면, 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 배포

AWS 환경에 배포하는 방법:

1. AWS Elastic Beanstalk 설정
2. RDS 및 Cognito 서비스 구성
3. CI/CD 파이프라인 설정

자세한 배포 지침은 [배포 가이드](deployment-guide.md)를 참조하세요.

## 프론트엔드 연동

이 백엔드 서버는 안드로이드 앱과 함께 작동하도록 설계되었습니다. 안드로이드 앱 저장소는 [여기](https://github.com/yourusername/exam-app-android)에서 확인할 수 있습니다.

## 라이센스

MIT

## 연락처

프로젝트 관련 문의: wjdghksgml5754@gmail.com
