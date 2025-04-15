from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Union
import random
from sqlalchemy.sql import func
from datetime import datetime
from pydantic import BaseModel

from ..models.database import get_db
from ..models.models import (
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion, 
    ProgramQuestion, AppTestQuestion, AppDefectQuestion, 
    BaseSQLQuestion, HardSQLQuestion, User, UserWrongAnswer
)

# answer_comparison 모듈 대신 직접 함수 구현
def evaluate_answer(user_answer, question_data):
    """사용자 답변을 평가합니다"""
    correct_answer = question_data["answer"]
    is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
    return {
        "is_correct": is_correct,
        "score": 1.0 if is_correct else 0.0,
        "feedback": "정답입니다!" if is_correct else "틀렸습니다.",
        "correct_answer": correct_answer,
        "example": question_data.get("example")
    }

router = APIRouter(
    prefix="/api",
    tags=["API"],
    responses={404: {"description": "Not found"}}
)

# 문제 유형별 테이블 매핑
QUESTION_TYPE_MAPPING = {
    "os": OSQuestion,
    "db": DBQuestion,
    "network": NetworkQuestion,
    "algorithm": AlgorithmQuestion,
    "program": ProgramQuestion,
    "app_test": AppTestQuestion,
    "app_defect": AppDefectQuestion,
    "base_sql": BaseSQLQuestion,
    "hard_sql": HardSQLQuestion
}

# 모델 정의
class Question(BaseModel):
    id: str
    question: str
    answer: str
    example: Optional[str] = None
    difficulty: int
    keywords: Optional[str] = None
    
    class Config:
        orm_mode = True

class AnswerRequest(BaseModel):
    question_id: str
    answer: str

class AnswerResponse(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    correct_answer: str
    missing_points: List[str] = []
    incorrect_points: List[str] = []
    example: Optional[str] = None

class TestSubmission(BaseModel):
    answers: List[Dict[str, str]]  # 질문 ID와 사용자 답변 목록 [{question_id: "os-1", answer: "답변"}]
    user_id: Optional[str] = None  # 선택적 사용자 ID (익명 테스트도 가능)

class TestResult(BaseModel):
    correct_count: int  # 맞은 문제 수
    total_questions: int  # 총 문제 수
    score: int  # 총점 (문제당 5점)
    result_details: List[Dict[str, any]]  # 각 문제별 채점 결과
    is_passed: bool  # 합격 여부 (60점 이상)

class WrongAnswerResponse(BaseModel):
    id: int
    question_id: str
    question_text: str
    user_answer: Optional[str]
    correct_answer: str
    question_category: str
    keywords: Optional[str]
    attempt_count: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# 모든 문제 카테고리 가져오기
@router.get("/categories", response_model=List[str])
async def get_categories():
    return list(QUESTION_TYPE_MAPPING.keys())

# 특정 카테고리의 문제 목록 가져오기
@router.get("/questions", response_model=List[Question])
async def get_questions(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    try:
        # 현재 시간으로 랜덤 시드 설정
        random.seed(datetime.now().timestamp())
        
        # 카테고리가 지정되지 않은 경우 모든 카테고리에서 일부 문제 반환
        if not category:
            result = []
            category_limits = {}
            
            # 각 카테고리별 문제 수 결정
            total_needed = limit
            categories = list(QUESTION_TYPE_MAPPING.keys())
            random.shuffle(categories)  # 카테고리 순서 섞기
            
            for cat in categories:
                if total_needed <= 0:
                    break
                category_limits[cat] = max(1, total_needed // len(categories))
                total_needed -= category_limits[cat]
            
            # 남은 문제 수 배분
            for cat in categories:
                if total_needed <= 0:
                    break
                category_limits[cat] += 1
                total_needed -= 1
            
            # 각 카테고리별 문제 가져오기
            for cat, cat_limit in category_limits.items():
                model = QUESTION_TYPE_MAPPING[cat]
                query = db.query(model)
                
                if difficulty:
                    query = query.filter(model.difficulty == difficulty)
                
                # 전체 문제 수 확인
                total_count = query.count()
                
                if total_count > 0:
                    # 랜덤으로 선택할 ID 목록
                    all_ids = [q.id for q in query.all()]
                    
                    # 중복 없이 랜덤 선택
                    if total_count <= cat_limit:
                        selected_ids = all_ids
                    else:
                        selected_ids = random.sample(all_ids, cat_limit)
                    
                    # 선택된 ID로 문제 조회
                    questions = db.query(model).filter(model.id.in_(selected_ids)).all()
                    result.extend(questions)
            
            # 최종 결과 섞기
            random.shuffle(result)
            
            return result[:limit]
        
        # 카테고리가 지정된 경우
        if category not in QUESTION_TYPE_MAPPING:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"카테고리를 찾을 수 없습니다: {category}"
            )
        
        model = QUESTION_TYPE_MAPPING[category]
        query = db.query(model)
        
        # 난이도 필터 적용
        if difficulty:
            query = query.filter(model.difficulty == difficulty)
        
        # 전체 문제 수 확인
        total_count = query.count()
        
        if total_count == 0:
            return []
        
        # 문제 선택 방식 변경 - 랜덤 ID 목록 사용
        all_ids = [q.id for q in query.all()]
        
        # 페이지네이션 대신 랜덤 선택
        actual_limit = min(limit, total_count)
        
        if offset >= total_count:
            return []
        
        remaining_ids = all_ids[offset:]
        
        if len(remaining_ids) <= actual_limit:
            selected_ids = remaining_ids
        else:
            selected_ids = random.sample(remaining_ids, actual_limit)
        
        # 선택된 ID로 문제 조회
        questions = db.query(model).filter(model.id.in_(selected_ids)).all()
        
        # 결과 섞기
        random.shuffle(questions)
        
        return questions
    except Exception as e:
        print(f"Error in get_questions: {str(e)}")
        # 오류가 발생하면 빈 목록 반환
        return []

# 특정 ID의 문제 가져오기
@router.get("/questions/{question_id}", response_model=Question)
async def get_question(question_id: str, db: Session = Depends(get_db)):
    try:
        # ID 형식에서 카테고리 추출 (예: "os-1" -> "os")
        category = question_id.split('-')[0] if '-' in question_id else None
        
        if not category or category not in QUESTION_TYPE_MAPPING:
            # 모든 모델에서 문제 ID 검색
            for model in QUESTION_TYPE_MAPPING.values():
                question = db.query(model).filter(model.id == question_id).first()
                if question:
                    return question
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문제를 찾을 수 없습니다"
            )
        
        # 카테고리가 있는 경우 해당 모델에서만 검색
        model = QUESTION_TYPE_MAPPING[category]
        question = db.query(model).filter(model.id == question_id).first()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문제를 찾을 수 없습니다"
            )
        
        return question
    except Exception as e:
        print(f"Error in get_question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문제 조회 중 오류 발생: {str(e)}"
        )

