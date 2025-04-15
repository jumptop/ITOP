from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from .models.database import engine, Base, get_db
from .routers import auth, questions, admin, user_info, api

# 환경 변수 로드
load_dotenv()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="정보처리기능사 시험 앱 API",
    description="정보처리기능사 시험 준비를 위한 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 설정
origins = [
    "http://localhost",
    "http://localhost:3000",  # React 개발 서버
    "http://localhost:8080",  # Vue 개발 서버
    "http://localhost:4200",  # Angular 개발 서버
    "http://localhost:8081",  # Android 에뮬레이터
    "https://정보처리기능사.kr",  # 프로덕션 서버
    "*"  # 개발 중에는 모든 오리진 허용
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(admin.router)
app.include_router(user_info.router)
app.include_router(api.router)  # 새로 만든 간소화된 API 라우터 등록

@app.get("/")
async def root():
    return {
        "message": "정보처리기능사 시험 앱 API에 오신 것을 환영합니다.",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/info")
async def info(db: Session = Depends(get_db)):
    try:
        # 데이터베이스 연결 테스트
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "app_name": "정보처리기능사 시험 앱 API",
        "version": "1.0.0",
        "database_status": db_status,
        "environment": os.getenv("ENV", "development")
    }

if __name__ == "__main__":
    import uvicorn
    # 개발 환경에서 실행 (디버깅 가능)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 