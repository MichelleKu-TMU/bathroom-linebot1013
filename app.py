import os
import json
from flask import Flask, request
from linebot.v3.webhook import WebhookHandler
import gspread
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    PostbackAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    LocationMessageContent # 處理位置訊息的內容類型
)
import traceback
from dotenv import load_dotenv
from datetime import datetime


# 引入輔具中心處理模組
import aids_center 
# 引入小知識處理模組
import knowledge_module 

# --- 初始化 (配置與 Google Sheet) ---
load_dotenv()

# Line Bot API V3 SDK 配置 (請替換為您的實際值，或使用 .env 檔)
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN', 'IlLVRJiIJ8ZPe9Up1J+8kQUttWiLZKg1M2ByuP7EcxxXH3HhNYqJvBuoU2ng9aPE+9yXL+k4DgxckcqMAZ77qn58Ep8etCgf1V5pJxXeGvjba/SZftuHAult1miSePhF7XX8tkYNXIzFATv/pjdWIAdB04t89/1O/w1cDnyilFU=')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET', '962c3eb635b135fb8dbccc33ec10fb11')


configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
app = Flask(__name__)

# Google Sheet 初始化 (確保您的 JSON 文件存在於正確位置)
gc = gspread.service_account(filename='bathline-473103-2c3250106575.json')
sh = gc.open('bathlinebot')
worksheet = sh.worksheet('工作表4')


