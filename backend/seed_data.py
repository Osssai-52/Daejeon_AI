import os
import sys

sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Place
from app.services.ai_service import ai_instance

DATABASE_URL = "여기에 url 추가"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

IMAGE_FOLDER = "images" 

def init_db():
    print("🚀 DB 연결 및 초기화...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

def seed_places():
    db = SessionLocal()
    
    # 1. DB에 이미 있는 사진 목록 확인 (중복 방지)
    print("📋 기존 데이터 확인 중...")
    existing_images = set(db.scalars(select(Place.image_path)).all())
    
    grouped_places = [
        # 1-0. 성심당 본점 
        {
            "name": "성심당 본점",
            "addr": "대전 중구 대종로480번길 15",
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "튀김소보로와 명란바게트의 성지! 대전 필수 코스"},
                {"img": "01sungsim2.jpg",  "desc": "딸기시루 & 망고시루가 유명한 디저트 천국"},
                {"img": "01sungsim3.jpeg", "desc": "튀김소보로도 유명한 빵집"},
                {"img": "01sungsim4.jpeg", "desc": "보문산메아리와 명란바게트가 유명한 빵집"},
                {"img": "01sungsim5.jpg",  "desc": "성심당"},
            ]
        },
        # 1-1. 성심당 DCC점
        {
            "name": "성심당 DCC점",
            "addr": "대전 유성구 엑스포로 107 1층",
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "튀김소보로와 명란바게트의 성지! 대전 필수 코스"},
                {"img": "01sungsim2.jpg",  "desc": "딸기시루 & 망고시루가 유명한 디저트 천국"},
                {"img": "01sungsim3.jpeg", "desc": "튀김소보로도 유명한 빵집"},
                {"img": "01sungsim4.jpeg", "desc": "보문산메아리와 명란바게트가 유명한 빵집"},
                {"img": "01sungsim5.jpg",  "desc": "성심당"},
            ]
        },
        # 1-2. 성심당 대전역점
        {
            "name": "성심당 대전역점",
            "addr": "대전 동구 중앙로 215 2층",
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "튀김소보로와 명란바게트의 성지! 대전 필수 코스"},
                {"img": "01sungsim2.jpg",  "desc": "딸기시루 & 망고시루가 유명한 디저트 천국"},
                {"img": "01sungsim3.jpeg", "desc": "튀김소보로도 유명한 빵집"},
                {"img": "01sungsim4.jpeg", "desc": "보문산메아리와 명란바게트가 유명한 빵집"},
                {"img": "01sungsim5.jpg",  "desc": "성심당"},
            ]
        },
        # 1-3. 성심당 롯데백화점 대전점
        {
            "name": "성심당 롯데백화점 대전점",
            "addr": "대전 서구 계룡로 598 1층",
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "튀김소보로와 명란바게트의 성지! 대전 필수 코스"},
                {"img": "01sungsim2.jpg",  "desc": "딸기시루 & 망고시루가 유명한 디저트 천국"},
                {"img": "01sungsim3.jpeg", "desc": "튀김소보로도 유명한 빵집"},
                {"img": "01sungsim4.jpeg", "desc": "보문산메아리와 명란바게트가 유명한 빵집"},
                {"img": "01sungsim5.jpg",  "desc": "성심당"},
            ]
        },

        # 2. 엑스포 & 야경 맛집
        {
            "name": "엑스포 과학공원",
            "desc": "한빛탑과 꿈돌이가 반겨주는 대전의 랜드마크",
            "img": "01expo1.png",
            "addr": "대전 유성구 대덕대로 480"
        },
        {
            "name": "엑스포 다리",
            "desc": "야경이 예쁜 견우직녀 다리 (데이트 코스 강추)",
            "img": "01expo2.jpeg",
            "addr": "대전 유성구 도룡동"
        },
        {
            "name": "엑스포 아쿠아리움",
            "desc": "야경이 예쁜 견우직녀 다리 (데이트 코스 강추)",
            "img": "01expo3.jpeg",
            "addr": "대전 유성구 도룡동"
        },
        {
            "name": "신세계 아트앤사이언스",
            "desc": "대전 쇼핑과 문화의 중심, 아쿠아리움과 전망대까지!",
            "img": "shinsegae_dept.jpg",
            "addr": "대전 유성구 엑스포로 1"
        },
        {
            "name": "식장산 전망대",
            "desc": "대전 시내 야경이 한눈에 보이는 드라이브 코스",
            "img": "sikjang_mountain.jpg",
            "addr": "대전 동구 낭월동 산2-1"
        },

        # --- 🌳 [3. 힐링 & 자연] ---
        {
            "name": "한밭수목원",
            "desc": "도심 속 거대한 힐링 숲, 피크닉 명소",
            "img": "hanbat_arboretum.jpg",
            "addr": "대전 서구 둔산대로 169"
        },
        {
            "name": "장태산 자연휴양림",
            "desc": "메타세콰이어 숲과 아찔한 스카이웨이",
            "img": "jangtaesan.jpg",
            "addr": "대전 서구 장안로 461"
        },
        {
            "name": "계족산 황톳길",
            "desc": "맨발로 걷는 붉은 황톳길 트레킹",
            "img": "gyejoksan_redclay.jpg",
            "addr": "대전 대덕구 장동 산91"
        },
        {
            "name": "대청호반",
            "desc": "탁 트인 호수 뷰와 분위기 좋은 카페들이 있는 곳",
            "img": "daecheong_lake.jpg",
            "addr": "대전 대덕구 대청로 618-136"
        },
        {
            "name": "유성온천 족욕체험장",
            "desc": "여행의 피로를 푸는 따끈따끈 야외 족욕탕",
            "img": "yuseong_hotspring.jpg",
            "addr": "대전 유성구 봉명동 574"
        },
        {
            "name": "뿌리공원",
            "desc": "나의 뿌리를 찾는 효 테마 공원 (야경도 예쁨)",
            "img": "ppuri_park.jpg",
            "addr": "대전 중구 뿌리공원로 79"
        },
        {
            "name": "오월드",
            "desc": "동물원과 플라워랜드, 사파리가 있는 테마파크",
            "img": "oworld.jpg",
            "addr": "대전 중구 사정공원로 70"
        },

        # --- ☕ [4. 힙플 & 문화] ---
        {
            "name": "소제동 카페거리",
            "desc": "옛 관사촌을 개조한 감성 가득한 카페 골목",
            "img": "soje_street.jpg",
            "addr": "대전 동구 소제동"
        },
        {
            "name": "으능정이 스카이로드",
            "desc": "거대한 LED 천장이 있는 대전의 명동",
            "img": "skyroad.jpg",
            "addr": "대전 중구 중앙로164번길 21-13"
        },
        {
            "name": "대전예술의전당",
            "desc": "이응노 미술관과 함께 예술 감성 충전하는 곳",
            "img": "art_center.jpg",
            "addr": "대전 서구 둔산대로 135"
        },
        {
            "name": "동춘당",
            "desc": "고즈넉한 한옥의 멋을 느낄 수 있는 역사 공원",
            "img": "dongchundang.jpg",
            "addr": "대전 대덕구 동춘당로 80"
        },

        # --- 🍜 [5. 대전의 맛] ---
        {
            "name": "오씨칼국수",
            "desc": "물총조개가 산더미처럼 들어간 대전 명물 칼국수",
            "img": "kalguksu.jpg",
            "addr": "대전 동구 옛신탄진로 13"
        },
        {
            "name": "광천식당",
            "desc": "매콤한 양념이 중독적인 두부두루치기",
            "img": "tofu_duruchigi.jpg",
            "addr": "대전 중구 대종로505번길 29"
        },
        {
            "name": "태평소국밥",
            "desc": "육사시미와 국밥이 끝내주는 줄 서는 맛집",
            "img": "beef_soup.jpg",
            "addr": "대전 유성구 온천동로65번길 50"
        },
        {
            "name": "중앙시장",
            "desc": "대전의 정이 넘치는 전통시장 (스모키버거, 만두)",
            "img": "central_market.jpg",
            "addr": "대전 동구 대전로 783"
        }
    ]

    print(f"🚀 '{IMAGE_FOLDER}' 폴더 스캔 및 학습 시작...")
    
    count = 0
    # 첫 번째 루프: 장소별로 돌기
    for place in grouped_places:
        common_name = place["name"]
        common_addr = place["addr"]
        
        # 두 번째 루프: 그 장소 안의 사진들 꺼내기
        for item in place["contents"]:
            image_file = item["img"]
            description = item["desc"]

            # 중복 체크
            if image_file in existing_images:
                print(f"⏩ 패스: {image_file} (이미 아는 사진)")
                continue

            file_path = os.path.join(IMAGE_FOLDER, image_file)
            
            if not os.path.exists(file_path):
                print(f"❌ 파일 없음: {file_path}")
                continue
                
            try:
                print(f"📸 학습 중: {common_name} - {image_file}")
                with open(file_path, "rb") as f:
                    img_bytes = f.read()
                    
                vector = ai_instance.image_to_vector(img_bytes)
                
                if vector:
                    new_place = Place(
                        name=common_name,       # 공통 이름
                        address=common_addr,    # 공통 주소
                        description=description, # 개별 설명
                        image_path=image_file,   # 개별 사진
                        embedding=vector
                    )
                    db.add(new_place)
                    count += 1
                    
            except Exception as e:
                print(f"⚠️ 에러: {e}")
    
    if count > 0:
        db.commit()
        print(f"🎉 {count}장의 사진을 새로 학습했어!")
    else:
        print("💤 새로 학습할 게 없네!")
        
    db.close()

if __name__ == "__main__":
    init_db()
    seed_places()