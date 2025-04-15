# 정보처리기능사 시험 문제 데이터

이 폴더에는 정보처리기능사 시험 준비를 위한 문제 데이터가 포함되어 있습니다. 각 파일은 특정 분야의 문제들을 JSON 형식으로 정의합니다.

## 데이터 구조

각 문제 파일은 다음 구조의 JSON 배열로 이루어져 있습니다:

```json
[
  {
    "id": "분야-숫자",
    "question": "문제 내용",
    "answer": "정답",
    "example": "보기 또는 예시",
    "difficulty": 난이도(1-5),
    "keywords": "키워드1,키워드2,키워드3"
  },
  ...
]
```

## 문제 유형

현재 지원되는 문제 유형은 다음과 같습니다:

1. **OS 문제**: `os_questions.json` - 운영체제 관련 문제
2. **DB 문제**: `db_questions.json` - 데이터베이스 관련 문제
3. **네트워크 문제**: `network_questions.json` - 네트워크 관련 문제
4. **알고리즘 문제**: `algorithm_questions.json` - 알고리즘 및 자료구조 관련 문제
5. **프로그래밍 문제**: `program_questions.json` - 프로그래밍 언어 및 개발 방법론 관련 문제
6. **애플리케이션 테스트 문제**: `app_test_questions.json` - 소프트웨어 테스트 관련 문제
7. **애플리케이션 결함 문제**: `app_defect_questions.json` - 소프트웨어 결함 및 디버깅 관련 문제
8. **기본 SQL 문제**: `base_sql_questions.json` - 기본 SQL 관련 문제
9. **고급 SQL 문제**: `hard_sql_questions.json` - 고급 SQL 관련 문제

## 데이터 로드 방법

`loader.py` 스크립트를 사용하여 모든 문제 데이터를 데이터베이스에 로드할 수 있습니다:

```bash
python loader.py
```

이 스크립트는 각 JSON 파일을 읽고 해당 테이블에 문제를 추가합니다. 이미 존재하는 ID의 문제는 업데이트됩니다.

## 데이터 추가 및 수정 방법

새 문제를 추가하거나 기존 문제를 수정하려면 해당 JSON 파일을 편집한 후 `loader.py`를 실행하세요.

### 새 문제 추가 예시

```json
{
  "id": "os-8",
  "question": "페이지 교체 알고리즘 중 FIFO와 LRU의 차이점은?",
  "answer": "FIFO(First-In-First-Out)는 가장 먼저 들어온 페이지를 교체하는 반면, LRU(Least Recently Used)는 가장 오랫동안 사용되지 않은 페이지를 교체합니다.",
  "example": "FIFO, LRU, 페이지 교체, 가상 메모리, 벨라디의 모순",
  "difficulty": 3,
  "keywords": "페이지교체,FIFO,LRU,가상메모리,페이징"
}
```

## 데이터 백업

정기적으로 데이터를 백업하는 것이 좋습니다. 다음 명령어로 현재 데이터베이스의 모든 문제를 JSON 파일로 추출할 수 있습니다:

```bash
python data_backup.py
```

이 명령은 `backup` 폴더에 현재 날짜와 시간으로 백업 파일을 생성합니다.

## 데이터 형식 가이드라인

- `id`: 문제 유형의 약어와 숫자 조합 (예: "os-1", "db-2")
- `question`: 명확하고 간결한 문제 설명
- `answer`: 정확한 정답
- `example`: 객관식 보기 또는 관련 키워드 (쉼표로 구분)
- `difficulty`: 1(쉬움) ~ 5(어려움) 사이의 정수
- `keywords`: 문제와 관련된 키워드 (쉼표로 구분, 공백 없음)

## 주의사항

- JSON 파일을 편집할 때는 유효한 JSON 형식을 유지해야 합니다.
- 각 문제의 ID는 해당 유형 내에서 고유해야 합니다.
- 키워드는 검색 및 추천 알고리즘에 중요하므로 신중하게 선택하세요. 