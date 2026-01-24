import sys
import os

sys.path.append(os.getcwd())

from app.services.ai_service import ai_instance

def run_test():
    image_path = "성심당.jpeg"  
    
    if not os.path.exists(image_path):
        print(f"❌ '{image_path}' 파일이 없어. 사진 넣어줘!")
        return

    print(f"📸 '{image_path}' 읽는 중...")
    
    # 2. 파일을 바이트(bytes)로 읽기
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # 3. AI에게 던지기
    print("🧠 AI가 분석 중...")
    vector = ai_instance.image_to_vector(image_bytes)

    if vector:
        print("\n🎉 성공!")
        print(f"📊 벡터 길이: {len(vector)} (512개가 나와야 정상)")
        print(f"🔢 앞부분 5개만 구경해봐: {vector[:5]} ...")
        print("이 숫자들이 DB에 저장되면 검색이 되는 거야")
    else:
        print("실패")

if __name__ == "__main__":
    run_test()