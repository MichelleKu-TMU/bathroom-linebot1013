import os
import json
import re
from flask import Flask, request
from linebot.v3.webhook import WebhookHandler
import gspread
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage,
    QuickReply, QuickReplyItem, PostbackAction
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent,
    PostbackEvent, LocationMessageContent
)
from dotenv import load_dotenv
from datetime import datetime
import traceback

# --- 模組匯入 ---
import aids_center
import knowledge_module

# --- 初始化 ---
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
app = Flask(__name__)

# --- Google Sheet 初始化 ---
gc = gspread.service_account(filename='bathline-473103-2c3250106575.json')
sh = gc.open('bathlinebot')
worksheet = sh.worksheet('正式1')

# --- 問答測驗題 ---
QUIZ_QUESTIONS = [
    {"question": "Q1: 請問您是否有申請過長照服務？", "options": ["是", "否"], "feedback": ["感謝您的填答，長照服務能提供更多支持。", "感謝您的填答，若有需求可隨時諮詢長照服務。"], "score_map": {"是": 0, "否": 0}},
    {"question": "Q2: 請問您近半年是否有在浴室滑倒過？", "options": ["是", "否"], "feedback": ["有滑倒經驗應特別注意！", "保持警惕是好事，預防勝於治療。"], "score_map": {"是": 0, "否": 0}},
    {"question": "Q3: 您是否知道可以透過改善衛浴環境來避免跌倒？", "options": ["是", "否"], "feedback": ["很好，有觀念是改善的第一步。", "這很常見！我們的建議將幫助您。"], "score_map": {"是": 0, "否": 0}},
    {"question": "Q4: 浴廁門寬是否足夠讓輪椅或便盆椅進出?", "options": ["是", "否"], "feedback": ["太棒了！", "建議請專業人員評估是否能調整門框寬度喔。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q5: 浴廁門檻是否低於3公分?", "options": ["是", "否"], "feedback": ["很好！", "建議加裝斜坡墊或調整高度。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q6: 是否有使用洗澡椅?", "options": ["是", "否"], "feedback": ["非常好！", "建議使用洗澡椅可減少滑倒風險。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q7: 浴室地板是否止滑？", "options": ["是", "否"], "feedback": ["太好了！", "可鋪防滑墊或更換止滑磁磚。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q8: 淋浴處是否有加裝扶手?", "options": ["是", "否"], "feedback": ["很棒！", "建議在淋浴旁加裝防水扶手。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q9: 浴室是否為乾濕分離設計?", "options": ["是", "否"], "feedback": ["太好了！", "可加裝隔水簾或止水條改善。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q10: 馬桶是否有加裝馬桶增高器或扶手?", "options": ["是", "否"], "feedback": ["非常棒！", "建議加裝馬桶增高器或側邊扶手。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q11: 洗手台旁是否有加裝扶手?", "options": ["是", "否"], "feedback": ["很好！", "可加裝扶手提升安全性。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q12: 廁所入口處是否有扶手?", "options": ["是", "否"], "feedback": ["太棒了！", "可在門口安裝扶手，協助穩定走入。"], "score_map": {"是": 0, "否": 1}},
    {"question": "Q13: 廁所是否有加裝感應燈或小夜燈?", "options": ["是", "否"], "feedback": ["做得很好！", "可安裝小夜燈或感應燈提升安全。"], "score_map": {"是": 0, "否": 1}},
]
TOTAL_QUESTIONS = len(QUIZ_QUESTIONS)
user_states = {}

def get_quiz_quick_reply(index):
    q = QUIZ_QUESTIONS[index]
    return QuickReply(items=[
        QuickReplyItem(action=PostbackAction(label=o, data=f"quiz_answer={index},{o}", display_text=o))
        for o in q["options"]
    ])

def generate_quiz_conclusion(score):
    if score >= 8:
        level, detail = "高風險", "建議立即改善環境，避免意外發生。"
    elif score >= 5:
        level, detail = "中度風險", "建議針對部分項目進行改善。"
    else:
        level, detail = "安全良好", "請持續保持良好環境！"
    return f"【測驗總結】\n總分：{score}\n風險等級：{level}\n建議：{detail}"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception:
        traceback.print_exc()
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 啟動測驗
        if text.upper() == "開始居家衛浴安全測驗":
            user_states[user_id] = {"status": "ask_name"}
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請輸入您的姓名開始測驗：")]))
            return

        # 🧍 姓名檢查
        if user_states.get(user_id, {}).get("status") == "ask_name":
            name = text.strip()
            if not re.match(r"^[\u4e00-\u9fa5]{2,10}$", name):
                msg = "請輸入正確的中文姓名（2～10字，無數字或符號）。"
                line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)]))
                return
            user_states[user_id].update({"status": "ask_age", "name": name})
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=f"感謝您，{name}！請輸入您的年齡（數字）")]))
            return

        # 🎂 年齡防呆
        if user_states.get(user_id, {}).get("status") == "ask_age":
            age = text.strip()
            if not age.isdigit():
                msg = "請輸入有效的數字年齡，例如：65"
            elif not (1 <= int(age) <= 120):
                msg = "請輸入合理的年齡（1～120 歲之間）"
            else:
                user_states[user_id].update({"status": "ask_region", "age": int(age)})
                msg = "請問您的居住地區是？（例如：新北市中和區）"
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)]))
            return

        # 📍 地區防呆 + 容錯補齊
        if user_states.get(user_id, {}).get("status") == "ask_region":
            region = text.strip()
            strict_pattern = r'^[\u4e00-\u9fa5]{2,3}(市|縣)[\u4e00-\u9fa5]{1,3}(區|鄉|鎮)$'
            loose_pattern = r'^[\u4e00-\u9fa5]{2,3}(市|縣)[\u4e00-\u9fa5]{1,3}$'

            if re.match(strict_pattern, region):
                fixed_region = region
            elif re.match(loose_pattern, region):
                fixed_region = region + "區"
                line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=f"已自動補齊為「{fixed_region}」。")]))
            else:
                msg = "請輸入正確格式，例如：「新北市中和區」或「花蓮縣吉安鄉」。"
                line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)]))
                return

            user_states[user_id].update({"region": fixed_region, "status": "ask_gender"})
            gender_reply = QuickReply(items=[
                QuickReplyItem(action=PostbackAction(label="男性", data="quiz_gender=男性")),
                QuickReplyItem(action=PostbackAction(label="女性", data="quiz_gender=女性")),
                QuickReplyItem(action=PostbackAction(label="不透漏", data="quiz_gender=不透漏")),
            ])
            msg = f"感謝您！已記錄地區：{fixed_region}\n請問您的性別是？"
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg, quick_reply=gender_reply)]))
            return

        # 其他
        msg = "請輸入「開始居家衛浴安全測驗」開始問卷。"
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)]))

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data = event.postback.data
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 性別 → 身份類別
        if data.startswith("quiz_gender="):
            _, gender = data.split("=")
            user_states[user_id].update({"gender": gender, "status": "ask_role"})
            role_reply = QuickReply(items=[
                QuickReplyItem(action=PostbackAction(label="個案本人", data="quiz_role=個案本人")),
                QuickReplyItem(action=PostbackAction(label="家屬", data="quiz_role=家屬")),
                QuickReplyItem(action=PostbackAction(label="居服員", data="quiz_role=居服員")),
                QuickReplyItem(action=PostbackAction(label="其他", data="quiz_role=其他")),
            ])
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請問您是誰？", quick_reply=role_reply)]))
            return

        # 身份 → 居住環境
        if data.startswith("quiz_role="):
            _, role = data.split("=")
            user_states[user_id].update({"role": role, "status": "ask_living"})
            living_reply = QuickReply(items=[
                QuickReplyItem(action=PostbackAction(label="獨居", data="quiz_living=獨居")),
                QuickReplyItem(action=PostbackAction(label="與家人同住", data="quiz_living=與家人同住")),
                QuickReplyItem(action=PostbackAction(label="安養機構", data="quiz_living=安養機構")),
                QuickReplyItem(action=PostbackAction(label="其他", data="quiz_living=其他")),
            ])
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請問個案目前的居住環境？", quick_reply=living_reply)]))
            return

        # 居住環境 → 行動狀況
        if data.startswith("quiz_living="):
            _, living = data.split("=")
            user_states[user_id].update({"living_type": living, "status": "ask_mobility"})
            mobility_reply = QuickReply(items=[
                QuickReplyItem(action=PostbackAction(label="使用輪椅", data="quiz_mobility=使用輪椅")),
                QuickReplyItem(action=PostbackAction(label="拐杖", data="quiz_mobility=拐杖")),
                QuickReplyItem(action=PostbackAction(label="無", data="quiz_mobility=無")),
                QuickReplyItem(action=PostbackAction(label="其他", data="quiz_mobility=其他")),
            ])
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="請問是否有行動不便或使用輔具？", quick_reply=mobility_reply)]))
            return

        # 行動狀況 → 啟動測驗
        if data.startswith("quiz_mobility="):
            _, mobility = data.split("=")
            s = user_states[user_id]
            s.update({"mobility_status": mobility, "status": "quiz", "step": 0, "score": 0})
            new_row = [user_id, s["name"], s["age"], s["region"], s["gender"], s["role"], s["living_type"], s["mobility_status"]] + [""] * TOTAL_QUESTIONS + ["", ""]
            worksheet.append_row(new_row)
            s["row_index"] = len(worksheet.get_all_values())
            q = QUIZ_QUESTIONS[0]
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=f"✅ 感謝您！資料已記錄。\n\n🏠【居家衛浴安全測驗開始】\n共有 {TOTAL_QUESTIONS} 題。\n--- 第1題 ---\n{q['question']}", quick_reply=get_quiz_quick_reply(0))]))
            return

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))