from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Dict, Optional
from pydantic import BaseModel

from ..auth.cognito import cognito_auth, get_current_user
from ..models.database import get_db
from ..models.models import User

router = APIRouter(
    prefix="/users",
    tags=["사용자 정보"],
    responses={404: {"description": "Not found"}},
)

# 모델 정의
class UserInfoResponse(BaseModel):
    id: str
    username: str
    email: str
    user_work: bool
    last_work_date: Optional[datetime] = None
    test_date: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class TestDateUpdate(BaseModel):
    test_date: datetime

# 사용자 정보 조회 엔드포인트
@router.get("/me", response_model=UserInfoResponse)
async def get_user_info(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.cognito_id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    return user

# 학습 상태 업데이트 엔드포인트
@router.post("/work-status", response_model=Dict)
async def update_work_status(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.cognito_id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 오늘 날짜 가져오기
    today = datetime.now().date()
    
    # 마지막 학습 날짜가 오늘이 아니면 user_work를 True로 설정
    if not user.last_work_date or user.last_work_date.date() != today:
        user.user_work = True
        user.last_work_date = datetime.now()
        db.commit()
        return {"message": "오늘의 학습이 완료되었습니다."}
    else:
        return {"message": "이미 오늘의 학습을 완료했습니다."}

# 시험 일정 설정 엔드포인트
@router.post("/test-date", response_model=Dict)
async def set_test_date(
    test_date: TestDateUpdate,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.cognito_id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    user.test_date = test_date.test_date
    db.commit()
    return {"message": "시험 일정이 업데이트되었습니다."}

# D-day 계산 엔드포인트
@router.get("/d-day", response_model=Dict)
async def get_d_day(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.cognito_id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    if not user.test_date:
        return {"d_day": None, "message": "시험 일정이 설정되지 않았습니다."}
    
    # 현재 날짜와 시험 일정의 차이를 일 단위로 계산
    today = datetime.now().date()
    test_day = user.test_date.date()
    delta = (test_day - today).days
    
    return {
        "d_day": delta,
        "test_date": user.test_date,
        "message": f"시험까지 D-{delta}일 남았습니다." if delta > 0 else "시험일입니다!" if delta == 0 else f"시험일로부터 {abs(delta)}일이 지났습니다."
    } 