# 답안 평가
@router.post("/evaluate", response_model=AnswerResponse)
async def evaluate_user_answer(request: AnswerRequest, db: Session = Depends(get_db)):
    try:
        # ID 형식에서 카테고리 추출 (예: "os-1" -> "os")
        category = request.question_id.split('-')[0] if '-' in request.question_id else None
        
        if not category or category not in QUESTION_TYPE_MAPPING:
            # 모든 모델에서 문제 ID 검색
            for model_type, model in QUESTION_TYPE_MAPPING.items():
                question = db.query(model).filter(model.id == request.question_id).first()
                if question:
                    category = model_type
                    break
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="문제를 찾을 수 없습니다"
                )
        
        # 해당 모델에서 문제 조회
        model = QUESTION_TYPE_MAPPING[category]
        question = db.query(model).filter(model.id == request.question_id).first()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문제를 찾을 수 없습니다"
            )
        
        # 문제 데이터 구성
        question_data = {
            "question": question.question,
            "answer": question.answer,
            "example": question.example if hasattr(question, "example") else None
        }
        
        # 답변 평가
        evaluation_result = evaluate_answer(request.answer, question_data)
        
        return {
            "is_correct": evaluation_result["is_correct"],
            "score": round(evaluation_result["score"] * 100) / 100,  # 소수점 2자리까지
            "feedback": evaluation_result["feedback"],
            "correct_answer": evaluation_result["correct_answer"],
            "missing_points": evaluation_result.get("missing_points", []),
            "incorrect_points": evaluation_result.get("incorrect_points", []),
            "example": evaluation_result.get("example")
        }
    except Exception as e:
        print(f"Error in evaluate_user_answer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"답변 평가 중 오류 발생: {str(e)}"
        )

