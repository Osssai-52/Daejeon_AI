import os
from typing import List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv   
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import httpx 
from jose import jwt 

from app.services.ai_service import ai_instance
from app.db.models import Place, User 
from app.utils import sort_by_shortest_path, calculate_distance
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
import uvicorn

# 1. 환경변수 로딩
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY") 
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "http://localhost:3000/oauth")
SECRET_KEY = os.getenv("SECRET_KEY", "secret_key_backup") # 없을 경우 대비해 임시값 설정
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# DB 연결 체크
if not DATABASE_URL:
    print("❌ 에러: .env 파일을 못 찾거나 DATABASE_URL이 없어!")

app = FastAPI()

# 2. CORS 설정 (프론트엔드 연결 허용)
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
# 🔑 [로그인] 카카오 로그인 & 회원가입 API (수정됨!)
# ---------------------------------------------------------
@app.post("/auth/kakao")
async def kakao_login(auth_req: KakaoAuthRequest, db: Session = Depends(get_db)):
    # [디버깅] 현재 설정값 확인
    print(f"👀 [확인] 서버 API 키: |{KAKAO_REST_API_KEY}|")
    print(f"👀 [확인] 리다이렉트 URI: |{KAKAO_REDIRECT_URI}|")
    print(f"🔑 받은 인가 코드: {auth_req.code[:10]}...") 

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
        
        # [수정] 실패 시 카카오가 보낸 에러 메시지를 터미널에 출력
        if token_res.status_code != 200:
            print(f"❌ 카카오 토큰 발급 실패! 상태코드: {token_res.status_code}")
            print(f"❌ 에러 내용: {token_res.text}") # 여기가 범인을 알려줌
            raise HTTPException(status_code=400, detail="카카오 토큰 발급 실패")
        
        access_token = token_res.json().get("access_token")

        # B. 사용자 정보 요청
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        user_headers = {"Authorization": f"Bearer {access_token}"}
        
        user_res = await client.get(user_info_url, headers=user_headers)
        if user_res.status_code != 200:
            print(f"❌ 유저 정보 요청 실패: {user_res.text}")
            raise HTTPException(status_code=400, detail="카카오 유저 정보 가져오기 실패")
        
        # C. 데이터 파싱
        user_data = user_res.json()
        kakao_id = str(user_data.get("id")) # ID는 문자열로 관리하는 게 안전함
        properties = user_data.get("properties", {})
        kakao_account = user_data.get("kakao_account", {})
        
        nickname = properties.get("nickname", "이름없음")
        profile_image = properties.get("profile_image", "")
        email = kakao_account.get("email", "")

        print(f"✅ 카카오 로그인 성공: {nickname} (ID: {kakao_id})")

    # D. DB 저장 또는 업데이트
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    if not user:
        new_user = User(
            kakao_id=kakao_id,
            nickname=nickname,
            profile_image=profile_image,
            email=email,
            created_at=str(datetime.now()) # 혹은 datetime.now() 그대로 사용 (DB 모델에 따라 다름)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user
        print("🎉 신규 회원 가입 완료!")
    else:
        # 정보가 바뀌었을 수 있으니 업데이트
        user.nickname = nickname
        user.profile_image = profile_image
        db.commit()
        print("👋 기존 회원 로그인 성공!")

    # E. 우리 서비스 전용 JWT 토큰 발급
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
# 🍞 [기존 기능] 유잼 탐지기
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "🍞 대전 유잼 탐지기 서버 정상 가동 중! 🍞"}

@app.post("/analyze")
async def analyze_image(
    files: List[UploadFile] = File(...),
    current_lat: float = Form(36.3325), 
    current_lng: float = Form(127.4342) 
):
    print(f"📸 분석 시작... (사진 {len(files)}장)")
    
    db = SessionLocal()
    raw_candidates = []
    seen_names = set()

    try:
        for file in files:
            content = await file.read()
            user_vector = ai_instance.image_to_vector(content)
            
            if user_vector is None: continue

            # DB에서 유사한 장소 검색 (pgvector)
            distance_col = Place.embedding.cosine_distance(user_vector).label("distance")
            stmt = select(Place, distance_col).order_by(distance_col).limit(10)
            results = db.execute(stmt).all() 

            for row in results:
                place, distance = row
                
                if place.name in seen_names: continue

                if distance < 0.45: # 유사도 기준 (취향껏 조절 가능)
                    raw_candidates.append({
                        "name": place.name,
                        "description": place.description,
                        "address": place.address,   
                        "lat": place.latitude,
                        "lng": place.longitude,
                        "similarity": float(distance) 
                    })
                    seen_names.add(place.name)

        if not raw_candidates:
            return {"status": "fail", "message": "비슷한 곳을 못 찾겠어요 😭"}
        
        # 브랜드 필터링 (성심당 등 중복 제거 로직)
        final_recommendations = []
        brand_groups = {"성심당": []} 
        
        for place in raw_candidates:
            is_brand = False
            for brand_name in brand_groups.keys():
                if brand_name in place["name"]:
                    brand_groups[brand_name].append(place)
                    is_brand = True
                    break
            if not is_brand:
                final_recommendations.append(place)
        
        for brand_name, branches in brand_groups.items():
            if branches:
                # 현재 위치에서 가장 가까운 지점 하나만 추천
                best_branch = min(
                    branches,
                    key=lambda p: calculate_distance(current_lat, current_lng, p['lat'], p['lng'])
                )
                final_recommendations.append(best_branch)

        # 최단 거리 순 정렬
        sorted_recommendations = sort_by_shortest_path(current_lat, current_lng, final_recommendations)

        return {
            "status": "success",
            "start_point": {"lat": current_lat, "lng": current_lng},
            "data": sorted_recommendations 
        }

    finally:
        db.close()
        
@app.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"count": len(users), "users": users}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)