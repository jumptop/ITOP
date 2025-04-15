import re
import string
from typing import Dict, Any, List, Tuple
import openai
import os
from dotenv import load_dotenv
from difflib import SequenceMatcher

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def preprocess_text(text: str) -> str:
    """텍스트 전처리: 소문자 변환, 특수문자 제거, 공백 정규화"""
    if not text:
        return ""
    # 소문자 변환
    text = text.lower()
    # 구두점 제거
    text = text.translate(str.maketrans('', '', string.punctuation))
    # 여러 공백을 하나로 치환
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_similarity(text1: str, text2: str) -> float:
    """두 텍스트 간의 유사도 계산(0~1 사이 값)"""
    # 전처리
    text1 = preprocess_text(text1)
    text2 = preprocess_text(text2)
    
    # 시퀀스 매처 사용하여 유사도 계산
    matcher = SequenceMatcher(None, text1, text2)
    return matcher.ratio()

def get_keywords_from_text(text: str) -> List[str]:
    """텍스트에서 핵심 키워드 추출"""
    words = preprocess_text(text).split()
    # 간단한 불용어 제거 (영어, 한국어)
    stopwords = {'the', '그', '이', '그리고', '또한', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'at'}
    keywords = [word for word in words if word not in stopwords and len(word) > 1]
    return keywords

def compare_answers_simple(user_answer: str, correct_answer: str) -> Tuple[bool, float, str]:
    """
    사용자 답변과 정답을 간단히 비교
    
    Returns:
        Tuple[bool, float, str]: (정답 여부, 유사도 점수, 피드백)
    """
    # 텍스트 유사도 계산
    similarity = calculate_similarity(user_answer, correct_answer)
    
    # 키워드 비교
    correct_keywords = set(get_keywords_from_text(correct_answer))
    user_keywords = set(get_keywords_from_text(user_answer))
    
    # 정답의 핵심 키워드 중 일치하는 비율 계산
    if correct_keywords:
        keyword_match_ratio = len(correct_keywords.intersection(user_keywords)) / len(correct_keywords)
    else:
        keyword_match_ratio = 0.0
    
    # 최종 점수 계산 (유사도와 키워드 매칭 비율의 가중 평균)
    final_score = 0.3 * similarity + 0.7 * keyword_match_ratio
    
    # 정답 여부 판단 (70% 이상일 경우 정답으로 간주)
    is_correct = final_score >= 0.7
    
    # 피드백 메시지 생성
    if is_correct:
        feedback = "정답입니다!"
    elif final_score >= 0.5:
        feedback = "부분적으로 정답이지만, 좀 더 정확한 답변이 필요합니다."
    else:
        feedback = "틀렸습니다. 정답을 다시 확인해보세요."
    
    return is_correct, final_score, feedback

def compare_answers_advanced(user_answer: str, correct_answer: str, question: str = "", example: str = None) -> Dict[str, Any]:
    """
    OpenAI API를 사용하여 고급 답변 비교 및 분석
    
    Args:
        user_answer: 사용자 답변
        correct_answer: 정답
        question: 문제 내용 (선택사항)
        example: 보기 항목 (선택사항)
    
    Returns:
        Dict: 분석 결과 {
            "is_correct": bool,
            "score": float,
            "feedback": str,
            "missing_points": List[str],
            "incorrect_points": List[str]
        }
    """
    try:
        # 보기 항목 포함 여부에 따른 프롬프트 구성
        example_text = ""
        if example:
            example_text = f"""
보기 항목:
{example}
"""
        
        # OpenAI API 호출을 위한 프롬프트 구성
        prompt = f"""
정보처리기능사 시험 문제의 답변을 평가해주세요.

문제: {question}
{example_text}
정답:
{correct_answer}

사용자 답변:
{user_answer}

다음 형식으로 답변을 평가해주세요:
1. 정확도 점수(0~100): 사용자 답변이 정답과 얼마나 일치하는지 점수로 평가
2. 정답 여부(맞음/틀림): 70점 이상이면 맞음, 그 미만이면 틀림
3. 누락된 핵심 개념: 정답에는 있지만 사용자 답변에 누락된 중요 개념
4. 잘못된 내용: 사용자 답변에 있는 오류나 잘못된 내용
5. 피드백: 사용자가 답변을 개선할 수 있는 간단한 조언

JSON 형식으로 응답해주세요:
```json
{{
  "score": 점수,
  "is_correct": true/false,
  "missing_points": ["누락된 개념1", "누락된 개념2", ...],
  "incorrect_points": ["잘못된 내용1", "잘못된 내용2", ...],
  "feedback": "피드백 메시지"
}}
```
"""
        
        # 시스템 메시지 구성 - 보기 항목 포함 여부에 따라 다르게
        system_content = "너는 정보처리기능사 시험 채점 전문가입니다. 객관적으로 답변을 평가하고 정확한 점수와 피드백을 제공합니다."
        if example:
            system_content += " 문제와 정답뿐만 아니라 보기 항목도 함께 고려하여 평가합니다."
        
        # OpenAI API 호출
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        # 응답 파싱
        result = response.choices[0].message.content
        # JSON 파싱
        import json
        result_json = json.loads(result)
        
        # 필요한 필드 설정
        result_json["score"] = float(result_json.get("score", 0)) / 100  # 0~1 범위로 정규화
        
        return result_json
    
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {str(e)}")
        # API 오류 시 간단한 비교 방식으로 폴백
        is_correct, score, feedback = compare_answers_simple(user_answer, correct_answer)
        return {
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
            "missing_points": [],
            "incorrect_points": []
        }

