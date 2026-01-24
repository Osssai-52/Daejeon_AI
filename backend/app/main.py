import os
from typing import List
from dotenv import load_dotenv  
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from app.services.ai_service import ai_instance
from app.db.models import Place
from app.utils import sort_by_shortest_path, calculate_distance
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import uvicorn

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ 에러: .env 파일을 못 찾거나 DATABASE_URL이 없어!")

app = FastAPI()

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

# DB 연결
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@app.get("/")
def read_root():
    return {"message": "🍞 대전 유잼 탐지기 서버 정상 가동 중! 🍞"}

@app.post("/analyze")
async def analyze_image(
    files: List[UploadFile] = File(...),
    current_lat: float = Form(36.3325), 
    current_lng: float = Form(127.4342) 
):
    print(f"📸 분석 시작... (사진 {len(files)}장, 출발지: {current_lat}, {current_lng})")
    
    db = SessionLocal()
    
    # 1. 일단 모든 후보를 다 모을 임시 리스트
    raw_candidates = []
    seen_names = set()

    try:
        # 사진마다 루프 돌면서 후보 찾기
        for file in files:
            content = await file.read()
            user_vector = ai_instance.image_to_vector(content)
            
            if user_vector is None:
                continue

            # 유사도 거리 계산
            distance_col = Place.embedding.cosine_distance(user_vector).label("distance")
            
            stmt = select(Place, distance_col).order_by(distance_col).limit(10)
            results = db.execute(stmt).all() 

            for row in results:
                place, distance = row
                
                # 완전 똑같은 지점(이름 기준) 중복 제거
                if place.name in seen_names:
                    continue

                if distance < 0.45:
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
            return {
                "status": "fail",
                "message": "비슷한 곳을 하나도 못 찾겠어요 😭"
            }
        
        # 브랜드 중복 제거 로직 (성심당 1곳만 남기기)
        final_recommendations = []
        brand_groups = {"성심당": []} 
        
        # 1. 분류하기
        for place in raw_candidates:
            is_brand = False
            for brand_name in brand_groups.keys():
                if brand_name in place["name"]:
                    brand_groups[brand_name].append(place)
                    is_brand = True
                    break
            
            if not is_brand:
                final_recommendations.append(place)
        
        # 2. 브랜드별로 가까운 1곳 뽑기
        for brand_name, branches in brand_groups.items():
            if branches:
                best_branch = min(
                    branches,
                    key=lambda p: calculate_distance(current_lat, current_lng, p['lat'], p['lng'])
                )
                final_recommendations.append(best_branch)

        # 최단 시간 경로로 '재정렬' & 시간 계산
        sorted_recommendations = sort_by_shortest_path(current_lat, current_lng, final_recommendations)

        return {
            "status": "success",
            "start_point": {"lat": current_lat, "lng": current_lng},
            "data": sorted_recommendations 
        }

    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)