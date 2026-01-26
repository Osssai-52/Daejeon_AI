import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. 환경변수 불러오기
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. DB 연결
engine = create_engine(DATABASE_URL)

def reset_database():
    print("🧹 DB 청소 준비 중...")
    with engine.connect() as conn:
        # Places 테이블을 싹 비우기 (CASCADE: 얘랑 연결된 Visit 기록도 같이 지워짐)
        conn.execute(text("TRUNCATE TABLE places RESTART IDENTITY CASCADE;"))
        conn.commit()
        print("✨ DB 청소 완료! 모든 장소 데이터가 삭제됐어.")

if __name__ == "__main__":
    reset_database()