def evaluate_answer(user_answer: str, question_data: Dict[str, Any], use_advanced: bool = True) -> Dict[str, Any]:
    """
    사용자 답변 평가 통합 함수 (모든 기능 통합)
    
    Args:
        user_answer: 사용자 답변
        question_data: 문제 데이터 (question, answer, example 등 포함)
        use_advanced: 고급 평가(OpenAI) 사용 여부 (기본값: True)
    
    Returns:
        Dict: 평가 결과
    """
    # 입력 검증
    if not user_answer or not question_data or "answer" not in question_data:
        return {
            "is_correct": False,
            "score": 0.0,
            "feedback": "답변 또는 문제 데이터가 없습니다.",
            "missing_points": [],
            "incorrect_points": []
        }
    
    correct_answer = question_data.get("answer", "").strip()
    question = question_data.get("question", "")
    example = question_data.get("example", None)  # 보기 항목 추출
    
    # 1. 간단한 정확도 계산을 먼저 수행 (정확히 일치하면 즉시 정답 처리)
    if user_answer.strip() == correct_answer:
        return {
            "is_correct": True,
            "score": 1.0,
            "feedback": "정답입니다!",
            "missing_points": [],
            "incorrect_points": [],
            "correct_answer": correct_answer
        }
    
    # 2. 보기 항목 처리: 숫자 또는 항목 내용 모두 정답으로 인정
    if example:
        options = example.split('\n')
        for option in options:
            match = re.match(r'(\d+)\.\s*(.*)', option.strip())
            if match:
                option_num, option_text = match.groups()
                option_text = option_text.strip()
                
                # 정답이 번호(예: "5")인 경우
                if correct_answer == option_num:
                    # 사용자가 번호 또는 해당 텍스트를 입력한 경우
                    if user_answer.strip() == option_num or preprocess_text(user_answer) == preprocess_text(option_text):
                        return {
                            "is_correct": True,
                            "score": 1.0,
                            "feedback": "정답입니다!",
                            "missing_points": [],
                            "incorrect_points": [],
                            "correct_answer": correct_answer,
                            "example": example
                        }
                
                # 정답이 텍스트(예: "SNMP")인 경우
                elif preprocess_text(correct_answer) == preprocess_text(option_text):
                    # 사용자가 번호 또는 해당 텍스트를 입력한 경우
                    if user_answer.strip() == option_num or preprocess_text(user_answer) == preprocess_text(option_text):
                        return {
                            "is_correct": True,
                            "score": 1.0,
                            "feedback": "정답입니다!",
                            "missing_points": [],
                            "incorrect_points": [],
                            "correct_answer": correct_answer,
                            "example": example
                        }
    
    # 3. 문제 조건 분석
    # 영문 약어 요구 조건 확인
    if ("영문 약어" in question or "영문약어" in question) and re.search(r'[A-Z]{2,}', correct_answer):
        # 영문 약어가 정답인데 사용자가 입력하지 않은 경우
        if not re.search(r'[A-Z]{2,}', user_answer):
            return {
                "is_correct": False,
                "score": 0.1,
                "feedback": "영문 약어로 작성해야 합니다.",
                "missing_points": ["영문 약어 형식"],
                "incorrect_points": [],
                "correct_answer": correct_answer,
                "example": example if example else None
            }
    
    # 4. 나열형 문제 확인 (예: ㄱ,ㄴ,ㄷ 또는 1,2,3 형식)
    if "," in correct_answer or "，" in correct_answer:
        correct_items = re.split(r'[,，]', correct_answer)
        correct_items = [item.strip() for item in correct_items]
        
        user_items = re.split(r'[,，]', user_answer)
        user_items = [item.strip() for item in user_items]
        
        # 순서와 개수가 정확히 일치하는지 확인
        if len(correct_items) == len(user_items) and all(preprocess_text(c) == preprocess_text(u) for c, u in zip(correct_items, user_items)):
            return {
                "is_correct": True,
                "score": 1.0,
                "feedback": "정답입니다!",
                "missing_points": [],
                "incorrect_points": [],
                "correct_answer": correct_answer,
                "example": example if example else None
            }
    
    # 5. OpenAI API를 사용한 고급 평가
    if use_advanced:
        try:
            # 보기 항목 포함 여부에 따른 프롬프트 구성
            example_text = ""
            if example:
                example_text = f"""
보기 항목:
{example}
"""
            
            # OpenAI API 호출을 위한 프롬프트 구성
            prompt = f"""
정보처리기능사 시험 문제의 답변을 평가해주세요.

문제: {question}
{example_text}
정답: {correct_answer}

사용자 답변: {user_answer}

답변 평가 시 다음 사항을 고려해주세요:
1. 보기가 있는 경우: 보기의 번호(예: "1")나 내용(예: "TCP") 둘 다 정답으로 인정합니다.
2. 영문 약어로 작성하라는 지시가 있는 경우: 영문 약어 형식을 확인합니다.
3. 나열형 문제의 경우: 답안의 순서와 개수가 정확한지 확인합니다.

다음 형식으로 답변을 평가해주세요:
1. 정확도 점수(0~100): 사용자 답변이 정답과 얼마나 일치하는지 점수로 평가
2. 정답 여부(true/false): 70점 이상이면 true, 그 미만이면 false
3. 누락된 핵심 개념: 정답에는 있지만 사용자 답변에 누락된 중요 개념
4. 잘못된 내용: 사용자 답변에 있는 오류나 잘못된 내용
5. 피드백: 사용자가 답변을 개선할 수 있는 간단한 조언

JSON 형식으로 응답해주세요:
```
{{
  "score": 점수(0-100),
  "is_correct": true/false,
  "missing_points": ["누락된 개념1", "누락된 개념2", ...],
  "incorrect_points": ["잘못된 내용1", "잘못된 내용2", ...],
  "feedback": "피드백 메시지"
}}
```
"""
            
            # 시스템 메시지 구성
            system_content = "너는 정보처리기능사 시험 채점 전문가입니다. 객관적으로 답변을 평가하고 정확한 점수와 피드백을 제공합니다."
            
            # OpenAI API 호출
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            # 응답 파싱
            result = response.choices[0].message.content
            
            # JSON 파싱
            import json
            result_json = json.loads(result)
            
            # 필요한 필드 설정
            result_json["score"] = float(result_json.get("score", 0)) / 100  # 0~1 범위로 정규화
            result_json["correct_answer"] = correct_answer
            if example:
                result_json["example"] = example
            
            return result_json
            
        except Exception as e:
            print(f"OpenAI API 호출 중 오류 발생: {str(e)}")
            # API 오류 시 간단한 비교 방식으로 폴백 - 아래로 계속 진행
    
    # 6. 간단한 평가 (OpenAI 실패 또는 use_advanced=False인 경우)
    # 텍스트 유사도 계산
    matcher = SequenceMatcher(None, preprocess_text(user_answer), preprocess_text(correct_answer))
    similarity = matcher.ratio()
    
    # 키워드 비교
    correct_words = preprocess_text(correct_answer).split()
    user_words = preprocess_text(user_answer).split()
    
    common_words = set(correct_words).intersection(set(user_words))
    if correct_words:
        keyword_match_ratio = len(common_words) / len(correct_words)
    else:
        keyword_match_ratio = 0.0
    
    # 최종 점수 계산 (유사도와 키워드 매칭 비율의 가중 평균)
    final_score = 0.4 * similarity + 0.6 * keyword_match_ratio
    
    # 정답 여부 판단 (70% 이상일 경우 정답으로 간주)
    is_correct = final_score >= 0.7
    
    # 피드백 메시지 생성
    if is_correct:
        feedback = "정답입니다!"
    elif final_score >= 0.5:
        feedback = "부분적으로 정답이지만, 좀 더 정확한 답변이 필요합니다."
    else:
        feedback = "틀렸습니다. 정답을 다시 확인해보세요."
    
    # 결과 반환
    return {
        "is_correct": is_correct,
        "score": final_score,
        "feedback": feedback,
        "missing_points": [],
        "incorrect_points": [],
        "correct_answer": correct_answer,
        "example": example if example else None
    } 