# --- 問答測驗資料 ---
QUIZ_QUESTIONS = [
    # 前3題不計分
    {"question": "Q1: 請問您是否有申請過長照服務？", "options": ["是", "否"], "feedback": ["感謝您的填答，長照服務能提供更多支持。", "感謝您的填答，若有需求可隨時諮詢長照服務。"], "score_map": {"是": 0, "否": 0}},
    {"question": "Q2: 請問您近半年是否有在浴室滑倒過？", "options": ["是", "否"], "feedback": ["有滑倒經驗應特別注意！請檢視環境並繼續下一題。", "保持警惕是好事，預防勝於治療。請繼續下一題。"], "score_map": {"是": 0, "否": 0}},
    {"question": "Q3: 請問您是否知道可以透過改善衛浴環境來避免跌倒？", "options": ["是", "否"], "feedback": ["很好，有觀念是改善的第一步。", "這很常見！我們的建議將幫助您。"], "score_map": {"是": 0, "否": 0}},

    # 後10題計分 (省略 feedback 以保持簡潔，但您的原程式碼中應保留)
    {"question": "Q4: 浴廁門寬是否足夠讓輪椅或便盆椅進出?", "options": ["是", "否"], "feedback": ["太棒了！這樣進出空間更安全也更方便長輩活動～", "如果門太窄，出入時容易卡住或跌倒，建議可請專業人員評估是否能調整門框寬度喔。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q5: 浴廁門檻是否低於3公分?", "options": ["是", "否"], "feedback": ["很好！低門檻能減少絆倒風險，出入更安心～", "門檻過高容易讓長輩絆倒，可考慮加裝斜坡墊或調整高度。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q6: 是否有使用洗澡椅?", "options": ["是", "否"], "feedback": ["非常好！洗澡椅能穩定坐姿，讓沐浴更安全又輕鬆～", "建議考慮使用洗澡椅，能減少滑倒風險，也讓照顧更省力喔。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q7: 浴室地板是否止滑？", "options": ["是", "否"], "feedback": ["太好了！止滑地板能有效預防跌倒，讓家更安心～", "滑滑的地板很危險，可以鋪防滑墊或更換止滑磁磚來改善！"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q8: 淋浴處（浴缸）是否有加裝扶手?", "options": ["是", "否"], "feedback": ["很棒！有扶手能協助起身與保持平衡，安全加倍～", "沐浴時容易滑倒，建議可在浴缸或淋浴旁加裝防水扶手。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q9: 浴室是否為乾濕分離設計?", "options": ["是", "否"], "feedback": ["太好了！乾濕分離能保持地面乾燥，減少滑倒風險～", "若浴室容易積水，可加裝隔水簾或止水條改善環境安全。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q10: 馬桶是否有加裝馬桶增高器或扶手?", "options": ["是", "否"], "feedback": ["非常棒！有輔助設備能讓如廁更穩定、更省力～", "建議可加裝馬桶增高器或側邊扶手，幫助起身時更安全。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q11: 洗手台旁是否有加裝扶手?", "options": ["是", "否"], "feedback": ["很好！這樣能幫助長輩在洗手或站立時保持平衡～", "洗手時若需支撐，可在旁邊加裝扶手，提升整體安全性。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q12: 廁所入口處是否有扶手?", "options": ["是", "否"], "feedback": ["太棒了！有扶手的入口更安全，進出時不易跌倒～", "建議可在門口或牆邊安裝扶手，協助長輩穩定走入廁所。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q13: 廁所是否有加裝感應燈/小夜燈?", "options": ["是", "否"], "feedback": ["做得很好！夜間有感應燈能讓長輩在黑暗中行動更安心～", "夜晚光線不足容易跌倒，可安裝小夜燈或感應燈增加安全感。"], "score_map": {"是": 0, "否": 1}},
]

TOTAL_QUESTIONS = len(QUIZ_QUESTIONS)
user_states = {} # 用於儲存用戶測驗狀態

# --- QuickReply、結論生成函數 (與您的原程式碼相同) ---
def get_quiz_quick_reply(question_index):
    q = QUIZ_QUESTIONS[question_index]
    items = []
    for option in q["options"]:
        items.append(
            QuickReplyItem(
                action=PostbackAction(
                    label=option,
                    data=f"quiz_answer={question_index},{option}",
                    display_text=option
                )
            )
        )
    return QuickReply(items=items)

def generate_quiz_conclusion(score):
    # 根據分數設定風險等級和初步建議
    if score >= 8:
        level = "高風險"
        detail = "您的浴室目前存在多項高風險問題，建議您「立即」請專業人員進行詳細評估與改善，避免意外發生。"
    elif score >= 5:
        level = "中度風險"
        detail = "整體安全大致良好，但有幾項細節可再加強。建議參考測驗中提到的建議，改善中度風險區域。"
    else:
        level = "安全良好"
        detail = "您的浴室環境相當安全，請持續保持！"
    
    # 組合最終結論文字
    conclusion = (
        f"【測驗總結】\n"
        f"總分：{score} 分（後10題計分）\n\n"
        f"風險等級：{level}\n"
        f"建議：{detail}\n\n"
        f"您可以上「新北市輔具資源中心網」了解更多資訊\n"
        f"https://atrc.aihsin.ntpc.gov.tw/EducationClass/6"
    )
    
    return conclusion


# --- Webhook 路由 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except Exception as e:
        traceback.print_exc()
    return 'OK'


# --- 1. 輔具中心推薦處理 (Location Message) ---
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_message_2(event):
    # 創建 API 客戶端實例
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        # 呼叫 aids_center.py 中的函數，傳入 event 和 line_bot_api
        aids_center.handle_aids_center_location(event, line_bot_api) 


# 假設您已經在程式碼頂部引入了必要的類別，例如：
# from linebot.v3.messaging import TextMessage, ReplyMessageRequest, ApiClient, PostbackAction, QuickReply, QuickReplyItem
# from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent
# from datetime import datetime
# from your_modules import knowledge_module, QUIZ_QUESTIONS, TOTAL_QUESTIONS, get_quiz_quick_reply, generate_quiz_conclusion

# --- 2. 文字訊息處理 (Text Message) ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    
    # 創建 API 客戶端實例
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 🎯 新增功能：處理「小知識」文字指令 (已新增 Log)
        if text == "小知識":
            app.logger.info(f"User {user_id} requested '小知識'. Calling knowledge module.")
            knowledge_module.handle_knowledge_quiz(event, line_bot_api)
            return
            
        # 🎯 新增功能：處理「附近輔具資源」文字指令
        if text == "附近輔具資源":
            # 回覆一段文字，並附上 line://nv/location 連結
            reply_text = (
                "📍 好的，請點擊下方的 **「+」號按鈕**，選擇 **「位置資訊」** 傳送您的目前位置給我。\n\n"
                "您也可以直接點擊此連結開啟位置分享介面：\n"
                "line://nv/location"
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
            return
            
        # 啟動測驗
        if text.upper() == "開始居家衛浴安全測驗":
            user_states[user_id] = {"status": "ask_name"}
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="請輸入您的姓名開始測驗：")]
                )
            )
            return

        # ------------------------------------------------------------------
        # 👇 變更 1: 使用者輸入姓名 -> 進入詢問年齡階段
        # ------------------------------------------------------------------
        elif user_id in user_states and user_states[user_id].get("status") == "ask_name":
            name = text
            # 儲存姓名，進入詢問年齡階段
            user_states[user_id]["status"] = "ask_age"
            user_states[user_id]["name"] = name
            
            # 回覆詢問年齡
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"感謝您，{name}！\n\n請問您的年齡是？ \n(請直接輸入數字)")]
                )
            )
            return

        # ------------------------------------------------------------------
        # 👇 新增 1: 使用者輸入年齡 -> 進入詢問性別階段
        # ------------------------------------------------------------------
        elif user_id in user_states and user_states[user_id].get("status") == "ask_age":
            age = text
            
            # 簡單檢查輸入是否為數字
            if not age.isdigit():
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="請輸入有效的數字年齡，例如：65")]
                    )
                )
                return

            # 儲存年齡，進入詢問性別階段
            user_states[user_id]["status"] = "ask_gender"
            user_states[user_id]["age"] = age
            
            # 準備 Quick Reply for Gender
            gender_quick_reply = QuickReply(
                items=[
                    QuickReplyItem(
                        action=PostbackAction(label="男性", data="quiz_gender=男性", display_text="男性")
                    ),
                    QuickReplyItem(
                        action=PostbackAction(label="女性", data="quiz_gender=女性", display_text="女性")
                    ),
                    QuickReplyItem(
                        action=PostbackAction(label="不透漏", data="quiz_gender=不透漏", display_text="不透漏")
                    )
                ]
            )

            # 回覆詢問性別
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text="請問您的性別是？",
                        quick_reply=gender_quick_reply
                    )]
                )
            )
            return
            
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------


        # 其他文字
        else:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="請輸入「開始居家衛浴安全測驗」來啟動測驗、輸入「小知識」來獲得安全提醒，或傳送您的位置資訊來尋找最近的輔具中心。")]
                )
            )