# 랜덤 문제 가져오기
@router.get("/random", response_model=Question)
async def get_random_question(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        # 현재 시간으로 랜덤 시드 설정
        random.seed(datetime.now().timestamp())
        
        if category and category not in QUESTION_TYPE_MAPPING:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"카테고리를 찾을 수 없습니다: {category}"
            )
        
        if category:
            # 특정 카테고리에서 랜덤 문제 선택
            model = QUESTION_TYPE_MAPPING[category]
            query = db.query(model)
            if difficulty:
                query = query.filter(model.difficulty == difficulty)
            
            # 전체 문제 ID 목록 가져오기
            all_question_ids = [q.id for q in query.all()]
            
            if not all_question_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="조건에 맞는 문제가 없습니다"
                )
            
            # 랜덤으로 ID 선택
            selected_id = random.choice(all_question_ids)
            
            # 선택된 ID로 문제 조회
            question = db.query(model).filter(model.id == selected_id).first()
            return question
        else:
            # 모든 카테고리에서 랜덤 문제 선택
            categories = list(QUESTION_TYPE_MAPPING.keys())
            random.shuffle(categories)  # 카테고리 순서 섞기
            
            all_questions = []
            for cat in categories:
                model = QUESTION_TYPE_MAPPING[cat]
                query = db.query(model)
                if difficulty:
                    query = query.filter(model.difficulty == difficulty)
                
                # 이 카테고리의 문제 ID 목록
                question_ids = [q.id for q in query.all()]
                
                if question_ids:
                    # 랜덤으로 ID 선택
                    selected_id = random.choice(question_ids)
                    # 선택된 ID로 문제 조회
                    question = db.query(model).filter(model.id == selected_id).first()
                    all_questions.append(question)
            
            if not all_questions:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="조건에 맞는 문제가 없습니다"
                )
            
            # 선택된 문제들 중에서 다시 랜덤 선택
            return random.choice(all_questions)
    except Exception as e:
        print(f"Error in get_random_question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"랜덤 문제 조회 중 오류 발생: {str(e)}"
        )

# 커스텀 시험 요청 모델
class TestConfigRequest(BaseModel):
    os_count: int = 3
    network_count: int = 3
    db_count: int = 3
    sql_count: int = 4  # 기본 + 고급 SQL 합계
    basic_sql_ratio: float = 0.5  # 기본 SQL이 차지하는 비율 (0.5면 기본과 고급을 2:2로 구성)
    program_count: int = 6
    app_count: int = 1  # 테스트 + 결함 합계
    app_test_ratio: float = 0.5  # 테스트가 차지하는 비율

