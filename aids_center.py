# aids_center.py
import heapq
import math
# 引入 V3 SDK 相關類別
from linebot.v3.messaging import ReplyMessageRequest, TextMessage 

# 引入距離計算函數
# 如果您運行 app.py 時出現 ImportError，請將 from .haversine_formula import count_dist 改為 from haversine_formula import count_dist
from haversine_formula import count_dist
 


# 最新輔具中心資料列表（更新經緯度）
centers = [
    {"name": "新北市輔具資源中心_蘆洲中心", "address": "新北市蘆洲區集賢路245號9樓", "lat": 25.08494, "lng": 121.48218},
    {"name": "新北市輔具資源中心_新店中心", "address": "新北市新店區北新路一段281號", "lat": 24.96717, "lng": 121.54118},
    {"name": "中和分站（中和衛生所）", "address": "新北市中和區南山路4巷3號", "lat": 24.99886, "lng": 121.50184},
    {"name": "永和分站（iCARE長照咖啡館）", "address": "新北市永和區文化路155號", "lat": 25.01650, "lng": 121.51119},
    {"name": "永耕分站（第一輔具永和門市）", "address": "新北市永和區豫溪街57巷10弄10號", "lat": 25.01088, "lng": 121.51859},
    {"name": "雙溪分站（雙溪衛生所）", "address": "新北市雙溪區新基南街18號", "lat": 25.03818, "lng": 121.86697},
    {"name": "金山分站（台大醫院金山分院）", "address": "新北市金山區玉爐路7號7樓", "lat": 25.21970, "lng": 121.62882},
    {"name": "淡水分站（長照淡水站）", "address": "新北市淡水區中山路158號", "lat": 25.17296, "lng": 121.44091},
    {"name": "深坑分站（深坑衛生所）", "address": "新北市深坑區深坑街165號", "lat": 25.00110, "lng": 121.61255},
    {"name": "三峽分站（三峽衛生所）", "address": "新北市三峽區光明路71號4樓", "lat": 24.92859, "lng": 121.37615},
    {"name": "烏來分站（烏來衛生所）", "address": "新北市烏來區新烏路五段109號", "lat": 24.87225, "lng": 121.54792},
    {"name": "坪林分站（坪林衛生所）", "address": "新北市坪林區坪林街104號", "lat": 24.93617, "lng": 121.71166},
    {"name": "央北分站（央北社會住宅）", "address": "新北市新店區中山路135號1樓", "lat": 24.98129, "lng": 121.52625},
    {"name": "台北市合宜輔具中心", "address": "臺北市中山區玉門街1號", "lat": 25.07021, "lng": 121.52215},
    {"name": "台北市西區輔具中心", "address": "臺北市中山區長安西路5巷2號1樓", "lat": 25.05064, "lng": 121.52105},
    {"name": "台北市南區輔具中心", "address": "臺北市信義區大道路116號3樓之2", "lat": 25.03924, "lng": 121.58335},
]


# 核心處理函數，現在需要接收 line_bot_api 參數
def handle_aids_center_location(event, line_bot_api):
    # LocationMessageContent 已經確保 message.type 是 'location'
    user_lat = event.message.latitude
    user_lon = event.message.longitude
        
    dis_list = []
    for center in centers:
        center_lat = center['lat']
        center_lon = center['lng']
            
        # 計算距離
        distance = count_dist(float(user_lon), float(user_lat), float(center_lon), float(center_lat))
            
        # 將距離和中心資訊一起儲存
        dis_list.append((distance, center))
            
    # 找出距離最小的三個輔具中心
    closest_three_centers = heapq.nsmallest(3, dis_list)
    
    # 建構回覆訊息
    reply_text = "📍 為您推薦最近的三個輔具資源中心：\n\n"
    
    for i, (distance, center) in enumerate(closest_three_centers):
        reply_text += f"【No.{i+1}：{center['name']}】\n"
        reply_text += f"🏠 地址：{center['address']}\n"
        reply_text += f"📏 距離：約 {distance:.1f} 公里\n"
        
        # Line Bot V3 TextMessage 不支援 Markdown，但為格式美觀保留粗體標記
        # 這裡加入 Google Maps 連結，方便使用者導航
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={center['lat']},{center['lng']}"
        reply_text += f"🗺️ 導航：{google_maps_url}\n"
        
        if i < 2:
             reply_text += "----------\n"

    # 使用 V3 SDK 進行回覆
    line_bot_api.reply_message(
        reply_message_request=ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(text="收到您的位置資訊！正在為您尋找最近的輔具資源中心..."),
                TextMessage(text=reply_text)
            ]
        )
    )