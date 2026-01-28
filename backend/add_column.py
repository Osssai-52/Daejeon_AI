# add_column.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. 환경 변수 로드
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. DB 연결
engine = create_engine(DATABASE_URL)

def add_manual_mood_column():
    print("⏳ manual_mood 컬럼 추가를 시작할게...")
    
    try:
        with engine.connect() as conn:
            # 3. 테이블에 컬럼이 이미 있는지 확인하고 없으면 추가하는 SQL
            # PostgreSQL 기준 명령어이야!
            conn.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS manual_mood VARCHAR;"))
            conn.commit()
            print("✅ 성공! places 테이블에 manual_mood 컬럼이 추가되었어.")
            print("이제 기존 데이터는 그대로 유지되면서 새로운 칸만 생겼을 거야! ✨")
            
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        print("이미 컬럼이 있거나 DB 연결에 문제가 있을 수 있어.")

if __name__ == "__main__":
    add_manual_mood_column()