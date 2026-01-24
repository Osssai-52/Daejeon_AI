import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    두 좌표 사이의 거리 계산 (Haversine 공식)
    return: 거리 (km)
    """
    R = 6371  # 지구 반지름 (km)

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) * math.sin(d_lon / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_duration(distance_km):
    """
    거리에 따라 이동 수단을 판단하고 시간 계산
    - 1km 미만: 걷기 (시속 4km)
    - 1km 이상: 차량 (시속 30km)
    """
    if distance_km <= 0:
        return {"min": 0, "type": "도보"}

    if distance_km < 1.0:
        speed = 4  # 시속 4km (걷기)
        move_type = "도보"
    else:
        speed = 30 # 시속 30km (차량)
        move_type = "차량"

    hours = distance_km / speed
    minutes = round(hours * 60)
    
    return {"min": minutes, "type": move_type}

def sort_by_shortest_path(start_lat, start_lng, places):
    """
    현재 위치에서 출발해서 가장 빨리 갈 수 있는 순서로 정렬 (Greedy)
    """
    sorted_places = []
    current_lat = start_lat
    current_lng = start_lng
    
    # 원본 리스트 복사
    remaining_places = places.copy()

    while remaining_places:
        # 1. 현재 위치에서 가장 가까운 곳 찾기
        nearest_place = min(
            remaining_places, 
            key=lambda p: calculate_distance(current_lat, current_lng, p['lat'], p['lng'])
        )
        
        # 2. 이동 시간 및 타입 계산해서 데이터에 추가
        dist = calculate_distance(current_lat, current_lng, nearest_place['lat'], nearest_place['lng'])
        time_info = calculate_duration(dist) 
        
        nearest_place['duration'] = time_info['min']     # 예: 15 (분)
        nearest_place['transport'] = time_info['type']   # 예: "차량"
        
        # 3. 결과 리스트에 넣고, 남은 목록에서 삭제
        sorted_places.append(nearest_place)
        remaining_places.remove(nearest_place)
        
        # 4. 다음 출발지를 여기로 업데이트
        current_lat = nearest_place['lat']
        current_lng = nearest_place['lng']
        
    return sorted_places