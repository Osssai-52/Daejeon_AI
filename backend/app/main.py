# backend/app/main.py
from fastapi import FastAPI, UploadFile, File
from app.services.ai_service import ai_instance
from app.db.models import Place
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import uvicorn

app = FastAPI()

DATABASE_URL = "postgresql://postgres.lejcuodzqwfhsnbtkbco:HAKSIKMUKJA260116@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@app.get("/")
def read_root():
    return {"message": "🍞 대전 유잼 탐지기 서버 정상 가동 중! 🍞"}

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    print("📸 분석 시작...")
    content = await file.read()
    user_vector = ai_instance.image_to_vector(content)
    
    if user_vector is None:
        return {"status": "error", "message": "이미지 분석 실패"}

    db = SessionLocal()
    try:
        distance_col = Place.embedding.cosine_distance(user_vector).label("distance")
        
        # 상위 5개까지 가져오기
        stmt = select(Place, distance_col).order_by(distance_col).limit(5)
        results = db.execute(stmt).all() 

        if not results:
            return {"status": "error", "message": "DB에 데이터가 없어"}

        # 결과를 리스트에 담기
        recommendations = []
        
        for row in results:
            place, distance = row
            
            # 커트라인 체크 (0.45 안쪽인 애들만)
            if distance < 0.45:
                recommendations.append({
                    "name": place.name,
                    "description": place.description,
                    "address": place.address,
                    "distance": float(distance) # 이건 '유사도' 거리임 (0에 가까울수록 비슷)
                })

        # 결과가 하나라도 있으면 성공!
        if len(recommendations) > 0:
            return {
                "status": "success",
                "data": recommendations 
            }
        else:
            return {
                "status": "fail",
                "message": "비슷한 곳을 못 찾겠어요"
            }

    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)