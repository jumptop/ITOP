import os
from openai import OpenAI
from typing import Dict, Tuple, List
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성
client = OpenAI(api_key=OPENAI_API_KEY)

def verify_answer(question: str, correct_answer: str, user_answer: str) -> Tuple[bool, float, str]:
    """
    ChatGPT API를 사용하여 사용자의 답변을 검증합니다.
    
    Args:
        question (str): 문제 텍스트
        correct_answer (str): 데이터베이스에 저장된 정답
        user_answer (str): 사용자가 입력한 답변
        
    Returns:
        Tuple[bool, float, str]: (정답 여부, 유사도 점수, 피드백)
    """
    if not user_answer.strip():
        return False, 0.0, "답변이 입력되지 않았습니다."
    
    # 프롬프트 설계
    prompt = f"""
    당신은 정보처리기능사 시험의 채점자입니다. 다음 문제와 모범 답안, 그리고 사용자의 답안을 비교하여 채점해 주세요.
    
    [문제]
    {question}
    
    [모범 답안]
    {correct_answer}
    
    [사용자 답안]
    {user_answer}
    
    다음 항목을 평가해 주세요:
    1. 정확성: 사용자의 답변이 모범 답안과 내용적으로 일치하는지 평가
    2. 유사도: 0(전혀 관련 없음)부터 1(완전히 일치)까지의 점수로 평가
    3. 피드백: 사용자 답변에 대한 구체적인 피드백 제공
    
    JSON 형식으로 결과를 반환해 주세요:
    {{
        "is_correct": true/false,
        "similarity_score": 0.0~1.0,
        "feedback": "피드백 내용"
    }}
    """
    
    try:
        # ChatGPT API 호출
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "당신은 정보처리기능사 시험 채점 도우미입니다."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # 응답 파싱
        result = response.choices[0].message.content
        import json
        parsed_result = json.loads(result)
        
        is_correct = parsed_result.get("is_correct", False)
        similarity_score = parsed_result.get("similarity_score", 0.0)
        feedback = parsed_result.get("feedback", "답변을 평가할 수 없습니다.")
        
        return is_correct, similarity_score, feedback
    except Exception as e:
        print(f"ChatGPT API 호출 중 오류 발생: {str(e)}")
        
        # 간단한 문자열 유사도 계산으로 폴백
        # 실제 구현에서는 더 정교한 알고리즘 사용 필요
        similarity = simple_string_similarity(correct_answer, user_answer)
        is_correct = similarity > 0.8
        
        return is_correct, similarity, "시스템 오류로 인해 기본 유사도 검사를 수행했습니다."

def simple_string_similarity(str1: str, str2: str) -> float:
    """
    두 문자열 간의 간단한 유사도를 계산합니다. (API 실패 시 폴백 기능)
    Jaccard 유사도: 두 집합의 교집합 크기를 합집합 크기로 나눈 값
    
    Args:
        str1 (str): 첫 번째 문자열
        str2 (str): 두 번째 문자열
        
    Returns:
        float: 0.0~1.0 사이의 유사도 점수
    """
    # 공백 제거 및 소문자 변환
    str1 = str1.lower().replace(" ", "")
    str2 = str2.lower().replace(" ", "")
    
    # 각 문자열을 문자 집합으로 변환
    set1 = set(str1)
    set2 = set(str2)
    
    # 교집합과 합집합 크기 계산
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    # Jaccard 유사도 계산
    if union == 0:
        return 1.0 if len(str1) == 0 and len(str2) == 0 else 0.0
    
    return intersection / union

def get_similar_questions(keywords: List[str], category: str, count: int = 5) -> List[Dict]:
    """
    키워드와 카테고리를 기반으로 ChatGPT API를 사용해 유사 문제를 생성합니다.
    
    Args:
        keywords (List[str]): 키워드 목록
        category (str): 문제 카테고리 (OS, DB 등)
        count (int): 생성할 문제 수
        
    Returns:
        List[Dict]: 유사 문제 목록 (질문과 답변 포함)
    """
    if not keywords:
        return []
    
    # 프롬프트 설계
    prompt = f"""
    당신은 정보처리기능사 시험 문제 생성기입니다. 다음 키워드와 카테고리를 바탕으로 {count}개의 유사 문제와 답변을 생성해 주세요.
    
    [카테고리] {category}
    [키워드] {', '.join(keywords)}
    
    다음과 같은 JSON 형식으로 반환해 주세요:
    [
        {{
            "question": "질문 내용",
            "answer": "모범 답안",
            "difficulty": 1-5 사이의 난이도 (5가 가장 어려움)
        }},
        ...
    ]
    """
    
    try:
        # ChatGPT API 호출
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "당신은 정보처리기능사 시험 문제 생성 전문가입니다."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # 응답 파싱
        result = response.choices[0].message.content
        import json
        parsed_result = json.loads(result)
        
        # 리스트 형태로 반환되는지 확인
        if isinstance(parsed_result, list):
            return parsed_result
        elif isinstance(parsed_result, dict) and 'questions' in parsed_result:
            return parsed_result.get('questions', [])
        else:
            # 적절한 형식이 아니면 빈 리스트 반환
            return []
    except Exception as e:
        print(f"ChatGPT API 호출 중 오류 발생: {str(e)}")
        return [] 