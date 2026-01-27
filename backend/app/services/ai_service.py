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

            # 4. 결과 텐서 추출 (transformers 버전에 따라 타입이 다를 수 있음)
            if hasattr(outputs, "pooler_output"):
                image_features = outputs.pooler_output
            elif isinstance(outputs, (tuple, list)):
                image_features = outputs[0]
            else:
                image_features = outputs

            # 이 모델은 숫자 512개짜리 벡터를 반환
            vector = image_features[0].tolist()
            return vector
            
        except Exception as e:
            print(f"❌ AI 변환 중 에러 발생: {e}")
            return None

# 이 변수를 다른 파일에서 가져다 씁니다
ai_instance = AIService()
