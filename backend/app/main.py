import os
import uuid 
from typing import List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv   
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import httpx 
from jose import jwt 
import boto3 

from app.services.ai_service import ai_instance
from app.services.recommend_service import recommend_service
from app.db.models import Place, User, Visit, Route, RoutePlace, PlacePhoto, Base
from app.utils import calculate_distance, sort_by_shortest_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import uvicorn

# 1. 환경변수 로딩
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY") 
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "http://localhost:8080/oauth")
SECRET_KEY = os.getenv("SECRET_KEY", "secret_key_backup") 
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# [S3] AWS 환경변수 로딩
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2") 

if not DATABASE_URL:
    print("❌ 에러: .env 파일을 못 찾거나 DATABASE_URL이 없음")

# [S3] 클라이언트 연결 (서버 켜질 때 한 번만 연결)
try:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    print("✅ S3 클라이언트 연결 성공!")
except Exception as e:
    print(f"❌ S3 연결 실패: {e}")

app = FastAPI()

# 2. CORS 설정
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
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

# [S3] 이미지 업로드 도우미 함수
def upload_to_s3(file: UploadFile) -> str:
    try:
        # 1. 파일 내용 읽기
        file_content = file.file.read()
        
        # 2. 고유한 파일명 만들기 (덮어쓰기 방지)
        file_ext = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # 3. S3 버킷에 업로드
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=unique_filename,
            Body=file_content,
            ContentType=file.content_type
        )
        
        # 4. 접근 가능한 URL 생성 (Public Read 권한 필요)
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        return image_url

    except Exception as e:
        print(f"❌ S3 업로드 중 에러 발생: {e}")
        raise HTTPException(status_code=500, detail="이미지 서버 업로드 실패")

# 토큰 인증을 위한 스킴 정의
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/kakao")

class KakaoAuthRequest(BaseModel):
    code: str 

class KakaoUserInfo(BaseModel):
    id: int
    nickname: str
    profile_image: str

class KakaoAuthResponse(BaseModel):
    status: str
    token: str
    user: KakaoUserInfo

class RoutePlaceSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    lat: float
    lng: float

class RouteRequest(BaseModel):
    start_lat: float
    start_lng: float
    places: List[RoutePlaceSchema]

class RouteResponse(BaseModel):
    status: str
    start_point: dict
    data: list

class RoutePlacePayload(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    lat: float
    lng: float

class RouteHistoryCreateRequest(BaseModel):
    start_lat: float
    start_lng: float
    places: List[RoutePlacePayload]

class RouteHistoryListResponse(BaseModel):
    status: str
    routes: list

class PlacePhotoResponse(BaseModel):
    status: str
    place_id: int
    image_url: Optional[str] = None

class PlacePhotoListItem(BaseModel):
    place_id: int
    image_url: str
    updated_at: datetime

class PlacePhotoListResponse(BaseModel):
    status: str
    photos: list

# 🔑 [로그인] 카카오 로그인 & 회원가입 API
@app.post(
    "/auth/kakao",
    response_model=KakaoAuthResponse,
    responses={
        200: {
            "description": "Kakao login success",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwgImV4cCI6MTczODAwMDAwMH0.signature",
                        "user": {
                            "id": 1,
                            "nickname": "홍길동",
                            "profile_image": "https://k.kakaocdn.net/dn/example_profile.jpg"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "카카오 토큰 발급 실패"}
                }
            }
        }
    }
)

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

# 🍞 취향 분석 및 맞춤 추천
@app.get("/")
def read_root():
    return {"message": "🍞 대전 유잼 탐지기 서버 정상 가동 중! 🍞"}

@app.post("/route", response_model=RouteResponse)
def calculate_route(req: RouteRequest):
    """
    장소 좌표 리스트를 받아 최적(가까운 순) 경로로 정렬해 반환.
    """
    if not req.places:
        return {"status": "fail", "message": "places가 비어 있습니다."}

    places_payload = [
        {
            "id": p.id,
            "name": p.name,
            "lat": p.lat,
            "lng": p.lng,
        }
        for p in req.places
    ]

    sorted_places = sort_by_shortest_path(req.start_lat, req.start_lng, places_payload)
    return {
        "status": "success",
        "start_point": {"lat": req.start_lat, "lng": req.start_lng},
        "data": sorted_places,
    }

