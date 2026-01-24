import sys
import os

sys.path.append(os.getcwd())

from dotenv import load_dotenv

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.db.models import Place
from app.services.ai_service import ai_instance

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def search_similar_place(image_filename):
    print(f"🔎 검색 시작: {image_filename}")
    
    # 1. images 폴더에서 사진 읽기
    file_path = os.path.join("images", image_filename)
    
    if not os.path.exists(file_path):
        print(f"❌ 오류: 'images' 폴더에 '{image_filename}' 파일이 없습니다.")
        return

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    # 2. AI로 변환 (벡터 만들기)
    user_vector = ai_instance.image_to_vector(img_bytes)

    if user_vector is None:
        print("❌ 오류: AI가 이미지를 분석하지 못했습니다.")
        return

    # 3. DB에서 가장 비슷한 장소 찾기
    db = SessionLocal()
    
    # 코사인 거리(Distance)가 가장 가까운 순서대로 정렬해서 1등만 가져옴
    distance_col = Place.embedding.cosine_distance(user_vector).label("distance")
    stmt = select(Place, distance_col).order_by(distance_col).limit(1)
    
    result = db.execute(stmt).first()

    if result:
        place, distance = result
        print("\n" + "="*30)
        print(f"🎉 추천 결과: {place.name}")
        print(f"📝 설명: {place.description}")
        print(f"📊 유사도 거리: {distance:.4f} (0에 가까울수록 똑같음)")
        print("="*30 + "\n")
        
        if distance < 0.25:
            print("✅ 판정: 여기 맞습니다! (확실함)")
        elif distance < 0.4:
            print("🤔 판정: 긴가민가하지만 여기 같아요.")
        else:
            print("❌ 판정: 비슷한 곳을 못 찾겠어요.")
    else:
        print("❌ DB에 데이터가 하나도 없습니다.")
    
    db.close()

if __name__ == "__main__":
    # ★ 테스트하고 싶은 사진 이름을 여기에 적으세요!
    # 예: images 폴더 안에 있는 '성심당.jpeg'로 테스트
    search_similar_place("07gyejoksan1.jpg")
