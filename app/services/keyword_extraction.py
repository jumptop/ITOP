import os
import boto3
import json
from typing import List, Dict
from dotenv import load_dotenv
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import openai

# 환경 변수 로드
load_dotenv()

# AWS 설정
REGION = os.getenv("AWS_REGION")

# OpenAI API 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# Comprehend 클라이언트 생성
comprehend = boto3.client('comprehend', region_name=REGION)

# NLTK 데이터 다운로드 (최초 1회만)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# 한국어 불용어
KOREAN_STOPWORDS = {
    '있는', '하는', '그', '및', '이', '그리고', '또는', '또한', '수', '등', '이런', '저런',
    '하며', '하고', '하지만', '그런', '이런', '저런', '것', '이것', '저것', '그것', '이는', 
    '있다', '하다', '이다', '된다', '에서', '으로', '에게', '뿐만', '아니라', '만약', '때문에'
}

def filter_keywords_with_openai(text: str, raw_keywords: List[str], language_code: str = 'ko') -> List[str]:
    """
    OpenAI GPT를 사용하여 Comprehend로 추출한 키워드를 필터링합니다.
    
    Args:
        text (str): 원본 텍스트
        raw_keywords (List[str]): Comprehend로 추출한 초기 키워드 목록
        language_code (str): 텍스트의 언어 코드
        
    Returns:
        List[str]: 필터링된 고품질 키워드 목록
    """
    if not raw_keywords:
        return []
    
    try:
        # OpenAI API 호출을 위한 프롬프트 구성
        prompt = f"""
당신은 기술 문서에서 핵심 개념과 전문 용어를 정확하게 추출하는 전문가입니다. 
다음 텍스트에서 정보처리기능사 시험과 관련된 정보 기술 분야의 핵심 용어와 개념을 추출해주세요.

다음 가이드라인을 따라주세요:
1. 명사 형태의 전문 용어만 선택하세요 (예: 운영체제, TCP/IP, 데이터베이스)
2. 다음은 제외하세요:
   - 일반적인 단어 ('의', '위한', '있는', '것', '주요' 등)
   - 동사나 형용사 (운영하다, 구성되는 등)
   - 문장 형식(예시 : 관계형 데이터베이스의 설계 X 관계형 O, 데이터베이스 O)
3. 전문적이고 기술적인 용어에 집중하세요
4. 최대 3개의 핵심 키워드만 선택하세요
5. 각 키워드는 명확하고 독립적인 개념이어야 합니다
6. 동의어나 유사 개념은 하나만 선택하세요

원본 텍스트:
{text}

추출된 초기 키워드 목록:
{', '.join(raw_keywords)}

응답 형식:
콤마로 구분된 핵심 키워드만 나열하세요. 다른 설명이나 문장을 추가하지 마세요.
"""
        
        # OpenAI API 호출
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 문제에서 핵심 단어 키워드만 추출하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=100
        )
        
        # 응답 파싱
        filtered_keywords_text = response.choices[0].message.content.strip()
        
        # 키워드 목록으로 변환
        filtered_keywords = [keyword.strip() for keyword in filtered_keywords_text.split(',') if keyword.strip()]
        
        # 빈 응답이면 원래 키워드 반환
        if not filtered_keywords:
            return raw_keywords
            
        return filtered_keywords
    except Exception as e:
        print(f"OpenAI 키워드 필터링 중 오류 발생: {str(e)}")
        # 오류 발생 시 원래 키워드 반환
        return raw_keywords

def extract_key_phrases(text: str, language_code: str = 'ko') -> List[str]:
    """
    AWS Comprehend를 사용하여 텍스트에서 핵심 구문을 추출합니다.
    
    Args:
        text (str): 키워드를 추출할 텍스트
        language_code (str): 텍스트의 언어 코드 (ko: 한국어, en: 영어)
        
    Returns:
        List[str]: 추출된 키워드 목록
    """
    if not text.strip():
        return []
    
    # 텍스트 길이 제한 (Comprehend는 최대 5KB까지 처리)
    if len(text) > 5000:
        text = text[:5000]
    
    try:
        response = comprehend.detect_key_phrases(
            Text=text,
            LanguageCode=language_code
        )
        
        # 키워드 추출 및 중요도 순으로 정렬
        key_phrases = [phrase['Text'] for phrase in response.get('KeyPhrases', [])]
        
        # OpenAI로 키워드 필터링
        filtered_key_phrases = filter_keywords_with_openai(text, key_phrases, language_code)
        
        return filtered_key_phrases
    except Exception as e:
        print(f"AWS Comprehend 키워드 추출 중 오류 발생: {str(e)}")
        # 오류 발생 시 내부 로직으로 백업 키워드 추출
        return _fallback_extract_key_phrases(text, 5)

