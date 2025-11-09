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
import time
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
user_states = {}

def get_quiz_quick_reply(index):
    q = QUIZ_QUESTIONS[index]
    return QuickReply(items=[
        QuickReplyItem(action=PostbackAction(label=o, data=f"quiz_answer={index},{o}", display_text=o))
        for o in q["options"]
    ])

def generate_quiz_conclusion_old(score):
    if score >= 8:
        level, detail = "高風險", "建議立即改善環境，避免意外發生。"
    elif score >= 5:
        level, detail = "中度風險", "建議針對部分項目進行改善。"
    else:
        level, detail = "安全良好", "請持續保持良好環境！"
    return f"【測驗總結】\n總分：{score}\n風險等級：{level}\n建議：{detail}"
    
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
        # 小知識指令
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
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
            return
        
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
                # Don't reply twice with the same reply_token (it becomes invalid after first use).
                # We'll include the auto-correction message together with the next prompt in one reply.
            else:
                msg = "請輸入正確格式，例如：「新北市中和區」或「花蓮縣吉安鄉」。"
                line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)]))
                # line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)]))
                return

            user_states[user_id].update({"region": fixed_region, "status": "ask_gender"})
            # Prepare messages list so we reply only once with the same reply_token
            messages = []
            gender_reply = QuickReply(items=[
                QuickReplyItem(action=PostbackAction(label="男性", data="quiz_gender=男性")),
                QuickReplyItem(action=PostbackAction(label="女性", data="quiz_gender=女性")),
                QuickReplyItem(action=PostbackAction(label="不透漏", data="quiz_gender=不透漏")),
            ])
            # If we auto-corrected the region (loose pattern branch), include that notice first
            if re.match(loose_pattern, region):
                messages.append(TextMessage(text=f"已自動補齊為「{fixed_region}」。"))

            msg = f"感謝您！已記錄地區：{fixed_region}\n請問您的性別是？"
            messages.append(TextMessage(text=msg, quick_reply=gender_reply))

            # Send a single reply using the provided reply_token
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=messages))
            return

        

        # 其他
        msg = "請輸入「開始居家衛浴安全測驗」開始問卷。"
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)]),
                                    async_req=True, )
        
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_message_2(event):
    # 創建 API 客戶端實例
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        # 呼叫 aids_center.py 中的函數，傳入 event 和 line_bot_api
        aids_center.handle_aids_center_location(event, line_bot_api) 

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

        # 處理測驗答案（來自 Quick Reply 的 postback: quiz_answer=index,option）
        if data.startswith("quiz_answer="):
            try:
                _, params = data.split("=", 1)
                q_index_str, answer = params.split(",", 1)
                q_index = int(q_index_str)
            except ValueError:
                return

            s = user_states.get(user_id)
            # 驗證使用者狀態與步驟一致
            if not s or s.get("status") != "quiz" or s.get("step") != q_index:
                return

            current_question = QUIZ_QUESTIONS[q_index]
            score_add = current_question["score_map"].get(answer, 0)
            # 前 3 題不計分
            if q_index >= 3:
                s["score"] = s.get("score", 0) + score_add

            s["step"] = s.get("step", 0) + 1
            # 回饋文字
            try:
                option_index = current_question["options"].index(answer)
                feedback_text = current_question["feedback"][option_index]
            except ValueError:
                feedback_text = ""

            row_index = s.get("row_index")
            # 答案欄位起始於第 9 欄（前面儲存了 8 個欄位：user_id,name,age,region,gender,role,living_type,mobility_status）
            if row_index:
                worksheet.update_cell(row_index, q_index + 9, f"{answer}({score_add})")

            reply_msgs = [TextMessage(text=f"您的答案是：{answer}\n💬 {feedback_text}")]

            if s["step"] < TOTAL_QUESTIONS:
                next_q = QUIZ_QUESTIONS[s["step"]]
                reply_msgs.append(TextMessage(text=f"--- 第 {s['step'] + 1} 題 ---\n{next_q['question']}", quick_reply=get_quiz_quick_reply(s["step"])))
            else:
                final_score = s.get("score", 0)
                conclusion = generate_quiz_conclusion(final_score)
                # 分數與時間戳記欄位位置：TOTAL_QUESTIONS 後面接分數與時間
                if row_index:
                    worksheet.update_cell(row_index, TOTAL_QUESTIONS + 9, final_score)
                    worksheet.update_cell(row_index, TOTAL_QUESTIONS + 10, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                reply_msgs.append(TextMessage(text="✅ 測驗完成！"))
                reply_msgs.append(TextMessage(text=conclusion))
                # 清除狀態
                try:
                    del user_states[user_id]
                except KeyError:
                    pass

            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=reply_msgs))
            return

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))