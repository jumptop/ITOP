import os
import sys
import json
import importlib
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정
from app.models.database import get_db
from app.models.models import (
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion, 
    ProgramQuestion, AppTestQuestion, AppDefectQuestion, 
    BaseSQLQuestion, HardSQLQuestion
)

# 문제 유형별 테이블 매핑
MODEL_MAPPING = {
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

def insert_questions(db: Session, question_type: str, questions: List[Dict[str, Any]]) -> List[str]:
    """
    지정된 유형의 문제를 데이터베이스에 삽입합니다.
    
    Args:
        db (Session): 데이터베이스 세션
        question_type (str): 문제 유형 (os, db, network 등)
        questions (List[Dict]): 삽입할 문제 목록
        
    Returns:
        List[str]: 삽입된 문제 ID 목록
    """
    model = MODEL_MAPPING.get(question_type)
    if not model:
        raise ValueError(f"지원되지 않는 문제 유형입니다: {question_type}")
    
    inserted_ids = []
    
    for question_data in questions:
        # 이미 존재하는 ID인지 확인
        existing = db.query(model).filter(model.id == question_data["id"]).first()
        if existing:
            print(f"ID가 이미 존재합니다: {question_data['id']}, 업데이트합니다.")
            # 기존 객체 업데이트
            for key, value in question_data.items():
                setattr(existing, key, value)
            inserted_ids.append(existing.id)
        else:
            # 새 객체 생성
            new_question = model(**question_data)
            db.add(new_question)
            inserted_ids.append(new_question.id)
    
    db.commit()
    return inserted_ids

def load_questions_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    파일에서 문제 데이터를 로드합니다.
    
    Args:
        file_path (str): 로드할 파일 경로
        
    Returns:
        List[Dict]: 문제 데이터 목록
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_all_questions(db: Session):
    """
    모든 문제 데이터를 로드합니다.
    
    Args:
        db (Session): 데이터베이스 세션
    """
    data_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 각 문제 유형별 파일 로드
    question_types = [
        "os", "db", "network", "algorithm", "program", 
        "app_test", "app_defect", "base_sql", "hard_sql"
    ]
    
    for q_type in question_types:
        file_path = os.path.join(data_dir, f"{q_type}_questions.json")
        if os.path.exists(file_path):
            print(f"{q_type} 문제 로드 중...")
            questions = load_questions_from_file(file_path)
            inserted_ids = insert_questions(db, q_type, questions)
            print(f"{len(inserted_ids)}개의 {q_type} 문제가 로드되었습니다.")
        else:
            print(f"경고: {file_path} 파일이 존재하지 않습니다.")

def main():
    """
    메인 실행 함수
    """
    # 데이터베이스 연결
    db = next(get_db())
    
    try:
        # 모든 문제 로드
        load_all_questions(db)
        print("모든 문제가 성공적으로 로드되었습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 