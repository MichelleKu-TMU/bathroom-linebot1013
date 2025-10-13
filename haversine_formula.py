# haversine_formula.py
import math

def count_dist(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    使用 Haversine 公式計算兩點經緯度之間的距離。(單位：公里)

    參數:
        lon1 (float): 第一點的經度 (使用者位置)
        lat1 (float): 第一點的緯度 (使用者位置)
        lon2 (float): 第二點的經度 (輔具中心)
        lat2 (float): 第二點的緯度 (輔具中心)

    回傳:
        float: 兩點之間的距離 (公里)
    """
    # 地球平均半徑 (公里)
    R = 6371.0 

    # 1. 將度數轉換為弧度
    lon1_rad, lat1_rad, lon2_rad, lat2_rad = map(math.radians, [lon1, lat1, lon2, lat2])

    # 緯度差和經度差
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    # 2. Haversine 公式計算 (a)
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    
    # 3. 反正切函數計算 (c)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # 4. 距離 = R * c
    distance = R * c
    
    return distance