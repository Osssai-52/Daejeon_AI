import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import User 

# 1. 환경변수 및 DB 연결
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# 2. 회원 명단 조회
print("👥 회원 명부 확인 중...")
users = db.query(User).all()

if not users:
    print("아직 가입한 회원이 한 명도 없습니다.")
else:
    print(f"총 {len(users)}명의 회원이 있습니다.")
    for user in users:
        print(f"------------------------")
        print(f"🆔 내부 ID: {user.id}")
        print(f"🟡 카카오 ID: {user.kakao_id}")
        print(f"👤 닉네임: {user.nickname}")
        print(f"🖼️ 프사: {user.profile_image}")

db.close()