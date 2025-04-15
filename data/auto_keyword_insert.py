#!/usr/bin/env python
import os
import csv
import uuid
from dotenv import load_dotenv
import boto3

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트 경로 추가
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 필요한 모듈 import
from app.models.database import SessionLocal
from app.models.models import (
    OSQuestion, DBQuestion, NetworkQuestion, AlgorithmQuestion,
    ProgramQuestion, AppTestQuestion, AppDefectQuestion,
    BaseSQLQuestion, HardSQLQuestion
)
from app.services.keyword_extraction import extract_key_phrases, detect_dominant_language

def insert_questions_from_csv(csv_file, question_type):
    """
    CSV 파일에서 문제 데이터를 읽고 데이터베이스에 삽입하는 함수
    
    Args:
        csv_file (str): CSV 파일 경로
        question_type (str): 문제 유형 ('OS', 'DB', 'Network' 등)
    """
    # 데이터베이스 세션 생성
    db = SessionLocal()
    
    # 문제 유형에 따른 모델 클래스 선택
    model_map = {
        'OS': OSQuestion,
        'DB': DBQuestion,
        'Network': NetworkQuestion,
        'Algorithm': AlgorithmQuestion,
        'Program': ProgramQuestion,
        'AppTest': AppTestQuestion,
        'AppDefect': AppDefectQuestion,
        'BaseSQL': BaseSQLQuestion,
        'HardSQL': HardSQLQuestion
    }
    
    question_model = model_map.get(question_type)
    if not question_model:
        print(f"오류: 유효하지 않은 문제 유형 '{question_type}'")
        return
    
    # CSV 파일 읽기
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = 0
            
            for row in reader:
                # 필수 필드 확인
                if not row.get('question_text') or not row.get('answer'):
                    print(f"경고: 필수 필드 누락된 행 건너뜀: {row}")
                    continue
                
                # 난이도 처리
                difficulty = 1  # 기본값
                if row.get('difficulty'):
                    try:
                        difficulty = int(row['difficulty'])
                    except ValueError:
                        print(f"경고: 유효하지 않은 난이도, 기본값 1 사용: {row}")
                
                # 키워드 자동 추출
                text = row['question_text'] + " " + row['answer']
                # 언어 감지
                language_code = detect_dominant_language(text)
                # AWS Comprehend로 키워드 추출
                extracted_keywords = extract_key_phrases(text, language_code)
                keywords = ",".join(extracted_keywords[:5])  # 상위 5개 키워드만 사용
                print(f"AWS Comprehend로 키워드 자동 추출: {keywords}")
                
                # 문제 객체 생성
                question = question_model(
                    id=row['id'],
                    question=row['question_text'],
                    answer=row['answer'],
                    example=row.get('example', ''),
                    difficulty=difficulty,
                    keywords=keywords
                )
                
                # 데이터베이스에 추가
                db.add(question)
                count += 1
                
                # 매 10개 항목마다 커밋
                if count % 10 == 0:
                    db.commit()
                    print(f"{count}개 항목 삽입 완료")
            
            # 남은 항목 커밋
            if count % 10 != 0:
                db.commit()
            
            print(f"총 {count}개의 {question_type} 문제가 데이터베이스에 삽입되었습니다.")
    
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        db.rollback()
    finally:
        db.close()

