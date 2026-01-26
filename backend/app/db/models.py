from sqlalchemy import Column, Integer, String, Float, Text, BigInteger 
from pgvector.sqlalchemy import Vector  
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)       # 장소 이름 (예: 성심당)
    description = Column(Text)              # 설명
    image_path = Column(String)             # 이미지 파일 위치
    
    address = Column(String)       # 주소
    latitude = Column(Float)       # 위도 
    longitude = Column(Float)      # 경도 

    embedding = Column(Vector(512)) 

    def __repr__(self):
        return f"<Place(name={self.name})>"

# [추가] 카카오 로그인 유저 모델
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(BigInteger, unique=True, index=True) # 카카오 고유 ID (숫자가 커서 BigInteger)
    nickname = Column(String) # 카카오 닉네임
    profile_image = Column(String) # 프로필 사진 URL
    email = Column(String, nullable=True) # 이메일 (선택사항이라 nullable=True)
    created_at = Column(String) # 가입 시간