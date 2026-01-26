import os
from typing import List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv   
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx 
from jose import jwt 

from app.services.ai_service import ai_instance
from app.services.recommend_service import recommend_service
from app.db.models import Place, User, Visit, Base
from app.utils import calculate_distance
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import uvicorn

# 1. 환경변수 로딩
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY") 
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "http://localhost:3000/oauth")
SECRET_KEY = os.getenv("SECRET_KEY", "secret_key_backup") 
ALGORITHM = os.getenv("ALGORITHM", "HS256")

if not DATABASE_URL:
    print("❌ 에러: .env 파일을 못 찾거나 DATABASE_URL이 없어!")

app = FastAPI()

# 2. CORS 설정
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:5500", 
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. DB 세션 설정
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class KakaoAuthRequest(BaseModel):
    code: str 

# ---------------------------------------------------------
# 🔑 [로그인] 카카오 로그인 & 회원가입 API
# ---------------------------------------------------------
@app.post("/auth/kakao")
async def kakao_login(auth_req: KakaoAuthRequest, db: Session = Depends(get_db)):
    print(f"👀 [확인] 서버 API 키: |{KAKAO_REST_API_KEY}|")
    
    async with httpx.AsyncClient() as client:
        # A. 토큰 요청
        token_url = "https://kauth.kakao.com/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": auth_req.code,
        }
        
        token_res = await client.post(token_url, headers=headers, data=data)
        
        if token_res.status_code != 200:
            print(f"❌ 카카오 토큰 발급 실패: {token_res.text}")
            raise HTTPException(status_code=400, detail="카카오 토큰 발급 실패")
        
        access_token = token_res.json().get("access_token")

        # B. 사용자 정보 요청
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        user_headers = {"Authorization": f"Bearer {access_token}"}
        
        user_res = await client.get(user_info_url, headers=user_headers)
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="카카오 유저 정보 가져오기 실패")
        
        # C. 데이터 파싱
        user_data = user_res.json()
        kakao_id = str(user_data.get("id"))
        properties = user_data.get("properties", {})
        kakao_account = user_data.get("kakao_account", {})
        
        nickname = properties.get("nickname", "이름없음")
        profile_image = properties.get("profile_image", "")
        email = kakao_account.get("email", "")

    # D. DB 저장 또는 업데이트
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        new_user = User(
            kakao_id=kakao_id,
            nickname=nickname,
            profile_image=profile_image,
            email=email,
            created_at=str(datetime.now())
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user
        print("🎉 신규 회원 가입 완료!")
    else:
        user.nickname = nickname
        user.profile_image = profile_image
        db.commit()
        print("👋 기존 회원 로그인 성공!")

    # E. JWT 토큰 발급
    expire = datetime.utcnow() + timedelta(days=7) 
    jwt_payload = {"sub": str(user.id), "exp": expire}
    app_token = jwt.encode(jwt_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "status": "success",
        "token": app_token, 
        "user": {
            "id": user.id,
            "nickname": user.nickname,
            "profile_image": user.profile_image
        }
    }

# ---------------------------------------------------------
# 🍞 [기능 1~3] 취향 분석 및 맞춤 추천
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "🍞 대전 유잼 탐지기 서버 정상 가동 중! 🍞"}

@app.post("/analyze")
async def analyze_image(
    files: List[UploadFile] = File(...),
    current_lat: float = Form(36.3325), 
    current_lng: float = Form(127.4342),
    db: Session = Depends(get_db)
):
    print(f"📸 분석 시작... (사진 {len(files)}장)")
    
    # 로직을 서비스 계층으로 위임 (Code Refactoring)
    sorted_recommendations = await recommend_service.get_recommendations(
        db, files, current_lat, current_lng
    )

    if not sorted_recommendations:
        return {"status": "fail", "message": "비슷한 곳을 못 찾겠어요 😭"}

    return {
        "status": "success",
        "start_point": {"lat": current_lat, "lng": current_lng},
        "data": sorted_recommendations 
    }

# ---------------------------------------------------------
# 🚩 [기능 5] 방문 인증 (나만의 지도 만들기)
# ---------------------------------------------------------
@app.post("/visits")
def verify_visit(
    user_id: int = Form(...),
    place_id: int = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    사용자가 특정 장소 근처(500m)에 도착해서 사진을 찍으면 '방문 완료' 처리
    """
    # 1. 장소 정보 조회
    target_place = db.query(Place).filter(Place.id == place_id).first()
    if not target_place:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")

    # 2. 거리 검증 (GPS 조작 방지)
    distance = calculate_distance(lat, lng, target_place.latitude, target_place.longitude)
    print(f"📍 현재 위치와 {target_place.name} 거리: {distance:.2f}km")

    if distance > 0.5: # 500m 이내여야 인증 성공
        return {
            "status": "fail", 
            "message": f"장소와 너무 멀어요! ({int(distance*1000)}m 거리)"
        }

    # 3. 방문 기록 저장
    # (실제 서비스에선 이미지를 S3에 올리고 그 URL을 저장해야 함. 여기선 파일명만 임시 저장)
    new_visit = Visit(
        user_id=user_id, 
        place_id=place_id, 
        visit_image=file.filename # 임시
    )
    db.add(new_visit)
    db.commit()
    
    return {
        "status": "success", 
        "message": f"🚩 {target_place.name} 방문 인증 완료! 나만의 지도에 기록되었습니다."
    }

@app.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"count": len(users), "users": users}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)