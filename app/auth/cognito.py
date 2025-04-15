import os
import boto3
import json
import time
import logging
from botocore.exceptions import ClientError
from fastapi import HTTPException, Depends, status
from jose import jwk, jwt
from jose.utils import base64url_decode
from dotenv import load_dotenv
import requests
from typing import Dict, Optional, List

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# Cognito 설정
REGION = os.getenv("AWS_REGION")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")

# Cognito 클라이언트 생성
cognito_idp = boto3.client('cognito-idp', region_name=REGION)

# JWT 토큰 검증을 위한 함수
class CognitoAuth:
    def __init__(self):
        self.region = REGION
        self.user_pool_id = USER_POOL_ID
        self.app_client_id = APP_CLIENT_ID
        self.jwks = None
        self._load_jwks()

    def _load_jwks(self):
        keys_url = f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json'
        try:
            response = requests.get(keys_url)
            self.jwks = response.json()['keys']
        except Exception as e:
            print(f"Failed to load JWKS: {str(e)}")
            self.jwks = []

    def verify_token(self, token: str) -> Dict:
        # JWKS가 로드되지 않았다면 다시 로드
        if not self.jwks:
            self._load_jwks()

        # 토큰 헤더 파싱
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']

        # 해당 kid를 가진 키 찾기
        key_index = -1
        for i in range(len(self.jwks)):
            if kid == self.jwks[i]['kid']:
                key_index = i
                break

        if key_index == -1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public key not found in jwks.json"
            )

        # 공개 키 가져오기
        public_key = jwk.construct(self.jwks[key_index])
        
        # 토큰 검증을 위한 message와 signature 파싱
        message, encoded_signature = token.rsplit('.', 1)
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        
        # 토큰 서명 검증
        if not public_key.verify(message.encode('utf8'), decoded_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature verification failed"
            )
        
        # 클레임 가져오기
        claims = jwt.get_unverified_claims(token)
        
        # 토큰 만료 검증
        if claims.get('exp', 0) < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        # 토큰의 대상 검증
        if claims.get('client_id') != self.app_client_id and claims.get('aud') != self.app_client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token was not issued for this audience"
            )
        
        return claims

# 회원가입 함수
def sign_up(username: str, password: str, email: str) -> Dict:
    try:
        logger.info(f"회원가입 시도: {username}, {email}")
        logger.info(f"Cognito 클라이언트 설정: REGION={REGION}, APP_CLIENT_ID={APP_CLIENT_ID}")
        
        response = cognito_idp.sign_up(
            ClientId=APP_CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                }
            ]
        )
        logger.info(f"회원가입 성공: {response}")
        return {
            "message": "회원가입 성공. 이메일 인증이 필요합니다.",
            "user_sub": response["UserSub"]
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"회원가입 오류: {error_code} - {error_message}")
        logger.error(f"요청 정보: username={username}, email={email}")
        logger.error(f"전체 오류: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{error_code}: {error_message}"
        )
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"예상치 못한 오류: {str(e)}"
        )

# 이메일 인증 확인 함수
def confirm_sign_up(username: str, confirmation_code: str) -> Dict:
    try:
        cognito_idp.confirm_sign_up(
            ClientId=APP_CLIENT_ID,
            Username=username,
            ConfirmationCode=confirmation_code
        )
        return {"message": "이메일 인증이 완료되었습니다."}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{error_code}: {error_message}"
        )

