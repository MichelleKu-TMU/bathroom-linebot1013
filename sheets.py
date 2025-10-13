import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEETS_KEY = os.getenv("GOOGLE_SHEETS_KEY")
SHEET_NAME = os.getenv("SHEET_NAME")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_KEY, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1  # 用第一個工作表

def add_response(user_id, question, answer, score):
    sheet.append_row([user_id, question, answer, score])