def test_aws_comprehend():
    """AWS Comprehend 설정 테스트"""
    try:
        # AWS 설정 확인
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION")
        
        if not aws_access_key or not aws_secret_key:
            print("오류: AWS 자격 증명이 설정되지 않았습니다. .env 파일을 확인하세요.")
            return False
            
        # Comprehend 클라이언트 생성
        comprehend = boto3.client(
            'comprehend',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # 간단한 텍스트로 키워드 추출 테스트
        test_text = "AWS Comprehend는 자연어 처리 서비스입니다. 이 서비스는 텍스트에서 통찰력을 추출하는 데 도움이 됩니다."
        response = comprehend.detect_key_phrases(
            Text=test_text,
            LanguageCode='ko'
        )
        
        if 'KeyPhrases' in response:
            print("\n===== AWS Comprehend 테스트 성공 =====")
            print("추출된 키워드:")
            for phrase in response['KeyPhrases']:
                print(f"- {phrase['Text']}")
            return True
        else:
            print("오류: AWS Comprehend 응답에 KeyPhrases가 없습니다.")
            return False
            
    except Exception as e:
        print(f"AWS Comprehend 테스트 중 오류 발생: {str(e)}")
        return False

def insert_questions_from_json(json_file, question_type):
    """
    JSON 파일에서 문제 데이터를 읽고 AWS Comprehend로 키워드를 추출하여 데이터베이스에 삽입하는 함수
    
    Args:
        json_file (str): JSON 파일 경로
        question_type (str): 문제 유형 ('OS', 'DB', 'Network' 등)
    """
    import json
    
    # 데이터베이스 세션 생성
    db = SessionLocal()
    
    # 문제 유형에 따른 모델 클래스 선택
    model_map = {
        'OS': OSQuestion,
        'DB': DBQuestion,
        'Network': NetworkQuestion,
        'Algorithm': AlgorithmQuestion,
        'Program': ProgramQuestion,
        'AppTest': AppTestQuestion,
        'AppDefect': AppDefectQuestion,
        'BaseSQL': BaseSQLQuestion,
        'HardSQL': HardSQLQuestion
    }
    
    question_model = model_map.get(question_type)
    if not question_model:
        print(f"오류: 유효하지 않은 문제 유형 '{question_type}'")
        return
    
    # JSON 파일 읽기
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            questions = json.load(file)
            count = 0
            
            for item in questions:
                # 필수 필드 확인
                if not item.get('question') or not item.get('answer'):
                    print(f"경고: 필수 필드 누락된 항목 건너뜀: {item}")
                    continue
                
                # 난이도 처리
                difficulty = 1  # 기본값
                if item.get('difficulty'):
                    try:
                        difficulty = int(item['difficulty'])
                    except ValueError:
                        print(f"경고: 유효하지 않은 난이도, 기본값 1 사용: {item}")
                
                # 키워드 자동 추출
                text = item['question'] + " " + item['answer']
                # 언어 감지
                language_code = detect_dominant_language(text)
                # AWS Comprehend로 키워드 추출
                extracted_keywords = extract_key_phrases(text, language_code)
                keywords = ",".join(extracted_keywords[:5])  # 상위 5개 키워드만 사용
                print(f"AWS Comprehend로 키워드 자동 추출: {keywords}")
                
                # 문제 객체 생성
                question = question_model(
                    id=item['id'],
                    question=item['question'],
                    answer=item['answer'],
                    example=item.get('example', ''),
                    difficulty=difficulty,
                    keywords=keywords
                )
                
                # 데이터베이스에 추가
                db.add(question)
                count += 1
                
                # 매 10개 항목마다 커밋
                if count % 10 == 0:
                    db.commit()
                    print(f"{count}개 항목 삽입 완료")
            
            # 남은 항목 커밋
            if count % 10 != 0:
                db.commit()
            
            print(f"총 {count}개의 {question_type} 문제가 데이터베이스에 삽입되었습니다.")
    
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # AWS Comprehend 테스트
    if not test_aws_comprehend():
        print("AWS Comprehend 설정을 확인한 후 다시 시도하세요.")
        exit(1)
    
    # 현재 스크립트 위치 기준으로 JSON 파일 경로 설정
    data_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 모든 JSON 파일 처리
    file_types = [
        ("os_questions.json", "OS"),
        ("db_questions.json", "DB"),
        ("network_questions.json", "Network"),
        ("algorithm_questions.json", "Algorithm"),
        ("program_questions.json", "Program"),
        ("app_test_questions.json", "AppTest"),
        ("app_defect_questions.json", "AppDefect"),
        ("base_sql_questions.json", "BaseSQL"),
        ("hard_sql_questions.json", "HardSQL")
    ]
    
    for json_file, question_type in file_types:
        print(f"\n===== {question_type} 문제 데이터 삽입 =====")
        full_path = os.path.join(data_dir, json_file)
        if os.path.exists(full_path):
            insert_questions_from_json(full_path, question_type)
        else:
            print(f"오류: {full_path} 파일이 존재하지 않습니다.") 