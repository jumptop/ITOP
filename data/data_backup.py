import os
import sys
import json
import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 데이터베이스 연결 설정
from app.models.database import get_db
from app.models.models import (
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion, 
    ProgramQuestion, AppTestQuestion, AppDefectQuestion, 
    BaseSQLQuestion, HardSQLQuestion
)

# 모델과 파일 이름 매핑
MODEL_FILE_MAPPING = {
    OSQuestion: "os_questions.json",
    DBQuestion: "db_questions.json",
    NetworkQuestion: "network_questions.json",
    AlgorithmQuestion: "algorithm_questions.json",
    ProgramQuestion: "program_questions.json",
    AppTestQuestion: "app_test_questions.json",
    AppDefectQuestion: "app_defect_questions.json",
    BaseSQLQuestion: "base_sql_questions.json",
    HardSQLQuestion: "hard_sql_questions.json"
}

def serialize_question(question):
    """
    SQLAlchemy 모델 객체를 JSON 직렬화 가능한 사전으로 변환합니다.
    
    Args:
        question: SQLAlchemy 모델 객체
        
    Returns:
        Dict: JSON 직렬화 가능한 사전
    """
    return {
        "id": question.id,
        "question": question.question,
        "answer": question.answer,
        "example": question.example,
        "difficulty": question.difficulty,
        "keywords": question.keywords
    }

def backup_questions(db: Session):
    """
    모든 문제 테이블의 데이터를 백업합니다.
    
    Args:
        db (Session): 데이터베이스 세션
    """
    # 백업 폴더 생성
    data_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(data_dir, "backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    # 현재 날짜와 시간으로 타임스탬프 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 모든 문제 테이블 백업
    for model, file_name in MODEL_FILE_MAPPING.items():
        questions = db.query(model).all()
        
        if not questions:
            print(f"{model.__name__}에 문제가 없습니다. 건너뜁니다.")
            continue
        
        # 객체를 직렬화하여 배열로 변환
        serialized_questions = [serialize_question(q) for q in questions]
        
        # 백업 파일 경로 생성 (타임스탬프 포함)
        backup_file = os.path.join(backup_dir, f"{timestamp}_{file_name}")
        
        # JSON 파일로 저장
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(serialized_questions, f, ensure_ascii=False, indent=2)
        
        print(f"{len(serialized_questions)}개의 {model.__name__} 문제를 {backup_file}에 백업했습니다.")

def export_questions(db: Session):
    """
    모든 문제 테이블의 데이터를 개별 JSON 파일로 내보냅니다.
    
    Args:
        db (Session): 데이터베이스 세션
    """
    data_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 모든 문제 테이블 내보내기
    for model, file_name in MODEL_FILE_MAPPING.items():
        questions = db.query(model).all()
        
        if not questions:
            print(f"{model.__name__}에 문제가 없습니다. 건너뜁니다.")
            continue
        
        # 객체를 직렬화하여 배열로 변환
        serialized_questions = [serialize_question(q) for q in questions]
        
        # 파일 경로 생성
        file_path = os.path.join(data_dir, file_name)
        
        # JSON 파일로 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(serialized_questions, f, ensure_ascii=False, indent=2)
        
        print(f"{len(serialized_questions)}개의 {model.__name__} 문제를 {file_path}에 내보냈습니다.")

def main():
    """
    메인 실행 함수
    """
    # 데이터베이스 연결
    db = next(get_db())
    
    try:
        # 백업 및 내보내기 수행
        backup_questions(db)
        export_questions(db)
        print("모든 문제 데이터 백업 및 내보내기가 완료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 