# 커스텀 시험 생성 API
@router.post("/custom-test", response_model=List[Question])
async def create_custom_test(config: TestConfigRequest, db: Session = Depends(get_db)):
    try:
        # 현재 시간으로 랜덤 시드 설정
        random.seed(datetime.now().timestamp())
        result = []
        
        # OS 문제
        if config.os_count > 0:
            # 모든 OS 문제 ID 가져오기
            all_os_ids = [q.id for q in db.query(OSQuestion.id).all()]
            # 문제 수가 충분하면 랜덤 선택, 아니면 모두 선택
            if len(all_os_ids) >= config.os_count:
                selected_os_ids = random.sample(all_os_ids, config.os_count)
                os_questions = db.query(OSQuestion).filter(OSQuestion.id.in_(selected_os_ids)).all()
            else:
                os_questions = db.query(OSQuestion).all()
            result.extend(os_questions)
        
        # 네트워크 문제
        if config.network_count > 0:
            all_network_ids = [q.id for q in db.query(NetworkQuestion.id).all()]
            if len(all_network_ids) >= config.network_count:
                selected_network_ids = random.sample(all_network_ids, config.network_count)
                network_questions = db.query(NetworkQuestion).filter(NetworkQuestion.id.in_(selected_network_ids)).all()
            else:
                network_questions = db.query(NetworkQuestion).all()
            result.extend(network_questions)
        
        # DB 문제
        if config.db_count > 0:
            all_db_ids = [q.id for q in db.query(DBQuestion.id).all()]
            if len(all_db_ids) >= config.db_count:
                selected_db_ids = random.sample(all_db_ids, config.db_count)
                db_questions = db.query(DBQuestion).filter(DBQuestion.id.in_(selected_db_ids)).all()
            else:
                db_questions = db.query(DBQuestion).all()
            result.extend(db_questions)
        
        # SQL 문제 (기본 + 고급)
        if config.sql_count > 0:
            basic_sql_count = int(config.sql_count * config.basic_sql_ratio)
            hard_sql_count = config.sql_count - basic_sql_count
            
            if basic_sql_count > 0:
                all_basic_sql_ids = [q.id for q in db.query(BaseSQLQuestion.id).all()]
                if len(all_basic_sql_ids) >= basic_sql_count:
                    selected_basic_sql_ids = random.sample(all_basic_sql_ids, basic_sql_count)
                    basic_sql_questions = db.query(BaseSQLQuestion).filter(BaseSQLQuestion.id.in_(selected_basic_sql_ids)).all()
                else:
                    basic_sql_questions = db.query(BaseSQLQuestion).all()
                result.extend(basic_sql_questions)
            
            if hard_sql_count > 0:
                all_hard_sql_ids = [q.id for q in db.query(HardSQLQuestion.id).all()]
                if len(all_hard_sql_ids) >= hard_sql_count:
                    selected_hard_sql_ids = random.sample(all_hard_sql_ids, hard_sql_count)
                    hard_sql_questions = db.query(HardSQLQuestion).filter(HardSQLQuestion.id.in_(selected_hard_sql_ids)).all()
                else:
                    hard_sql_questions = db.query(HardSQLQuestion).all()
                result.extend(hard_sql_questions)
        
        # 프로그래밍 문제
        if config.program_count > 0:
            all_program_ids = [q.id for q in db.query(ProgramQuestion.id).all()]
            if len(all_program_ids) >= config.program_count:
                selected_program_ids = random.sample(all_program_ids, config.program_count)
                program_questions = db.query(ProgramQuestion).filter(ProgramQuestion.id.in_(selected_program_ids)).all()
            else:
                program_questions = db.query(ProgramQuestion).all()
            result.extend(program_questions)
        
        # 애플리케이션 문제 (테스트 + 결함)
        if config.app_count > 0:
            app_test_count = int(config.app_count * config.app_test_ratio)
            app_defect_count = config.app_count - app_test_count
            
            if app_test_count > 0:
                all_app_test_ids = [q.id for q in db.query(AppTestQuestion.id).all()]
                if len(all_app_test_ids) >= app_test_count:
                    selected_app_test_ids = random.sample(all_app_test_ids, app_test_count)
                    app_test_questions = db.query(AppTestQuestion).filter(AppTestQuestion.id.in_(selected_app_test_ids)).all()
                else:
                    app_test_questions = db.query(AppTestQuestion).all()
                result.extend(app_test_questions)
            
            if app_defect_count > 0:
                all_app_defect_ids = [q.id for q in db.query(AppDefectQuestion.id).all()]
                if len(all_app_defect_ids) >= app_defect_count:
                    selected_app_defect_ids = random.sample(all_app_defect_ids, app_defect_count)
                    app_defect_questions = db.query(AppDefectQuestion).filter(AppDefectQuestion.id.in_(selected_app_defect_ids)).all()
                else:
                    app_defect_questions = db.query(AppDefectQuestion).all()
                result.extend(app_defect_questions)
        
        # 결과 셔플 (순서 무작위화)
        random.shuffle(result)
        
        # 결과 개수 로그 출력
        print(f"생성된 시험 문제 수: {len(result)}")
        
        return result
    except Exception as e:
        print(f"Error in create_custom_test: {str(e)}")
        # 오류 발생 시 빈 목록 반환
        return []

# 기본 설정으로 정보처리기능사 표준 시험 생성 (20문제 표준 구성)
@router.get("/standard-test", response_model=List[Question])
async def create_standard_test(db: Session = Depends(get_db)):
    # 기본 표준 설정으로 생성
    config = TestConfigRequest(
        os_count=3,
        network_count=3, 
        db_count=3,
        sql_count=4,
        basic_sql_ratio=0.5,  # 기본 SQL 2문제, 고급 SQL 2문제
        program_count=6,
        app_count=1,
        app_test_ratio=0.5  # 테스트와 결함 각각 0.5문제씩 (랜덤 선택)
    )
    
    return await create_custom_test(config, db)

