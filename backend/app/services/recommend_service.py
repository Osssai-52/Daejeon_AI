from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import UploadFile
from typing import List
import torch 

from app.db.models import Place
from app.services.ai_service import ai_instance
from app.utils import calculate_distance, sort_by_shortest_path

class RecommendService:
    def analyze_mood(self, image_vector: list) -> str:
        """
        [기능 구현] 이미지 벡터를 분석해서 가장 어울리는 무드 키워드를 반환
        CLIP의 Zero-shot Classification 기능을 활용해 텍스트와 이미지의 유사도를 비교함
        """
        # 1. 비교할 무드 카테고리 정의 (영어 프롬프트 -> 한국어 결과 매핑)
        label_map = {
            "A peaceful photo of nature, forest, and healing scenery": "자연/힐링",
            "A retro style cafe with vintage atmosphere and emotional vibe": "레트로/감성카페",
            "A busy city street at night with neon lights and urban view": "야경/도시",
            "A dynamic photo of outdoor activities, sports, and excitement": "활동적/액티비티",
            "A delicious photo of fresh bread, pastries, and a bakery": "맛집/빵지순례"
        }
        
        prompts = list(label_map.keys())
        
        # 2. AI 모델 도구 가져오기 (ai_instance에서 빌려쓰기)
        processor = ai_instance.processor
        model = ai_instance.model
        
        # 3. 텍스트(키워드)를 벡터로 변환
        inputs = processor(text=prompts, return_tensors="pt", padding=True)
        
        # 4. 이미지 벡터(리스트)를 텐서로 변환
        image_tensor = torch.tensor([image_vector], dtype=torch.float32) # shape: [1, 512]

        # 5. 유사도 계산 (이미지 vs 5가지 무드)
        with torch.no_grad():
            # 텍스트 특징 추출
            text_outputs = model.get_text_features(**inputs) 
            
            # 모델 버전에 따라 결과가 상자일 수도, 숫자일 수도 있어서 안전하게 처리
            text_features = text_outputs.pooler_output if hasattr(text_outputs, 'pooler_output') else text_outputs

            # 정규화 (이제 text_features가 숫자니까 .norm()이 잘 작동할 것)
            image_features = image_tensor / image_tensor.norm(dim=-1, keepdim=True)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            # 내적을 통해 유사도 확률 계산 (Softmax)
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
            # 가장 점수가 높은 인덱스 찾기
            values, indices = similarity[0].topk(1)
            best_match_idx = indices[0].item()
            
        # 6. 한국어 키워드 반환
        best_prompt = prompts[best_match_idx]
        return label_map[best_prompt]

    async def get_recommendations(
        self, 
        db: Session, 
        files: List[UploadFile], 
        current_lat: float, 
        current_lng: float
    ):
        """
        메인 로직: 이미지 분석 -> 무드 파악 -> 유사 장소 검색 -> 필터링 -> 최단 경로 정렬
        """
        raw_candidates = []
        seen_names = set()

        # 1. 업로드된 파일들 분석
        for file in files:
            content = await file.read()
            user_vector = ai_instance.image_to_vector(content)
            
            if user_vector is None: continue

            # AI가 무드 분석
            detected_mood = self.analyze_mood(user_vector)

            # 2. 벡터 검색
            distance_col = Place.embedding.cosine_distance(user_vector).label("distance")
            stmt = select(Place, distance_col).order_by(distance_col).limit(10)
            results = db.execute(stmt).all() 

            for row in results:
                place, distance = row
                
                if place.name in seen_names: continue

                if distance < 0.45: # 유사도 기준
                    raw_candidates.append({
                        "id": place.id, 
                        "name": place.name,
                        "description": place.description,
                        "address": place.address,   
                        "image_url": place.image_path,
                        "lat": place.latitude,
                        "lng": place.longitude,
                        "similarity": float(distance),
                        "mood_tag": detected_mood # [결과에 추가] 분석된 무드 태그
                    })
                    seen_names.add(place.name)

        if not raw_candidates:
            return None 

        # 3. 브랜드 필터링
        final_recommendations = []
        brand_groups = {"성심당": []} 
        
        for place in raw_candidates:
            is_brand = False
            for brand_name in brand_groups.keys():
                if brand_name in place["name"]:
                    brand_groups[brand_name].append(place)
                    is_brand = True
                    break
            if not is_brand:
                final_recommendations.append(place)
        
        for brand_name, branches in brand_groups.items():
            if branches:
                best_branch = min(
                    branches,
                    key=lambda p: calculate_distance(current_lat, current_lng, p['lat'], p['lng'])
                )
                final_recommendations.append(best_branch)

        # 4. 최단 거리 순 정렬
        sorted_recommendations = sort_by_shortest_path(current_lat, current_lng, final_recommendations)
        
        return sorted_recommendations

# 서비스 인스턴스 생성
recommend_service = RecommendService()
