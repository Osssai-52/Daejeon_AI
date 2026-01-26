import os
import sys
import uuid 
import boto3 
from dotenv import load_dotenv

sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Place
from app.services.ai_service import ai_instance

# 1. 환경변수 로딩
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")

if not DATABASE_URL:
    print("❌ 에러: .env 파일을 못 찾거나, 안에 DATABASE_URL이 없어!")
    sys.exit(1)

# 2. S3 클라이언트 연결
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
    sys.exit(1)

# 3. DB 연결
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

IMAGE_FOLDER = "images" 

def init_db():
    print("🚀 DB 연결 및 초기화...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

# [핵심] 로컬 파일을 S3에 올리고 URL을 받아오는 함수
def upload_file_to_s3(local_file_path, original_filename):
    try:
        file_ext = original_filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}" # 이름 겹치지 않게 랜덤 생성
        
        with open(local_file_path, "rb") as f:
            file_content = f.read()
            
            # S3 업로드
            s3_client.put_object(
                Bucket=AWS_BUCKET_NAME,
                Key=unique_filename,
                Body=file_content,
                ContentType=f"image/{file_ext}"
            )
            
        # 접근 가능한 URL 반환
        return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    except Exception as e:
        print(f"❌ S3 업로드 실패 ({original_filename}): {e}")
        return None

