# backend/app/services/ai_service.py

from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io
import torch

class AIService:
    def __init__(self):
        print("🤖 HuggingFace AI 모델(CLIP) 로딩 중...")
        # 여기가 바로 Hugging Face에서 모델을 가져오는 부분입니다.
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        print("✅ 모델 장착 완료!")

    def image_to_vector(self, image_bytes):
        try:
            # 1. 바이트 형태의 이미지를 열기
            image = Image.open(io.BytesIO(image_bytes))
            
            # 2. AI가 이해할 수 있게 변환 (전처리)
            inputs = self.processor(images=image, return_tensors="pt")
            
            # 3. 벡터 추출 (특징 뽑아내기)
            with torch.no_grad():
                outputs = self.model.get_image_features(**inputs)
            
            # 4. 결과를 파이썬 리스트로 변환 (DB에 저장하기 위해)
            # 이 모델은 숫자 512개짜리 리스트를 만들어줍니다.
            vector = outputs[0].tolist()
            return vector
            
        except Exception as e:
            print(f"❌ AI 변환 중 에러 발생: {e}")
            return None

# 이 변수를 다른 파일에서 가져다 씁니다
ai_instance = AIService()