from sqlalchemy import Column, Integer, String, Float, Text, BigInteger, ForeignKey, DateTime
from pgvector.sqlalchemy import Vector  
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

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

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(BigInteger, unique=True, index=True) # 카카오 고유 ID
    nickname = Column(String) # 카카오 닉네임
    profile_image = Column(String) # 프로필 사진 URL
    email = Column(String, nullable=True) # 이메일
    created_at = Column(String) # 가입 시간

    visits = relationship("Visit", back_populates="user")

# 방문 인증을 위한 모델
class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # 누가
    place_id = Column(Integer, ForeignKey("places.id")) # 어디를
    
    visit_image = Column(String) # 인증샷 경로 (S3 URL 등)
    visited_at = Column(DateTime, default=datetime.now) # 언제
    
    # 관계 설정
    user = relationship("User", back_populates="visits")
    place = relationship("Place")