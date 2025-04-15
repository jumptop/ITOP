import os
from dotenv import load_dotenv
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from app.models.database import Base
from app.models.models import (
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion,
    ProgramQuestion, AppTestQuestion, AppDefectQuestion,
    BaseSQLQuestion, HardSQLQuestion
)
from app.services.keyword_extraction import extract_key_phrases

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KeywordUpdater")

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

# 데이터베이스 연결 URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 엔진 및 세션 생성
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모든 문제 유형 모델
QUESTION_MODELS = [
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion,
    ProgramQuestion, AppTestQuestion, AppDefectQuestion,
    BaseSQLQuestion, HardSQLQuestion
]

def update_keywords_for_all_questions():
    """
    모든 문제 테이블의 키워드를 AWS Comprehend와 OpenAI를 사용하여 업데이트합니다.
    """
    session = SessionLocal()
    
    try:
        total_updated = 0
        
        for model in QUESTION_MODELS:
            model_name = model.__name__
            logger.info(f"{model_name} 테이블의 키워드 업데이트 시작...")
            
            # 모든 질문 조회
            questions = session.query(model).all()
            logger.info(f"{len(questions)}개의 질문을 처리합니다.")
            
            # 각 질문의 키워드 업데이트
            for i, question in enumerate(questions):
                # 질문과 답변 결합
                text = f"{question.question} {question.answer}"
                
                # 키워드 추출
                extracted_keywords = extract_key_phrases(text, 'ko')
                
                # 키워드를 쉼표로 구분된 문자열로 변환
                keywords_str = ", ".join(extracted_keywords)
                
                # 키워드 업데이트
                question.keywords = keywords_str
                
                # 진행 상황 로깅 (10개마다)
                if (i + 1) % 10 == 0 or i == len(questions) - 1:
                    logger.info(f"{model_name}: {i + 1}/{len(questions)} 완료")
                
                total_updated += 1
            
            # 변경 사항 커밋
            session.commit()
            logger.info(f"{model_name} 테이블 업데이트 완료!")
        
        logger.info(f"총 {total_updated}개의 질문 키워드가 업데이트되었습니다.")
    
    except Exception as e:
        logger.error(f"키워드 업데이트 중 오류 발생: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("AWS Comprehend와 OpenAI를 사용한 키워드 업데이트 시작...")
    update_keywords_for_all_questions()
    logger.info("모든 키워드 업데이트가 완료되었습니다.") 