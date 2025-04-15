import re
import boto3
import json
from typing import Dict, Any, Optional, List
from app.services.keyword_extraction import filter_keywords_with_openai

# AWS Comprehend 클라이언트 초기화
comprehend = boto3.client('comprehend', region_name='ap-northeast-2')

def analyze_answer(user_answer: str, question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    사용자 답변을 분석하여 정답 여부를 판단하고 키워드를 추출합니다.
    
    Args:
        user_answer: 사용자가 입력한 답변
        question_data: 문제 데이터 (question, answer 등 포함)
        
    Returns:
        Dict: 분석 결과를 포함한 딕셔너리
            {
                "is_correct": bool,       # 정답 여부
                "error_message": str,     # 오답일 경우 메시지 (선택적)
                "keywords": List[str]     # 추출된 키워드 목록
            }
    """
    correct_answer = question_data.get("answer", "")
    
    # 정답이 없는 경우 처리
    if not correct_answer:
        return {
            "is_correct": False,
            "error_message": "문제에 설정된 정답이 없습니다.",
            "keywords": extract_keywords(user_answer)
        }
    
    # 정답 비교 로직
    # 1. 사용자 답변과 정답 전처리
    user_answer = user_answer.strip().lower()
    correct_answer = correct_answer.strip().lower()
    
    # 2. 간단한 정답 검증 (정답의 핵심 부분이 포함되어 있는지 확인)
    # 정답의 주요 부분을 추출 (예: 콤마로 구분된 리스트인 경우)
    if "," in correct_answer:
        correct_parts = [part.strip() for part in correct_answer.split(",")]
        # 주요 정답 부분 중 일정 비율 이상이 포함되어 있는지 확인
        matched_parts = sum(1 for part in correct_parts if part in user_answer)
        accuracy = matched_parts / len(correct_parts)
        
        # 70% 이상 일치하면 정답으로 간주
        if accuracy >= 0.7:
            return {
                "is_correct": True,
                "keywords": extract_keywords(user_answer)
            }
        else:
            return {
                "is_correct": False,
                "error_message": "정답에 필요한 핵심 요소가 부족합니다.",
                "keywords": extract_keywords(user_answer)
            }
    else:
        # 단일 문장 정답의 경우, 핵심 키워드가 포함되어 있는지 확인
        keywords = extract_core_keywords(correct_answer)
        matched_keywords = sum(1 for keyword in keywords if keyword in user_answer)
        
        if matched_keywords / max(len(keywords), 1) >= 0.7:
            return {
                "is_correct": True,
                "keywords": extract_keywords(user_answer)
            }
        else:
            return {
                "is_correct": False,
                "error_message": "정답과 일치하지 않습니다.",
                "keywords": extract_keywords(user_answer)
            }

def extract_core_keywords(text: str) -> List[str]:
    """
    텍스트에서 핵심 키워드를 추출합니다.
    간단한 구현으로, 불용어를 제외한 단어들을 반환합니다.
    
    Args:
        text: 키워드를 추출할 텍스트
        
    Returns:
        List[str]: 추출된 키워드 목록
    """
    # 간단한 한국어 불용어 리스트 (필요에 따라 확장)
    stopwords = {'있다', '이다', '하다', '그리고', '또한', '그러나', '하지만', '때문에', '따라서', '그래서', '등', '및', '이', '그', '저', '이런', '그런', '저런'}
    
    # 단어 분리 (공백, 마침표, 쉼표 등을 기준으로)
    words = re.findall(r'\w+', text)
    
    # 불용어 제거 및 중복 제거
    keywords = [word for word in words if word not in stopwords and len(word) > 1]
    return list(set(keywords))

def extract_keywords(text: str) -> List[str]:
    """
    Amazon Comprehend를 사용하여 텍스트에서 키워드를 추출하고,
    OpenAI GPT 모델로 필터링합니다.
    
    Args:
        text: 키워드를 추출할 텍스트
        
    Returns:
        List[str]: 추출된 키워드 목록
    """
    try:
        # Amazon Comprehend API를 사용하여 핵심 구문 추출
        response = comprehend.detect_key_phrases(
            Text=text,
            LanguageCode='ko'  # 한국어 텍스트
        )
        
        # 구문에서 키워드 추출
        keywords = []
        for phrase in response.get('KeyPhrases', []):
            # 신뢰도가 70% 이상인 구문만 사용
            if phrase.get('Score', 0) > 0.7:
                # 구문에서 불용어 제거 후 키워드 저장
                keywords.append(phrase.get('Text', '').strip())
        
        # 백업: Comprehend에서 키워드가 추출되지 않을 경우 기본 방법 사용
        if not keywords:
            keywords = extract_core_keywords(text)
        
        # OpenAI GPT로 키워드 필터링
        filtered_keywords = filter_keywords_with_openai(text, keywords, 'ko')
            
        # 최대 5개 키워드로 제한
        return filtered_keywords[:5]
        
    except Exception as e:
        print(f"Comprehend 키워드 추출 오류: {str(e)}")
        # 오류 발생 시 기본 방법으로 키워드 추출
        return extract_core_keywords(text) 