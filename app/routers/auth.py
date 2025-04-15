from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr, Field

from ..auth import cognito
from ..models.database import get_db
from ..models.models import User

router = APIRouter(
    prefix="/auth",
    tags=["인증"],
    responses={404: {"description": "Not found"}},
)

# OAuth2 비밀번호 기반 인증 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# 모델 정의
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserConfirm(BaseModel):
    username: str
    confirmation_code: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    id_token: str
    refresh_token: Optional[str] = None
    expires_in: int
    token_type: str

class PasswordReset(BaseModel):
    username: str

class PasswordResetConfirm(BaseModel):
    username: str
    confirmation_code: str
    new_password: str = Field(..., min_length=8)

class PasswordChange(BaseModel):
    previous_password: str
    proposed_password: str = Field(..., min_length=8)

# 회원가입 엔드포인트
@router.post("/register", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Cognito에 사용자 등록
    result = cognito.sign_up(user.username, user.password, user.email)
    
    # 데이터베이스에 사용자 정보 저장
    db_user = User(
        username=user.username,
        email=user.email,
        cognito_id=result["user_sub"]
    )
    db.add(db_user)
    db.commit()
    
    return {"message": "회원가입 성공. 이메일 인증이 필요합니다.", "user_id": db_user.id}

# 이메일 확인 엔드포인트
@router.post("/confirm-email", response_model=Dict)
async def confirm_email(user_confirm: UserConfirm):
    result = cognito.confirm_sign_up(user_confirm.username, user_confirm.confirmation_code)
    return result

# 로그인 엔드포인트
@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    result = cognito.sign_in(form_data.username, form_data.password)
    return result

# 직접 JSON으로 로그인하는 엔드포인트 추가 (Swagger UI 테스트용)
@router.post("/login-json", response_model=TokenResponse)
async def login_json(user: UserLogin):
    result = cognito.sign_in(user.username, user.password)
    return result

# 로그아웃 엔드포인트
@router.post("/logout", response_model=Dict)
async def logout(token: str = Depends(oauth2_scheme)):
    """
    현재 인증된 사용자를 로그아웃 처리합니다.
    액세스 토큰이 필요합니다.
    """
    result = cognito.sign_out(token)
    return result

# 토큰 갱신 엔드포인트
@router.post("/refresh-token", response_model=Dict)
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    result = cognito.refresh_token(refresh_token)
    return result

# 비밀번호 변경 엔드포인트
@router.post("/change-password", response_model=Dict)
async def change_password(
    password_change: PasswordChange,
    token: str = Depends(oauth2_scheme)
):
    result = cognito.change_password(
        token,
        password_change.previous_password,
        password_change.proposed_password
    )
    return result

# 비밀번호 재설정 요청 엔드포인트
@router.post("/forgot-password", response_model=Dict)
async def forgot_password(user: PasswordReset):
    result = cognito.forgot_password(user.username)
    return result

# 비밀번호 재설정 확인 엔드포인트
@router.post("/confirm-forgot-password", response_model=Dict)
async def confirm_forgot_password(reset_data: PasswordResetConfirm):
    result = cognito.confirm_forgot_password(
        reset_data.username,
        reset_data.confirmation_code,
        reset_data.new_password
    )
    return result

# 현재 사용자 정보 엔드포인트
@router.get("/me", response_model=Dict)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user_claims = cognito.cognito_auth.verify_token(token)
    return {
        "username": user_claims.get("username", ""),
        "email": user_claims.get("email", ""),
        "sub": user_claims.get("sub", "")
    } 