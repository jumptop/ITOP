from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Dict, Optional
from pydantic import BaseModel
import uuid
import random

from ..models.database import get_db
from ..models.models import (
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion, 
    ProgramQuestion, AppTestQuestion, AppDefectQuestion, BaseSQLQuestion, 
    HardSQLQuestion, User
)
from ..auth.cognito import cognito_auth, get_current_user
from ..services.answer_verification import verify_answer, get_similar_questions
from ..services.keyword_extraction import extract_keywords_from_answer
from ..services.simple_analysis import analyze_answer
from ..schemas.schemas import OSQuestionSchema, QuestionBase, AnswerSubmission, RecommendationRequest
from ..services.answer_comparison import evaluate_answer

router = APIRouter(
    prefix="/questions",
    tags=["문제"],
    responses={404: {"description": "Not found"}},
)

# OAuth2 비밀번호 기반 인증 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# 모델 정의
class QuestionBase(BaseModel):
    id: str
    question: str
    answer: str
    example: Optional[str] = None
    difficulty: int
    keywords: Optional[str] = None
    
    class Config:
        orm_mode = True

class QuestionResponse(QuestionBase):
    category: str

class AnswerSubmit(BaseModel):
    question_id: str
    question_type: str
    user_answer: str

class AnswerResult(BaseModel):
    correct: bool
    correct_answer: str
    message: str

# 질문 유형별 테이블 매핑
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

