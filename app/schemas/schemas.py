from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

class QuestionBase(BaseModel):
    id: str
    question: str
    answer: str
    example: Optional[str] = None
    difficulty: int
    keywords: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class OSQuestionSchema(QuestionBase):
    os_type: Optional[str] = None

class DBQuestionSchema(QuestionBase):
    db_type: Optional[str] = None

class NetworkQuestionSchema(QuestionBase):
    network_type: Optional[str] = None

class AlgorithmQuestionSchema(QuestionBase):
    algorithm_type: Optional[str] = None

class ProgramQuestionSchema(QuestionBase):
    program_type: Optional[str] = None

class AppTestQuestionSchema(QuestionBase):
    app_test_type: Optional[str] = None

class AppDefectQuestionSchema(QuestionBase):
    app_defect_type: Optional[str] = None

class BaseSQLQuestionSchema(QuestionBase):
    sql_type: Optional[str] = None

class HardSQLQuestionSchema(QuestionBase):
    sql_type: Optional[str] = None

# 사용자 답변 제출을 위한 스키마
class AnswerSubmission(BaseModel):
    answer: str

class AnswerEvaluationResult(BaseModel):
    is_correct: bool
    score: int
    feedback: str
    missing_points: Optional[List[str]] = []
    incorrect_points: Optional[List[str]] = []
    correct_answer: Optional[str] = None
    keywords: Optional[List[str]] = []

# 추천 질문 요청을 위한 스키마
class RecommendationRequest(BaseModel):
    question_types: List[str] = Field(..., description="추천 받을 질문 유형 목록")
    count: Optional[int] = Field(5, description="추천받을 질문 수 (기본값: 5, 최대: 10)")

    @validator('count')
    def validate_count(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError('추천 질문 수는 1에서 10 사이여야 합니다')
        return v

    @validator('question_types')
    def validate_question_types(cls, v):
        valid_types = ["os", "db", "network", "algorithm", "program", 
                       "app_test", "app_defect", "base_sql", "hard_sql"]
        for type_name in v:
            if type_name not in valid_types:
                raise ValueError(f"유효하지 않은 질문 유형: {type_name}")
        return v 