def _fallback_extract_key_phrases(text, top_n=5):
    """
    AWS Comprehend 사용이 불가능할 때 로컬에서 키워드를 추출하는 백업 함수
    
    Args:
        text (str): 키워드를 추출할 텍스트
        top_n (int): 반환할 상위 키워드 수
        
    Returns:
        list: 추출된 키워드 리스트
    """
    # 1. 특수문자 제거 및 소문자 변환
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # 2. 한글과 영어 단어 추출
    korean_words = re.findall(r'[가-힣]+', text)
    english_text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    
    # 3. 영어 단어 토큰화 및 불용어 제거
    english_tokens = word_tokenize(english_text)
    english_stop_words = set(stopwords.words('english'))
    english_filtered = [word for word in english_tokens if word not in english_stop_words and len(word) > 2]
    
    # 4. 한글 단어 불용어 제거
    korean_filtered = [word for word in korean_words if word not in KOREAN_STOPWORDS and len(word) > 1]
    
    # 5. 모든 단어 결합
    all_filtered = english_filtered + korean_filtered
    
    # 6. 단어 빈도수 계산
    word_freq = Counter(all_filtered)
    
    # 7. 상위 키워드 반환
    return [k for k, v in word_freq.most_common(top_n)]

def extract_entities(text: str, language_code: str = 'ko') -> List[Dict]:
    """
    AWS Comprehend를 사용하여 텍스트에서 개체(이름, 장소, 날짜 등)를 추출합니다.
    
    Args:
        text (str): 개체를 추출할 텍스트
        language_code (str): 텍스트의 언어 코드 (ko: 한국어, en: 영어)
        
    Returns:
        List[Dict]: 추출된 개체 목록 (유형과 텍스트 포함)
    """
    if not text.strip():
        return []
    
    # 텍스트 길이 제한 (Comprehend는 최대 5KB까지 처리)
    if len(text) > 5000:
        text = text[:5000]
    
    try:
        response = comprehend.detect_entities(
            Text=text,
            LanguageCode=language_code
        )
        
        entities = [
            {'type': entity['Type'], 'text': entity['Text']} 
            for entity in response.get('Entities', [])
        ]
        
        return entities
    except Exception as e:
        print(f"AWS Comprehend 개체 추출 중 오류 발생: {str(e)}")
        return []

def detect_dominant_language(text: str) -> str:
    """
    AWS Comprehend를 사용하여 텍스트의 주요 언어를 감지합니다.
    
    Args:
        text (str): 언어를 감지할 텍스트
        
    Returns:
        str: 감지된 언어의 코드 (예: 'ko', 'en')
    """
    if not text.strip():
        return 'ko'  # 기본값은 한국어
    
    # 텍스트 길이 제한 (Comprehend는 최대 5KB까지 처리)
    if len(text) > 5000:
        text = text[:5000]
    
    try:
        response = comprehend.detect_dominant_language(Text=text)
        
        languages = response.get('Languages', [])
        if languages:
            # 가장 높은 점수의 언어 코드 반환
            return languages[0]['LanguageCode']
        
        return 'ko'  # 기본값은 한국어
    except Exception as e:
        print(f"AWS Comprehend 언어 감지 중 오류 발생: {str(e)}")
        return 'ko'

def extract_keywords_from_answer(answer_text: str) -> List[str]:
    """
    사용자 답변에서 키워드를 추출하여 유사 문제 추천에 사용합니다.
    
    Args:
        answer_text (str): 사용자의 답변 텍스트
        
    Returns:
        List[str]: 추출된 키워드 목록
    """
    # 언어 감지
    language_code = detect_dominant_language(answer_text)
    
    # 키워드 추출
    key_phrases = extract_key_phrases(answer_text, language_code)
    
    # 개체 추출 (중요한 명사 등)
    entities = extract_entities(answer_text, language_code)
    entity_texts = [entity['text'] for entity in entities]
    
    # 키워드 및 개체 합치기 (중복 제거)
    all_keywords = list(set(key_phrases + entity_texts))
    
    # OpenAI로 최종 필터링
    final_keywords = filter_keywords_with_openai(answer_text, all_keywords, language_code)
    
    return final_keywords 