# 테스트 제출 및 채점 API
@router.post("/submit-test", response_model=TestResult)
async def submit_test(submission: TestSubmission, db: Session = Depends(get_db)):
    try:
        correct_count = 0
        total_questions = len(submission.answers)
        result_details = []
        
        # 사용자 ID가 제공된 경우 사용자 존재 확인
        user = None
        if submission.user_id:
            user = db.query(User).filter(User.id == submission.user_id).first()
        
        # 각 문제별 채점
        for answer_data in submission.answers:
            question_id = answer_data.get("question_id")
            user_answer = answer_data.get("answer", "").strip()
            
            if not question_id:
                continue
                
            # 문제 찾기
            category = question_id.split('-')[0] if '-' in question_id else None
            question = None
            
            if category and category in QUESTION_TYPE_MAPPING:
                model = QUESTION_TYPE_MAPPING[category]
                question = db.query(model).filter(model.id == question_id).first()
            else:
                # 카테고리가 없거나 유효하지 않은 경우 모든 모델에서 검색
                for model_type, model in QUESTION_TYPE_MAPPING.items():
                    q = db.query(model).filter(model.id == question_id).first()
                    if q:
                        question = q
                        category = model_type
                        break
            
            # 문제를 찾지 못한 경우 오답 처리
            if not question:
                result_details.append({
                    "question_id": question_id,
                    "is_correct": False,
                    "points": 0,
                    "user_answer": user_answer,
                    "correct_answer": "알 수 없음",
                    "feedback": "문제를 찾을 수 없습니다."
                })
                continue
                
            # 정답 확인
            is_correct = user_answer.lower() == question.answer.lower()
            
            # 틀린 문제일 경우 저장 (사용자 ID가 제공된 경우)
            if not is_correct and user:
                # 기존 틀린 문제 찾기
                existing_wrong = db.query(UserWrongAnswer).filter(
                    UserWrongAnswer.user_id == user.id,
                    UserWrongAnswer.question_id == question_id
                ).first()
                
                if existing_wrong:
                    # 이미 틀린 적이 있으면 시도 횟수 증가
                    existing_wrong.attempt_count += 1
                    existing_wrong.user_answer = user_answer
                    existing_wrong.created_at = func.now()
                else:
                    # 새로운 틀린 문제 저장
                    keywords = getattr(question, "keywords", None)
                    wrong_answer = UserWrongAnswer(
                        user_id=user.id,
                        question_id=question_id,
                        question_category=category,
                        user_answer=user_answer,
                        keywords=keywords
                    )
                    db.add(wrong_answer)
                
                db.commit()
            
            # 맞은 문제 카운트 증가
            if is_correct:
                correct_count += 1
                
            # 결과 상세 정보 추가
            result_details.append({
                "question_id": question_id,
                "is_correct": is_correct,
                "points": 5 if is_correct else 0,
                "user_answer": user_answer,
                "correct_answer": question.answer,
                "feedback": "정답입니다!" if is_correct else "틀렸습니다."
            })
            
        # 총점 계산 (맞은 문제 수 * 5점)
        total_score = correct_count * 5
        
        # 합격 여부 확인 (60점 이상)
        is_passed = total_score >= 60
        
        # 결과 로그 출력
        print(f"테스트 결과: {correct_count}/{total_questions} 문제 정답, 총점: {total_score}점, 합격여부: {'합격' if is_passed else '불합격'}")
        
        # 결과 반환
        return {
            "correct_count": correct_count,
            "total_questions": total_questions,
            "score": total_score,
            "result_details": result_details,
            "is_passed": is_passed
        }
            
    except Exception as e:
        print(f"Error in submit_test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"테스트 채점 중 오류 발생: {str(e)}"
        )