# 현재 사용자 정보 가져오기
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    claims = cognito_auth.verify_token(token)
    user = db.query(User).filter(User.cognito_id == claims.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    return user

# 모든 문제 카테고리 가져오기
@router.get("/categories", response_model=List[str])
async def get_categories():
    return ["OS", "DB", "Network", "Algorithm", "Program", "AppTest", "AppDefect", "BaseSQL", "HardSQL"]

# 랜덤 문제 가져오기
@router.get("/random", response_model=QuestionResponse)
async def get_random_question(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # 카테고리에 맞는 질문 모델 선택
    if category and category.lower() in QUESTION_TYPE_MAPPING:
        question_model = QUESTION_TYPE_MAPPING[category.lower()]
        query = db.query(question_model)
    else:
        # 카테고리가 없으면 OS 질문을 기본으로 사용
        query = db.query(OSQuestion)
    
    # 난이도 필터 적용
    if difficulty:
        query = query.filter(question_model.difficulty == difficulty)
    
    # 랜덤으로 문제 선택
    question = query.order_by(func.random()).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 조건에 맞는 문제를 찾을 수 없습니다."
        )
    
    return {
        "id": question.id,
        "question": question.question,
        "answer": question.answer,
        "example": question.example,
        "difficulty": question.difficulty,
        "keywords": question.keywords,
        "category": category or "OS"
    }

# 특정 문제 가져오기
@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str, question_type: str, db: Session = Depends(get_db)):
    if question_type.lower() not in QUESTION_TYPE_MAPPING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 문제 유형입니다."
        )
    
    question_model = QUESTION_TYPE_MAPPING[question_type.lower()]
    question = db.query(question_model).filter(question_model.id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    return {
        "id": question.id,
        "question": question.question,
        "answer": question.answer,
        "example": question.example,
        "difficulty": question.difficulty,
        "keywords": question.keywords,
        "category": question_type
    }

# 문제 목록 가져오기
@router.get("/", response_model=List[QuestionResponse])
async def get_questions(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    if category and category.lower() in QUESTION_TYPE_MAPPING:
        question_model = QUESTION_TYPE_MAPPING[category.lower()]
        query = db.query(question_model)
        
        # 난이도 필터 적용
        if difficulty:
            query = query.filter(question_model.difficulty == difficulty)
        
        # 페이지네이션 적용
        questions = query.offset(offset).limit(limit).all()
        
        # 응답 형식으로 변환
        result = []
        for question in questions:
            result.append({
                "id": question.id,
                "question": question.question,
                "answer": question.answer,
                "example": question.example,
                "difficulty": question.difficulty,
                "keywords": question.keywords,
                "category": category
            })
        
        return result
    else:
        # 카테고리가 없거나 유효하지 않은 경우 모든 카테고리에서 검색
        result = []
        remaining = limit
        
        for category_key, model in QUESTION_TYPE_MAPPING.items():
            if remaining <= 0:
                break
                
            query = db.query(model)
            
            # 난이도 필터 적용
            if difficulty:
                query = query.filter(model.difficulty == difficulty)
            
            # 각 카테고리에서 일부 문제만 가져오기
            category_limit = min(remaining, limit // len(QUESTION_TYPE_MAPPING) + 1)
            category_questions = query.offset(offset).limit(category_limit).all()
            
            for question in category_questions:
                result.append({
                    "id": question.id,
                    "question": question.question,
                    "answer": question.answer,
                    "example": question.example,
                    "difficulty": question.difficulty,
                    "keywords": question.keywords,
                    "category": category_key
                })
                
            remaining -= len(category_questions)
        
        return result

# 답변 제출
@router.post("/submit-answer", response_model=AnswerResult)
async def submit_answer(
    answer: AnswerSubmit,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 사용자 조회
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 문제 유형이 유효한지 확인
    if answer.question_type.lower() not in QUESTION_TYPE_MAPPING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 문제 유형입니다."
        )
    
    # 해당 모델에서 문제 조회
    question_model = QUESTION_TYPE_MAPPING[answer.question_type.lower()]
    question = db.query(question_model).filter(question_model.id == answer.question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    # 답변 정확성 확인 (간단한 문자열 비교)
    correct = answer.user_answer.strip().lower() == question.answer.strip().lower()
    
    return {
        "correct": correct,
        "correct_answer": question.answer,
        "message": "정답입니다!" if correct else "틀렸습니다."
    }

# 유사 문제 추천
@router.get("/similar/{question_id}", response_model=List[Dict])
async def get_similar_questions_api(
    question_id: str,
    count: int = Query(5, ge=1, le=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 문제 확인
    question = db.query(OSQuestion).filter(OSQuestion.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    # 사용자가 이 문제에 대해 오답을 제출한 적이 있는지 확인
    wrong_answer = db.query(UserWrongAnswer).filter(
        UserWrongAnswer.user_id == user.id,
        UserWrongAnswer.question_id == question_id
    ).first()
    
    if not wrong_answer:
        # 사용자가 오답을 제출한 적이 없으면 키워드 기반으로 추천
        keywords = question.keywords.split(",") if question.keywords else []
    else:
        # 사용자가 오답을 제출한 적이 있으면 오답에서 키워드 추출
        extracted_keywords = extract_keywords_from_answer(wrong_answer.user_answer)
        
        # 기존 키워드와 추출한 키워드 합치기
        base_keywords = question.keywords.split(",") if question.keywords else []
        keywords = list(set(base_keywords + extracted_keywords))
    
    # 유사 문제 생성
    similar_questions = get_similar_questions(keywords, question.category, count)
    
    return similar_questions

# 사용자 오답 목록 가져오기
@router.get("/wrong-answers", response_model=List[Dict])
async def get_wrong_answers(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 사용자 조회
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 더 이상 틀린 답변을 저장하지 않으므로 빈 목록 반환
    return []

# 키워드 기반 추천 문제 가져오기
@router.get("/recommended", response_model=List[Dict])
async def get_recommended_questions(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 사용자 조회
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 더 이상 개인화된 추천이 불가능하므로 랜덤한 문제 추천
    # 각 카테고리에서 1개씩 문제 선택
    recommended_questions = []
    
    for category, model in QUESTION_TYPE_MAPPING.items():
        question = db.query(model).order_by(func.random()).first()
        if question:
            recommended_questions.append({
                "id": question.id,
                "category": category,
                "question": question.question,
                "difficulty": question.difficulty
            })
    
    return recommended_questions

# 맞춤형 시험 문제 생성 엔드포인트
@router.post("/generate-exam", response_model=List[Dict])
async def generate_exam(
    total_questions: int = Query(20, ge=5, le=50),  # 총 문제 수
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 사용자 조회
    user = db.query(User).filter(User.cognito_id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 사용자의 틀린 문제 조회
    wrong_answers = db.query(UserWrongAnswer).filter(UserWrongAnswer.user_id == user.id).all()
    
    # 문제 유형별 빈도 계산
    type_counter = {}
    for wa in wrong_answers:
        type_counter[wa.question_type] = type_counter.get(wa.question_type, 0) + 1
    
    # 키워드 빈도 계산
    keyword_counter = {}
    for wa in wrong_answers:
        if wa.keywords:
            for keyword in wa.keywords.split(","):
                keyword = keyword.strip()
                if keyword:
                    keyword_counter[keyword] = keyword_counter.get(keyword, 0) + 1
    
    # 선택된 문제들을 담을 리스트
    selected_questions = []
    
    # 틀린 문제가 없는 경우 - 기본 분배
    if not wrong_answers:
        # 기본 분배 - 각 유형별로 동일한 수의 문제 선택
        question_types = list(QUESTION_TYPE_MAPPING.keys())
        questions_per_type = total_questions // len(question_types)
        remainder = total_questions % len(question_types)
        
        for q_type, model in QUESTION_TYPE_MAPPING.items():
            num_questions = questions_per_type + (1 if remainder > 0 else 0)
            remainder -= 1 if remainder > 0 else 0
            
            # 해당 유형의 문제를 랜덤하게 선택
            questions = db.query(model).order_by(func.random()).limit(num_questions).all()
            
            for q in questions:
                selected_questions.append({
                    "id": q.id,
                    "type": q_type,
                    "question": q.question,
                    "answer": q.answer,
                    "example": q.example,
                    "difficulty": q.difficulty
                })
    else:
        # 틀린 문제가 있는 경우 - 빈도 기반 분배
        # 총 틀린 문제 수
        total_wrong = sum(type_counter.values())
        
        # 타입별 출제 비율 계산 (최소 10%는 보장)
        allocation = {}
        for q_type in QUESTION_TYPE_MAPPING.keys():
            if q_type in type_counter:
                # 해당 유형의 틀린 문제 비율에 따라 가중치 부여 (최소 10% 보장)
                allocation[q_type] = max(0.1, type_counter[q_type] / total_wrong * 0.9)
            else:
                # 틀린 적 없는 유형은 기본 할당
                allocation[q_type] = 0.1 / (len(QUESTION_TYPE_MAPPING) - len(type_counter))
        
        # 비율 정규화
        total_allocation = sum(allocation.values())
        for q_type in allocation:
            allocation[q_type] = allocation[q_type] / total_allocation
        
        # 각 유형별 문제 수 계산
        questions_per_type = {}
        allocated_questions = 0
        
        for q_type, ratio in allocation.items():
            # 반올림하여 해당 유형의 문제 수 결정
            num = round(total_questions * ratio)
            questions_per_type[q_type] = num
            allocated_questions += num
        
        # 할당된 문제 수와 총 문제 수의 차이 보정
        diff = total_questions - allocated_questions
        if diff != 0:
            # 가장 비율이 높은 유형에 차이를 더하거나 뺌
            max_type = max(allocation.items(), key=lambda x: x[1])[0]
            questions_per_type[max_type] += diff
        
        # 키워드 기반 문제 선택
        for q_type, num_questions in questions_per_type.items():
            if num_questions <= 0:
                continue
                
            model = QUESTION_TYPE_MAPPING[q_type]
            
            # 키워드 기반 우선 선택 (70%)
            keyword_questions = []
            if keyword_counter:
                # 상위 키워드 선택
                top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)
                
                # 각 키워드에 대해 관련 문제 찾기
                for keyword, _ in top_keywords:
                    if len(keyword_questions) >= int(num_questions * 0.7):
                        break
                        
                    # 해당 키워드를 포함하는 문제 찾기
                    questions = db.query(model).filter(model.keywords.like(f"%{keyword}%"))\
                                .order_by(func.random())\
                                .limit(max(1, int(num_questions * 0.2))).all()
                    
                    for q in questions:
                        # 중복 방지
                        if any(kq["id"] == q.id for kq in keyword_questions):
                            continue
                            
                        keyword_questions.append({
                            "id": q.id,
                            "type": q_type,
                            "question": q.question,
                            "answer": q.answer,
                            "example": q.example,
                            "difficulty": q.difficulty,
                            "source": "keyword"
                        })
                        
                        if len(keyword_questions) >= int(num_questions * 0.7):
                            break
            
            # 남은 문제 수만큼 랜덤 선택 (30% 또는 키워드 기반으로 충분히 선택되지 않은 경우)
            remaining = num_questions - len(keyword_questions)
            if remaining > 0:
                # 이미 선택된 문제 ID 목록
                selected_ids = [q["id"] for q in keyword_questions]
                
                # 랜덤 문제 선택 (이미 선택된 문제 제외)
                random_questions = db.query(model)\
                    .filter(~model.id.in_(selected_ids))\
                    .order_by(func.random())\
                    .limit(remaining).all()
                
                for q in random_questions:
                    keyword_questions.append({
                        "id": q.id,
                        "type": q_type,
                        "question": q.question,
                        "answer": q.answer,
                        "example": q.example,
                        "difficulty": q.difficulty,
                        "source": "random"
                    })
            
            # 선택된 문제 추가
            selected_questions.extend(keyword_questions)
    
    # 최종 문제 순서 섞기
    random.shuffle(selected_questions)
    
    # 반환할 때 source 필드 제거
    for q in selected_questions:
        if "source" in q:
            del q["source"]
    
    return selected_questions

# 모든 질문 유형 목록 조회
@router.get("/types")
def get_question_types():
    return list(QUESTION_TYPE_MAPPING.keys())

# 특정 유형의 질문 목록 조회
@router.get("/{question_type}", response_model=List[QuestionBase])
def get_questions_by_type(
    question_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if question_type not in QUESTION_TYPE_MAPPING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"유효하지 않은 질문 유형: {question_type}"
        )
    
    model = QUESTION_TYPE_MAPPING[question_type]
    questions = db.query(model).all()
    
    return questions

# 특정 유형의 특정 질문 조회
@router.get("/{question_type}/{question_id}", response_model=QuestionBase)
def get_question(
    question_type: str,
    question_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if question_type not in QUESTION_TYPE_MAPPING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"유효하지 않은 질문 유형: {question_type}"
        )
    
    model = QUESTION_TYPE_MAPPING[question_type]
    question = db.query(model).filter(model.id == question_id).first()
    
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID가 {question_id}인 {question_type} 질문을 찾을 수 없습니다"
        )
    
    return question

# 답변 평가 엔드포인트
@router.post("/evaluate-answer")
async def evaluate_answer_endpoint(
    submission: AnswerSubmission,
    question_id: str,
    question_type: str,
    use_advanced: bool = Query(True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 문제 조회
    if question_type not in QUESTION_TYPE_MAPPING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 문제 유형입니다."
        )
    
    question_model = QUESTION_TYPE_MAPPING[question_type]
    question = db.query(question_model).filter(question_model.id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    # 답변 평가
    is_correct = False
    feedback = ""
    
    if use_advanced:
        # 고급 평가 로직
        # ...
        pass
    else:
        # 기본 평가 로직 (문자열 비교)
        is_correct = submission.answer.strip().lower() == question.answer.strip().lower()
        feedback = "정답입니다!" if is_correct else "틀렸습니다. 다시 시도해보세요."
    
    # 응답 반환
    return {
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "feedback": feedback,
        "example": question.example
    }

# 사용자에게 추천 문제 제공
@router.post("/recommend")
def recommend_questions(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 더 이상 개인화된 키워드 기반 추천이 불가능하므로 랜덤 추천
    result = []
    
    # 각 카테고리에서 요청한 수만큼 문제 선택
    for category, count in request.categories.items():
        if category in QUESTION_TYPE_MAPPING and count > 0:
            model = QUESTION_TYPE_MAPPING[category]
            questions = db.query(model).order_by(func.random()).limit(count).all()
            
            for q in questions:
                result.append({
                    "id": q.id,
                    "category": category,
                    "question": q.question,
                    "difficulty": q.difficulty
                })
    
    return result 