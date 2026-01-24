# backend/app/services/recommend_service.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Place
from app.services.ai_service import ai_instance

class RecommendService:
    def recommend_places(self, db: Session, user_image_bytes: bytes, top_k: int = 3):
        """
        1. 사용자 이미지를 벡터로 변환
        2. DB에서 가장 가까운 장소(코사인 유사도) 검색
        3. 결과 반환
        """
        # 1. 이미지 -> 벡터 변환 (아까 만든 CLIP 사용)
        user_vector = ai_instance.image_to_vector(user_image_bytes)
        
        if user_vector is None:
            return []

        # 2. 벡터 검색 (pgvector의 핵심 기능!)
        # Place.embedding.cosine_distance(user_vector) -> 거리가 가까울수록 유사함
        stmt = select(Place).order_by(
            Place.embedding.cosine_distance(user_vector)
        ).limit(top_k)
        
        results = db.scalars(stmt).all()
        return results

# 서비스 인스턴스 생성
recommend_service = RecommendService()