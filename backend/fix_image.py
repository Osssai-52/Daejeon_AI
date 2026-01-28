import sys
import os

# 현재 폴더를 파이썬 경로에 추가해서 app 모듈을 찾을 수 있게 함
sys.path.append(os.getcwd())

from app.main import SessionLocal
from app.db.models import Place

def update_daecheong_image():
    # 1. DB 세션(접속) 열기
    db = SessionLocal()
    
    try:
        # 2. '대청호반' 장소 찾기 (Select)
        # Place 테이블에서 이름이 '대청호반'인 것 하나만 (.first()) 가져옴
        target_place = db.query(Place).filter(Place.name == "대청호반").first()
        
        if not target_place:
            print("못 찾음")
            return

        print(f"찾음. 현재 저장된 이미지: {target_place.image_path}")

        # 3. 데이터 수정하기 (Update)
        NEW_IMAGE_URL = "https://image.newdaily.co.kr/site/data/img/2016/02/05/2016020500023_0.jpg" 
        
        target_place.image_path = NEW_IMAGE_URL
        
        # 4. 저장하기 (Commit) 
        db.commit()
        
        print(f"✅ '대청호반' 사진을 {NEW_IMAGE_URL} 로 수정함")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        db.rollback() 
    finally:
        # 5. 세션 닫기
        db.close()

if __name__ == "__main__":
    update_daecheong_image()