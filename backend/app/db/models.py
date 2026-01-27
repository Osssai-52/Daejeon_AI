from sqlalchemy import Column, Integer, String, Float, Text, BigInteger, ForeignKey, DateTime, UniqueConstraint
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

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_lat = Column(Float)
    start_lng = Column(Float)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    places = relationship("RoutePlace", back_populates="route", order_by="RoutePlace.order_index")

class RoutePlace(Base):
    __tablename__ = "route_places"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    order_index = Column(Integer)
    place_id = Column(Integer, nullable=True)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    lat = Column(Float)
    lng = Column(Float)

    route = relationship("Route", back_populates="places")

class PlacePhoto(Base):
    __tablename__ = "place_photos"
    __table_args__ = (UniqueConstraint("user_id", "place_id", name="uq_place_photos_user_place"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    place_id = Column(Integer, ForeignKey("places.id"))
    image_url = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    place = relationship("Place")
