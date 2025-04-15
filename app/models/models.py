from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid
from datetime import datetime

# 사용자 모델
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    cognito_id = Column(String(100), unique=True)
    user_work = Column(Boolean, default=False)  # 오늘 학습 완료 여부
    last_work_date = Column(DateTime)  # 마지막 학습 완료 날짜
    test_date = Column(DateTime)  # 시험 일정

# 사용자 틀린 문제 모델
class UserWrongAnswer(Base):
    __tablename__ = "user_wrong_answers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    question_id = Column(String(36), nullable=False)
    question_category = Column(String(20), nullable=False)  # os, db, network 등
    user_answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    attempt_count = Column(Integer, default=1)  # 틀린 횟수
    keywords = Column(String(255), nullable=True)  # 문제 키워드
    
    # 사용자와의 관계 설정
    user = relationship("User", backref="wrong_answers")

# OS 문제 모델
class OSQuestion(Base):
    __tablename__ = "os_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# DB 문제 모델
class DBQuestion(Base):
    __tablename__ = "db_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# 네트워크 문제 모델
class NetworkQuestion(Base):
    __tablename__ = "network_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# 프로그래밍 문제 모델
class ProgramQuestion(Base):
    __tablename__ = "program_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# 알고리즘 문제 모델
class AlgorithmQuestion(Base):
    __tablename__ = "algorithm_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# SQL 기본 문제 모델
class BaseSQLQuestion(Base):
    __tablename__ = "base_sql_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# SQL 고급 문제 모델
class HardSQLQuestion(Base):
    __tablename__ = "hard_sql_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# 애플리케이션 테스트 문제 모델
class AppTestQuestion(Base):
    __tablename__ = "app_test_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True)

# 애플리케이션 결함 문제 모델
class AppDefectQuestion(Base):
    __tablename__ = "app_defect_questions"
    
    id = Column(String(36), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    difficulty = Column(Integer, default=1)
    keywords = Column(String(255), nullable=True) 