# --- 3. Postback 回覆處理 ---
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data = event.postback.data
    
    # ------------------------------------------------------------------
    # 👇 新增 2: 處理性別 Postback (quiz_gender=...)，開始測驗
    # ------------------------------------------------------------------
    if data.startswith("quiz_gender="):
        try:
            _, gender = data.split("=", 1)
        except ValueError:
            return

        if user_id not in user_states or user_states[user_id]["status"] != "ask_gender":
            return

        state = user_states[user_id]
        name = state["name"]
        age = state["age"]
        
        # 儲存性別並初始化測驗狀態
        user_states[user_id] = {
            "status": "quiz", 
            "step": 0, 
            "score": 0, 
            "name": name, 
            "age": age, 
            "gender": gender
        }

        # 建立新列 (Google Sheet) - 欄位順序: user_id, name, age, gender, Q1...Qn, Score, Timestamp
        # 由於新增 age 和 gender 兩欄，問答的欄位索引將後移兩位
        new_row = [user_id, name, age, gender] + [""] * TOTAL_QUESTIONS + ["", ""]
        worksheet.append_row(new_row)
        user_states[user_id]["row_index"] = len(worksheet.get_all_values())
        
        # 問第一題
        q_index = 0
        question_text = QUIZ_QUESTIONS[q_index]["question"]
        quick_reply = get_quiz_quick_reply(q_index)
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text=f"感謝您，{name}！您的資料已記錄：年齡 {age} 歲，性別 {gender}。\n\n🏠【居家衛浴安全測驗開始】\n共有 {TOTAL_QUESTIONS} 題。\n--- 第 1 題 ---\n{question_text}",
                        quick_reply=quick_reply)]
                )
            )
        return
    # ------------------------------------------------------------------

    # 處理測驗答案
    elif data.startswith("quiz_answer="):
        try:
            _, params = data.split("=", 1)
            q_index_str, answer = params.split(",", 1)
            q_index = int(q_index_str)
        except ValueError:
            return

        if user_id not in user_states or user_states[user_id]["status"] != "quiz" or user_states[user_id]["step"] != q_index:
            return

        state = user_states[user_id]
        current_question = QUIZ_QUESTIONS[q_index]

        # 前3題不計分
        score_add = current_question["score_map"].get(answer, 0)
        if q_index >= 3:
            state["score"] += score_add

        state["step"] += 1
        option_index = current_question["options"].index(answer)
        feedback_text = current_question["feedback"][option_index]
        row_index = state["row_index"]
        
        # ------------------------------------------------------------------
        # 👇 變更 2: 更新 Google Sheet 欄位索引 (+2 位，因為多了 Age 和 Gender 兩欄)
        # ------------------------------------------------------------------
        # 答案欄位從 q_index + 3 變為 q_index + 5
        worksheet.update_cell(row_index, q_index + 5, f"{answer}({score_add})")

        reply_msgs = [TextMessage(
            text=f"您的答案是：{answer}\n💬 {feedback_text}"
        )]

        if state["step"] < TOTAL_QUESTIONS:
            next_q = QUIZ_QUESTIONS[state["step"]]
            quick_reply = get_quiz_quick_reply(state["step"])
            reply_msgs.append(TextMessage(
                text=f"--- 第 {state['step'] + 1} 題 ---\n{next_q['question']}",
                quick_reply=quick_reply
            ))
        else:
            final_score = state["score"]
            conclusion = generate_quiz_conclusion(final_score)
            
            # 測驗結束，更新 Google Sheet
            # 分數欄位從 TOTAL_QUESTIONS + 3 變為 TOTAL_QUESTIONS + 5
            worksheet.update_cell(row_index, TOTAL_QUESTIONS + 5, final_score)
            # 時間戳記欄位從 TOTAL_QUESTIONS + 4 變為 TOTAL_QUESTIONS + 6
            worksheet.update_cell(row_index, TOTAL_QUESTIONS + 6, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            reply_msgs.append(TextMessage(text="✅ 測驗完成！"))
            reply_msgs.append(TextMessage(text=conclusion))
            del user_states[user_id]
        # ------------------------------------------------------------------

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(reply_token=event.reply_token, messages=reply_msgs)
            )

    # 處理 Postback 動作 (例如：從測驗結論點擊「小知識」)
    elif data == "show_knowledge":
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            app.logger.info(f"User {user_id} postbacked 'show_knowledge'. Calling knowledge module.")
            # 由於 PostbackEvent 和 MessageEvent 結構類似，可以直接呼叫
            knowledge_module.handle_knowledge_quiz(event, line_bot_api)
        
    elif data == "find_center":
        # 模擬「附近輔具資源」的文字回覆
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            reply_text = (
                "📍 好的，請點擊下方的 **「+」號按鈕**，選擇 **「位置資訊」** 傳送您的目前位置給我。\n\n"
                "您也可以直接點擊此連結開啟位置分享介面：\n"
                "line://nv/location"
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
    elif data == "start_quiz_again":
        # 模擬「開始居家衛浴安全測驗」的流程
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            # 保持為 ask_name 狀態，讓流程重新開始
            user_states[user_id] = {"status": "ask_name"}
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="請輸入您的姓名開始測驗：")]
                )
            )


if __name__ == "__main__":
    # 確保您已經在終端機中設定了環境變數，或將您的 Line Bot 程式部署在伺服器上
    print("Line Bot 應用程式啟動...")
    app.run(port=8000, debug=True)                                                                                             