# 로그인 함수
def sign_in(username: str, password: str) -> Dict:
    try:
        logger.info(f"로그인 시도: 사용자명 '{username}'")
        logger.info(f"Cognito 클라이언트 설정: REGION={REGION}, APP_CLIENT_ID={APP_CLIENT_ID}")
        
        # 인증 시도
        logger.info("USER_PASSWORD_AUTH 인증 흐름으로 로그인 시도")
        response = cognito_idp.initiate_auth(
            ClientId=APP_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        logger.info("로그인 성공")
        auth_result = response.get('AuthenticationResult', {})
        return {
            "access_token": auth_result.get('AccessToken'),
            "id_token": auth_result.get('IdToken'),
            "refresh_token": auth_result.get('RefreshToken'),
            "expires_in": auth_result.get('ExpiresIn'),
            "token_type": auth_result.get('TokenType')
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"로그인 오류: {error_code} - {error_message}")
        logger.error(f"요청 정보: username={username}")
        logger.error(f"전체 오류: {str(e)}")
        
        # NotAuthorizedException은 보통 잘못된 자격 증명이나 인증되지 않은 사용자를 의미
        # UserNotConfirmedException은 이메일 인증이 완료되지 않은 경우
        if error_code == 'UserNotConfirmedException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 인증이 완료되지 않았습니다. 이메일을 확인하여 인증을 완료해 주세요."
            )
        elif error_code == 'NotAuthorizedException' and "Incorrect username or password" in error_message:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자 이름 또는 비밀번호가 올바르지 않습니다."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{error_code}: {error_message}"
            )
    except Exception as e:
        logger.error(f"예상치 못한 로그인 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"예상치 못한 오류: {str(e)}"
        )

# 토큰 갱신 함수
def refresh_token(refresh_token: str) -> Dict:
    try:
        response = cognito_idp.initiate_auth(
            ClientId=APP_CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )
        
        auth_result = response.get('AuthenticationResult', {})
        return {
            "access_token": auth_result.get('AccessToken'),
            "id_token": auth_result.get('IdToken'),
            "expires_in": auth_result.get('ExpiresIn'),
            "token_type": auth_result.get('TokenType')
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{error_code}: {error_message}"
        )

# 비밀번호 변경 함수
def change_password(access_token: str, previous_password: str, proposed_password: str) -> Dict:
    try:
        cognito_idp.change_password(
            AccessToken=access_token,
            PreviousPassword=previous_password,
            ProposedPassword=proposed_password
        )
        return {"message": "비밀번호가 성공적으로 변경되었습니다."}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{error_code}: {error_message}"
        )

# 비밀번호 재설정 요청 함수
def forgot_password(username: str) -> Dict:
    try:
        cognito_idp.forgot_password(
            ClientId=APP_CLIENT_ID,
            Username=username
        )
        return {"message": "비밀번호 재설정 코드가 이메일로 전송되었습니다."}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{error_code}: {error_message}"
        )

# 비밀번호 재설정 확인 함수
def confirm_forgot_password(username: str, confirmation_code: str, new_password: str) -> Dict:
    try:
        cognito_idp.confirm_forgot_password(
            ClientId=APP_CLIENT_ID,
            Username=username,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        return {"message": "비밀번호가 성공적으로 재설정되었습니다."}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{error_code}: {error_message}"
        )

# 인증된 사용자 확인을 위한 의존성
cognito_auth = CognitoAuth()

def get_current_user(token: str = Depends(lambda: None)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 제공되지 않았습니다."
        )
    
    try:
        claims = cognito_auth.verify_token(token)
        return claims
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# 로그아웃 함수
def sign_out(access_token: str) -> Dict:
    """
    사용자의 액세스 토큰을 사용하여 Cognito에서 로그아웃 처리합니다.
    글로벌 로그아웃을 수행하여 사용자의 모든 디바이스에서 로그아웃합니다.
    
    Args:
        access_token (str): 사용자의 액세스 토큰
        
    Returns:
        Dict: 로그아웃 결과 메시지
    """
    try:
        logger.info("로그아웃 시도")
        
        # 글로벌 로그아웃 수행 (모든 디바이스에서 로그아웃)
        cognito_idp.global_sign_out(
            AccessToken=access_token
        )
        
        logger.info("로그아웃 성공")
        return {"message": "로그아웃 되었습니다."}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"로그아웃 오류: {error_code} - {error_message}")
        logger.error(f"전체 오류: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{error_code}: {error_message}"
        )
    except Exception as e:
        logger.error(f"예상치 못한 로그아웃 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"예상치 못한 오류: {str(e)}"
        ) 