def seed_places():
    db = SessionLocal()
    
    # 중복 방지를 위해 이미 저장된 장소 이름 확인
    print("📋 기존 데이터 확인 중...")
    existing_places = set(db.scalars(select(Place.name)).all())
    
    grouped_places = [
        # 1. 성심당 시리즈
        {
            "name": "성심당 본점",
            "addr": "대전 중구 대종로480번길 15",
            "lat": 36.327666,
            "lng": 127.427346,
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "튀김소보로와 명란바게트의 성지! 대전 필수 코스"},
                {"img": "01sungsim2.jpg",  "desc": "딸기시루 & 망고시루가 유명한 디저트 천국"},
                {"img": "01sungsim3.jpeg", "desc": "튀김소보로도 유명한 빵집"},
                {"img": "01sungsim4.jpeg", "desc": "보문산메아리와 명란바게트가 유명한 빵집"},
                {"img": "01sungsim5.jpg",  "desc": "성심당"},
            ]
        },
        {
            "name": "성심당 DCC점",
            "addr": "대전 유성구 엑스포로 107 1층",
            "lat": 36.375248,
            "lng": 127.392525,
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "튀김소보로와 명란바게트의 성지! 대전 필수 코스"},
                {"img": "01sungsim2.jpg",  "desc": "딸기시루 & 망고시루가 유명한 디저트 천국"},
            ]
        },
        {
            "name": "성심당 대전역점",
            "addr": "대전 동구 중앙로 215 2층",
            "lat": 36.332512,
            "lng": 127.434199,
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "튀김소보로와 명란바게트의 성지! 대전 필수 코스"},
                {"img": "01sungsim3.jpeg", "desc": "튀김소보로도 유명한 빵집"},
            ]
        },
        {
            "name": "성심당 롯데백화점 대전점",
            "addr": "대전 서구 계룡로 598 1층",
            "lat": 36.340365,
            "lng": 127.390176,
            "contents": [
                {"img": "01sungsim1.jpeg", "desc": "마치 유럽 거리에 온 듯한 붉은 벽돌 건물!"},
                {"img": "01sungsim2.jpg",  "desc": "비주얼 쇼크! 전설의 딸기시루 케이크 🍓"},
            ]
        },

        # 2. 엑스포 & 야경
        {
            "name": "대전 엑스포 과학공원",
            "addr": "대전 유성구 대덕대로 480",
            "lat": 36.376483,
            "lng": 127.384852,
            "contents": [
                {"img": "02expo1.png", "desc": "대전의 상징 한빛탑! 미래 도시 느낌의 랜드마크 🚀"},
                {"img": "02expo2.jpeg", "desc": "대전 야경 원탑! 엑스포 다리 (견우직녀교) 🌉"},
                {"img": "02expo7.jpeg", "desc": "밤에 더 핫한 한빛탑 물빛광장과 음악분수 ✨"},
                {"img": "02expo8.jpeg", "desc": "꿈돌이와 꿈순이가 반겨주는 엑스포 광장 🌷"},
            ]
        },
        {
            "name": "대전 엑스포 아쿠아리움",
            "addr": "대전 유성구 엑스포로 1 대전신세계 아트앤사이언스 지하1층",
            "lat": 36.375155,
            "lng": 127.381457,
            "contents": [
                {"img": "02expo3.jpeg", "desc": "인생샷 보장! 몽환적인 해저 터널 📸"},
                {"img": "02expo4.jpeg", "desc": "신비로운 바닷속 세상! 도심 속 힐링 스팟 🐋"},
            ]
        },
        {
            "name": "신세계 아트앤사이언스",
            "addr": "대전 유성구 엑스포로 1",
            "lat": 36.375155,
            "lng": 127.381457,
            "contents": [
                {"img": "03shinsegae1.jpeg", "desc": "럭셔리한 분위기 끝판왕! 실내 데이트 필수 코스 🛍️"},
                {"img": "03shinsegae2.jpeg", "desc": "대전의 새로운 랜드마크! 🏢"},
            ]
        },
        {
            "name": "식장산 전망대",
            "addr": "대전 동구 세천공원로 32-836",
            "lat": 36.303988,
            "lng": 127.479953,
            "contents": [
                {"img": "04sikjang1.jpeg", "desc": "보석을 뿌려놓은 듯한 황홀한 도시 야경 🌃"},
                {"img": "04sikjang2.jpeg", "desc": "탁 트인 하늘과 멋진 한옥 정자(식장루) 🏯"},
            ]
        },

        # 3. 힐링 & 자연
        {
            "name": "한밭수목원",
            "addr": "대전 서구 둔산대로 169",
            "lat": 36.366782,
            "lng": 127.389278,
            "contents": [
                {"img": "05hanbat_arboretum1.jpeg", "desc": "도심 속 힐링 타임! 평화로운 호수 풍경 🌿"},
                {"img": "05hanbat_arboretum2.jpeg", "desc": "장미꽃이 만발한 로맨틱한 꽃 터널! 🌹"},
            ]
        },
        {
            "name": "장태산 자연휴양림",
            "addr": "대전 서구 장안로 461",
            "lat": 36.218206,
            "lng": 127.344265,
            "contents": [
                {"img": "06jangtaesan1.jpg", "desc": "빙글빙글 올라가는 재미가 있는 스카이타워! 🗼"},
                {"img": "06jangtaesan2.jpg", "desc": "호수 위에 비친 붉은 메타세콰이어 숲 🍂"},
                {"img": "06jangtaesan3.jpg", "desc": "아찔하고 스릴 넘치는 출렁다리 스카이웨이 ☁️"},
            ]
        },
        # {
        #     "name": "계족산 황톳길",
        #     "desc": "맨발로 걷는 붉은 황톳길 트레킹",
        #     "img": "gyejoksan_redclay.jpg",
        #     "addr": "대전 대덕구 장동 산91"
        # },
        # {
        #     "name": "대청호반",
        #     "desc": "탁 트인 호수 뷰와 분위기 좋은 카페들이 있는 곳",
        #     "img": "daecheong_lake.jpg",
        #     "addr": "대전 대덕구 대청로 618-136"
        # },
        # {
        #     "name": "유성온천 족욕체험장",
        #     "desc": "여행의 피로를 푸는 따끈따끈 야외 족욕탕",
        #     "img": "yuseong_hotspring.jpg",
        #     "addr": "대전 유성구 봉명동 574"
        # },
        # {
        #     "name": "뿌리공원",
        #     "desc": "나의 뿌리를 찾는 효 테마 공원 (야경도 예쁨)",
        #     "img": "ppuri_park.jpg",
        #     "addr": "대전 중구 뿌리공원로 79"
        # },
        # {
        #     "name": "오월드",
        #     "desc": "동물원과 플라워랜드, 사파리가 있는 테마파크",
        #     "img": "oworld.jpg",
        #     "addr": "대전 중구 사정공원로 70"
        # },

        # # --- ☕ [4. 힙플 & 문화] ---
        # {
        #     "name": "소제동 카페거리",
        #     "desc": "옛 관사촌을 개조한 감성 가득한 카페 골목",
        #     "img": "soje_street.jpg",
        #     "addr": "대전 동구 소제동"
        # },
        # {
        #     "name": "으능정이 스카이로드",
        #     "desc": "거대한 LED 천장이 있는 대전의 명동",
        #     "img": "skyroad.jpg",
        #     "addr": "대전 중구 중앙로164번길 21-13"
        # },
        # {
        #     "name": "대전예술의전당",
        #     "desc": "이응노 미술관과 함께 예술 감성 충전하는 곳",
        #     "img": "art_center.jpg",
        #     "addr": "대전 서구 둔산대로 135"
        # },
        # {
        #     "name": "동춘당",
        #     "desc": "고즈넉한 한옥의 멋을 느낄 수 있는 역사 공원",
        #     "img": "dongchundang.jpg",
        #     "addr": "대전 대덕구 동춘당로 80"
        # },

        # # --- 🍜 [5. 대전의 맛] ---
        # {
        #     "name": "오씨칼국수",
        #     "desc": "물총조개가 산더미처럼 들어간 대전 명물 칼국수",
        #     "img": "kalguksu.jpg",
        #     "addr": "대전 동구 옛신탄진로 13"
        # },
        # {
        #     "name": "광천식당",
        #     "desc": "매콤한 양념이 중독적인 두부두루치기",
        #     "img": "tofu_duruchigi.jpg",
        #     "addr": "대전 중구 대종로505번길 29"
        # },
        # {
        #     "name": "태평소국밥",
        #     "desc": "육사시미와 국밥이 끝내주는 줄 서는 맛집",
        #     "img": "beef_soup.jpg",
        #     "addr": "대전 유성구 온천동로65번길 50"
        # },
        # {
        #     "name": "중앙시장",
        #     "desc": "대전의 정이 넘치는 전통시장 (스모키버거, 만두)",
        #     "img": "central_market.jpg",
        #     "addr": "대전 동구 대전로 783"
        # }
    ]

    print(f"🚀 '{IMAGE_FOLDER}' 폴더 스캔 및 학습 시작...")
    
    count = 0
    
    for place in grouped_places:
        common_name = place["name"]
        
        if common_name in existing_places:
            print(f"⏩패스: {common_name} (이미 DB에 있음)")
            continue

        common_addr = place["addr"]
        common_lat = place["lat"]
        common_lng = place["lng"]
        
        for item in place["contents"]:
            image_file = item["img"]
            description = item["desc"]

            file_path = os.path.join(IMAGE_FOLDER, image_file)
            
            if not os.path.exists(file_path):
                print(f"❌ 로컬 파일 없음: {file_path}")
                continue
                
            try:
                print(f"📸 처리 중: {common_name} - {image_file}")
                
                # 1. S3 업로드 (URL 받기)
                s3_url = upload_file_to_s3(file_path, image_file)
                if not s3_url: continue # 실패하면 다음 사진으로

                # 2. 벡터 변환
                with open(file_path, "rb") as f:
                    img_bytes = f.read()
                    vector = ai_instance.image_to_vector(img_bytes)
                
                # 3. DB 저장 (URL 저장!)
                if vector:
                    new_place = Place(
                        name=common_name,       
                        address=common_addr,    
                        latitude=common_lat,    
                        longitude=common_lng,   
                        description=description, 
                        image_path=s3_url,   # 👈 여기가 핵심! URL이 들어감
                        embedding=vector
                    )
                    db.add(new_place)
                    count += 1
                    print(f"  ✅ 저장 완료! (URL: {s3_url})")
                    
            except Exception as e:
                print(f"⚠️ 에러: {e}")
    
    if count > 0:
        db.commit()
        print(f"🎉 {count}장의 사진을 S3에 올리고 DB에 저장했어!")
    else:
        print("💤 새로 추가된 게 없네!")
        
    db.close()

if __name__ == "__main__":
    init_db()
    seed_places()