# 사용자의 틀린 문제 목록 API
@router.get("/users/{user_id}/wrong-answers", response_model=List[WrongAnswerResponse])
async def get_user_wrong_answers(
    user_id: str, 
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    사용자가 틀린 문제 목록을 반환합니다.
    """
    try:
        # 사용자 존재 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 틀린 문제 조회 (생성일 기준 내림차순)
        wrong_answers = db.query(UserWrongAnswer).filter(
            UserWrongAnswer.user_id == user_id
        ).order_by(UserWrongAnswer.created_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for wa in wrong_answers:
            # 문제 정보 조회
            question = None
            if wa.question_category in QUESTION_TYPE_MAPPING:
                model = QUESTION_TYPE_MAPPING[wa.question_category]
                question = db.query(model).filter(model.id == wa.question_id).first()
            
            if question:
                result.append({
                    "id": wa.id,
                    "question_id": wa.question_id,
                    "question_text": question.question,
                    "user_answer": wa.user_answer,
                    "correct_answer": question.answer,
                    "question_category": wa.question_category,
                    "keywords": wa.keywords,
                    "attempt_count": wa.attempt_count,
                    "created_at": wa.created_at
                })
        
        return result
    
    except Exception as e:
        print(f"Error in get_user_wrong_answers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"틀린 문제 조회 중 오류 발생: {str(e)}"
        )

# 맞춤형 시험 API - 틀린 문제 키워드 기반
@router.get("/users/{user_id}/personalized-test", response_model=List[Question])
async def create_personalized_test(
    user_id: str, 
    wrong_ratio: float = Query(0.5, ge=0.0, le=1.0),  # 틀린 문제 키워드 비율 (0.0~1.0)
    total_questions: int = Query(20, ge=5, le=50),    # 총 문제 수
    db: Session = Depends(get_db)
):
    """
    사용자가 틀린 문제의 키워드를 기반으로 맞춤형 시험을 생성합니다.
    wrong_ratio: 틀린 문제 키워드 관련 문제 비율 (기본값: 0.5)
    total_questions: 총 문제 수 (기본값: 20)
    """
    try:
        # 현재 시간으로 랜덤 시드 설정
        random.seed(datetime.now().timestamp())
        
        # 1. 사용자 존재 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 2. 사용자가 틀린 문제의 키워드 수집
        wrong_answers = db.query(UserWrongAnswer).filter(
            UserWrongAnswer.user_id == user_id
        ).all()
        
        # 키워드 추출 및 빈도 계산
        keyword_frequency = {}
        for wa in wrong_answers:
            if wa.keywords:
                for keyword in wa.keywords.split(','):
                    keyword = keyword.strip()
                    if keyword:
                        keyword_frequency[keyword] = keyword_frequency.get(keyword, 0) + 1
        
        # 3. 키워드 기반 문제 선택
        keyword_questions = []
        if keyword_frequency:
            # 키워드 빈도에 기반한 가중치 계산
            total_frequency = sum(keyword_frequency.values())
            keyword_weights = {k: v/total_frequency for k, v in keyword_frequency.items()}
            
            # 각 카테고리별로 키워드 기반 문제 검색
            for category, model in QUESTION_TYPE_MAPPING.items():
                for keyword, weight in sorted(keyword_weights.items(), key=lambda x: x[1], reverse=True):
                    # 문제 검색 수를 키워드 가중치에 비례하게 설정
                    search_limit = max(1, int(total_questions * wrong_ratio * weight * 2))
                    keyword_like = f"%{keyword}%"
                    
                    # 키워드가 포함된 문제 검색
                    keyword_matches = db.query(model).filter(
                        model.keywords.like(keyword_like)
                    ).limit(search_limit).all()
                    
                    if keyword_matches:
                        keyword_questions.extend(keyword_matches)
        
        # 4. 남은 문제 수를 일반 랜덤 문제로 채움
        wrong_questions_count = min(len(keyword_questions), int(total_questions * wrong_ratio))
        remaining_count = total_questions - wrong_questions_count
        
        # 중복 제거를 위한 ID 기록
        selected_ids = set([q.id for q in keyword_questions[:wrong_questions_count]])
        
        result = keyword_questions[:wrong_questions_count]
        
        # 5. 남은 문제 수만큼 랜덤 문제 선택
        if remaining_count > 0:
            # 각 카테고리별 문제 분배
            categories = list(QUESTION_TYPE_MAPPING.keys())
            random.shuffle(categories)
            
            questions_per_category = max(1, remaining_count // len(categories))
            remaining = remaining_count
            
            for category in categories:
                if remaining <= 0:
                    break
                    
                model = QUESTION_TYPE_MAPPING[category]
                category_count = min(questions_per_category, remaining)
                
                # 이미 선택된 문제 제외
                random_questions = db.query(model).filter(
                    ~model.id.in_(selected_ids)
                ).all()
                
                if random_questions:
                    # 무작위 선택
                    if len(random_questions) > category_count:
                        selected = random.sample(random_questions, category_count)
                    else:
                        selected = random_questions
                    
                    for q in selected:
                        selected_ids.add(q.id)
                        result.append(q)
                    
                    remaining -= len(selected)
        
        # 6. 결과 셔플
        random.shuffle(result)
        
        # 7. 중복 제거 및 총 문제 수 제한
        unique_questions = []
        unique_ids = set()
        
        for q in result:
            if q.id not in unique_ids and len(unique_questions) < total_questions:
                unique_ids.add(q.id)
                unique_questions.append(q)
        
        # 로그 출력
        print(f"사용자 {user_id}를 위한 맞춤형 시험 생성: 총 {len(unique_questions)}문제 (키워드 기반: {wrong_questions_count})")
        
        return unique_questions
    
    except Exception as e:
        print(f"Error in create_personalized_test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"맞춤형 시험 생성 중 오류 발생: {str(e)}"
        )