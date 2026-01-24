# backend/app/db/models.py
from sqlalchemy import Column, Integer, String, Float, Text
from pgvector.sqlalchemy import Vector  # ★ 핵심: 벡터를 저장하는 타입
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