@app.post("/routes")
def create_route_history(
    req: RouteHistoryCreateRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    if not req.places:
        return {"status": "fail", "message": "places가 비어 있습니다."}

    new_route = Route(
        user_id=user_id,
        start_lat=req.start_lat,
        start_lng=req.start_lng
    )
    db.add(new_route)
    db.commit()
    db.refresh(new_route)

    route_places = []
    for idx, p in enumerate(req.places):
        route_places.append(RoutePlace(
            route_id=new_route.id,
            order_index=idx,
            place_id=p.id,
            name=p.name,
            description=p.description,
            image_url=p.image_url,
            lat=p.lat,
            lng=p.lng
        ))
    db.add_all(route_places)
    db.commit()

    return {
        "status": "success",
        "route_id": new_route.id
    }

@app.get("/routes", response_model=RouteHistoryListResponse)
def get_route_history(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    routes = db.query(Route).filter(Route.user_id == user_id).order_by(Route.created_at.desc()).all()
    result = []
    for route in routes:
        places_payload = []
        for p in route.places:
            places_payload.append({
                "id": p.place_id,
                "name": p.name,
                "description": p.description,
                "image_url": p.image_url,
                "lat": p.lat,
                "lng": p.lng,
                "order_index": p.order_index
            })

        result.append({
            "route_id": route.id,
            "created_at": route.created_at,
            "start_point": {"lat": route.start_lat, "lng": route.start_lng},
            "places": places_payload
        })

    return {"status": "success", "routes": result}

@app.delete("/routes/{route_id}")
def delete_route_history(
    route_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    route = db.query(Route).filter(Route.id == route_id, Route.user_id == user_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="경로를 찾을 수 없습니다.")

    db.query(RoutePlace).filter(RoutePlace.route_id == route_id).delete()
    db.delete(route)
    db.commit()

    return {"status": "success", "deleted_route_id": route_id}

@app.post("/analyze")
async def analyze_image(
    files: List[UploadFile] = File(...),
    current_lat: float = Form(36.3325), 
    current_lng: float = Form(127.4342),
    db: Session = Depends(get_db)
):
    print(f"📸 분석 시작... (사진 {len(files)}장)")
    
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

# 🚩 방문 인증 (나만의 지도 만들기 - S3 저장 적용!)
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
    S3에 이미지를 업로드하고 URL을 DB에 저장함.
    """
    # 1. 장소 정보 조회
    target_place = db.query(Place).filter(Place.id == place_id).first()
    if not target_place:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")

    # 2. 거리 검증
    distance = calculate_distance(lat, lng, target_place.latitude, target_place.longitude)
    print(f"📍 현재 위치와 {target_place.name} 거리: {distance:.2f}km")

    if distance > 0.5: 
        return {
            "status": "fail", 
            "message": f"장소와 너무 멀어요! ({int(distance*1000)}m 거리)"
        }

    # 3. [수정됨] S3에 이미지 업로드
    print("🚀 S3 업로드 시작...")
    uploaded_image_url = upload_to_s3(file)
    print(f"✅ S3 업로드 완료: {uploaded_image_url}")

    # 4. 방문 기록 저장 (URL 저장)
    new_visit = Visit(
        user_id=user_id, 
        place_id=place_id, 
        visit_image=uploaded_image_url
    )
    db.add(new_visit)
    db.commit()
    
    return {
        "status": "success", 
        "message": f"🚩 {target_place.name} 방문 인증 완료! 나만의 지도에 기록되었습니다.",
        "image_url": uploaded_image_url
    }

@app.post("/places/{place_id}/photo", response_model=PlacePhotoResponse)
def upload_place_photo(
    place_id: int,
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    거리 제한 없이, 특정 장소에 대해 사용자 1장 사진 업로드 (유저-장소 1장 유지).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다.")

    uploaded_image_url = upload_to_s3(file)

    photo = db.query(PlacePhoto).filter(
        PlacePhoto.user_id == user_id,
        PlacePhoto.place_id == place_id
    ).first()

    if photo:
        photo.image_url = uploaded_image_url
    else:
        photo = PlacePhoto(
            user_id=user_id,
            place_id=place_id,
            image_url=uploaded_image_url
        )
        db.add(photo)

    db.commit()

    return {"status": "success", "place_id": place_id, "image_url": uploaded_image_url}

@app.get("/places/{place_id}/photo", response_model=PlacePhotoResponse)
def get_place_photo(
    place_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    특정 장소에 대해 내가 올린 사진 1장을 조회.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    photo = db.query(PlacePhoto).filter(
        PlacePhoto.user_id == user_id,
        PlacePhoto.place_id == place_id
    ).first()

    if not photo:
        return {"status": "success", "place_id": place_id, "image_url": None}

    return {"status": "success", "place_id": place_id, "image_url": photo.image_url}

@app.get("/places/photos", response_model=PlacePhotoListResponse)
def get_place_photos(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    내가 올린 장소 사진들을 한 번에 조회 (place_id -> image_url 맵핑용).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    photos = db.query(PlacePhoto).filter(PlacePhoto.user_id == user_id).all()
    payload = [
        {
            "place_id": p.place_id,
            "image_url": p.image_url,
            "updated_at": p.updated_at
        }
        for p in photos
    ]

    return {"status": "success", "photos": payload}

# 🗺️ 나만의 지도 조회 (GET)
@app.get("/my-map")
def get_my_visits(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # 1. 토큰에서 사용자 ID 확인
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # 2. 내 방문 기록 + 장소 정보 조회
    results = db.query(Visit, Place).join(Place, Visit.place_id == Place.id).filter(Visit.user_id == user_id).all()
    
    # 3. 데이터 포맷팅
    my_map_data = []
    for visit, place in results:
        my_map_data.append({
            "visit_id": visit.id,
            "place_name": place.name,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "visited_at": visit.visited_at,
            "photo": visit.visit_image # S3 URL 반환
        })
        
    return {"count": len(my_map_data), "visits": my_map_data}

@app.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"count": len(users), "users": users}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
