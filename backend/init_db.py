from app.db.models import Base
from app.main import engine

print("🔨 DB 테이블 생성 중...")
Base.metadata.create_all(bind=engine)
print("✅ 테이블 생성 완료! 이제 'users' 테이블이 생겼습니다.")