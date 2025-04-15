from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Union
from pydantic import BaseModel

from ..models.database import get_db
from ..models.models import (
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion, 
    ProgramQuestion, AppTestQuestion, AppDefectQuestion, BaseSQLQuestion, 
    HardSQLQuestion, User
)
from ..auth.cognito import cognito_auth
from ..services.keyword_extraction import extract_key_phrases

router = APIRouter(
    prefix="/admin",
    tags=["관리자"],
    responses={404: {"description": "Not found"}},
)

# OAuth2 비밀번호 기반 인증 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# 모델 정의
class QuestionBase(BaseModel):
    question: str
    answer: str
    difficulty: int = 1

class OSQuestionCreate(QuestionBase):
    os_type: Optional[str] = None

class DBQuestionCreate(QuestionBase):
    db_type: Optional[str] = None

class NetworkQuestionCreate(QuestionBase):
    network_topic: Optional[str] = None

class AlgorithmQuestionCreate(QuestionBase):
    algorithm_type: Optional[str] = None

class ProgramQuestionCreate(QuestionBase):
    programming_language: Optional[str] = None

class AppTestQuestionCreate(QuestionBase):
    test_method: Optional[str] = None

class AppDefectQuestionCreate(QuestionBase):
    defect_type: Optional[str] = None

class BaseSQLQuestionCreate(QuestionBase):
    sql_level: Optional[str] = None

class HardSQLQuestionCreate(QuestionBase):
    sql_complexity: Optional[str] = None

# 관리자 확인
def get_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    claims = cognito_auth.verify_token(token)
    
    # 관리자 그룹 확인 로직
    # 실제 Cognito 그룹 확인 로직으로 대체 가능
    groups = claims.get("cognito:groups", [])
    if "admin" not in groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 없습니다."
        )
    
    user = db.query(User).filter(User.cognito_id == claims.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return user

# OS 문제 추가
@router.post("/questions/os", status_code=status.HTTP_201_CREATED)
async def create_os_question(
    question: OSQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = OSQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        os_type=question.os_type
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "OS 문제가 성공적으로 추가되었습니다."}

# DB 문제 추가
@router.post("/questions/db", status_code=status.HTTP_201_CREATED)
async def create_db_question(
    question: DBQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = DBQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        db_type=question.db_type
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "DB 문제가 성공적으로 추가되었습니다."}

# Network 문제 추가
@router.post("/questions/network", status_code=status.HTTP_201_CREATED)
async def create_network_question(
    question: NetworkQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = NetworkQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        network_topic=question.network_topic
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "네트워크 문제가 성공적으로 추가되었습니다."}

# Algorithm 문제 추가
@router.post("/questions/algorithm", status_code=status.HTTP_201_CREATED)
async def create_algorithm_question(
    question: AlgorithmQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = AlgorithmQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        algorithm_type=question.algorithm_type
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "알고리즘 문제가 성공적으로 추가되었습니다."}

# Program 문제 추가
@router.post("/questions/program", status_code=status.HTTP_201_CREATED)
async def create_program_question(
    question: ProgramQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = ProgramQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        programming_language=question.programming_language
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "프로그램 문제가 성공적으로 추가되었습니다."}

# AppTest 문제 추가
@router.post("/questions/apptest", status_code=status.HTTP_201_CREATED)
async def create_apptest_question(
    question: AppTestQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = AppTestQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        test_method=question.test_method
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "앱 테스트 문제가 성공적으로 추가되었습니다."}

# AppDefect 문제 추가
@router.post("/questions/appdefect", status_code=status.HTTP_201_CREATED)
async def create_appdefect_question(
    question: AppDefectQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = AppDefectQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        defect_type=question.defect_type
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "앱 결함 문제가 성공적으로 추가되었습니다."}

# BaseSQL 문제 추가
@router.post("/questions/basesql", status_code=status.HTTP_201_CREATED)
async def create_basesql_question(
    question: BaseSQLQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = BaseSQLQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        sql_level=question.sql_level
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "기본 SQL 문제가 성공적으로 추가되었습니다."}

# HardSQL 문제 추가
@router.post("/questions/hardsql", status_code=status.HTTP_201_CREATED)
async def create_hardsql_question(
    question: HardSQLQuestionCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question.question + " " + question.answer)
    keywords = ",".join(extracted_keywords)
    
    db_question = HardSQLQuestion(
        question=question.question,
        answer=question.answer,
        difficulty=question.difficulty,
        keywords=keywords,
        sql_complexity=question.sql_complexity
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return {"id": db_question.id, "message": "고급 SQL 문제가 성공적으로 추가되었습니다."}

# 문제 수정
@router.put("/questions/{question_type}/{question_id}", status_code=status.HTTP_200_OK)
async def update_question(
    question_type: str,
    question_id: str,
    question_update: QuestionBase,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 질문 유형 확인
    if question_type not in {
        "os": OSQuestion, 
        "db": DBQuestion, 
        "network": NetworkQuestion, 
        "algorithm": AlgorithmQuestion,
        "program": ProgramQuestion, 
        "app_test": AppTestQuestion, 
        "app_defect": AppDefectQuestion, 
        "base_sql": BaseSQLQuestion, 
        "hard_sql": HardSQLQuestion
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 문제 유형입니다."
        )
    
    # 적절한 모델 선택
    question_model = {
        "os": OSQuestion, 
        "db": DBQuestion, 
        "network": NetworkQuestion, 
        "algorithm": AlgorithmQuestion,
        "program": ProgramQuestion, 
        "app_test": AppTestQuestion, 
        "app_defect": AppDefectQuestion, 
        "base_sql": BaseSQLQuestion, 
        "hard_sql": HardSQLQuestion
    }[question_type]
    
    # 문제 확인
    db_question = db.query(question_model).filter(question_model.id == question_id).first()
    if not db_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    # 키워드 자동 추출
    extracted_keywords = extract_key_phrases(question_update.question + " " + question_update.answer)
    keywords = ",".join(extracted_keywords)
    
    # 문제 업데이트
    db_question.question = question_update.question
    db_question.answer = question_update.answer
    db_question.difficulty = question_update.difficulty
    db_question.keywords = keywords
    
    db.commit()
    
    return {"id": db_question.id, "message": "문제가 성공적으로 업데이트되었습니다."}

# 문제 삭제
@router.delete("/questions/{question_type}/{question_id}", status_code=status.HTTP_200_OK)
async def delete_question(
    question_type: str,
    question_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # 질문 유형 확인
    if question_type not in {
        "os": OSQuestion, 
        "db": DBQuestion, 
        "network": NetworkQuestion, 
        "algorithm": AlgorithmQuestion,
        "program": ProgramQuestion, 
        "app_test": AppTestQuestion, 
        "app_defect": AppDefectQuestion, 
        "base_sql": BaseSQLQuestion, 
        "hard_sql": HardSQLQuestion
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 문제 유형입니다."
        )
    
    # 적절한 모델 선택
    question_model = {
        "os": OSQuestion, 
        "db": DBQuestion, 
        "network": NetworkQuestion, 
        "algorithm": AlgorithmQuestion,
        "program": ProgramQuestion, 
        "app_test": AppTestQuestion, 
        "app_defect": AppDefectQuestion, 
        "base_sql": BaseSQLQuestion, 
        "hard_sql": HardSQLQuestion
    }[question_type]
    
    # 문제 확인
    db_question = db.query(question_model).filter(question_model.id == question_id).first()
    if not db_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문제를 찾을 수 없습니다."
        )
    
    # 문제 삭제
    db.delete(db_question)
    db.commit()
    
    return {"message": "문제가 성공적으로 삭제되었습니다."} 