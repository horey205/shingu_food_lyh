import urllib.request
import json
import os
from datetime import datetime

# -----------------------------------------------------------------------------
# 설정 / Configuration
# -----------------------------------------------------------------------------
def load_telegram_config():
    """파일에서 텔레그램 설정을 로드합니다."""
    config = {"token": "", "chat_id": ""}
    try:
        with open("telegram_API_GITHUB.txt", "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    key, value = line.split(":", 1)
                    if "api" in key.lower():
                        config["token"] = value.strip()
                    elif "id" in key.lower():
                        config["chat_id"] = value.strip()
    except FileNotFoundError:
        pass
    return config

_config = load_telegram_config()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or _config["token"] or 'YOUR_BOT_TOKEN_HERE'
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") or _config["chat_id"] or 'YOUR_CHAT_ID_HERE'

from bs4 import BeautifulSoup
import ssl

def get_menu_by_contents_no(contents_no, target_day):
    """지정된 식당(contents_no)과 날짜의 식단을 가져옵니다."""
    url = f"https://www.shingu.ac.kr/cms/FR_CON/index.do?MENU_ID=1630&CONTENTS_NO={contents_no}"
    try:
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context) as response:
            html = response.read()
            soup = BeautifulSoup(html, 'html.parser')
            
            items = soup.select('ul.menu_list > li')
            for item in items:
                day_tag = item.select_one('.date strong')
                if day_tag and day_tag.text.strip() == target_day:
                    menu_dict = {}
                    boxes = item.select('.menu_box')
                    for box in boxes:
                        m_type = box.select_one('.type').get_text(strip=True)
                        m_content = box.select_one('.menu_list').get_text(separator=" ", strip=True)
                        menu_dict[m_type] = m_content
                    return menu_dict
    except Exception as e:
        print(f"Error fetching contents_no={contents_no}: {e}")
    return None

def get_today_menu():
    """웹사이트에서 오늘자 식단 데이터를 크롤링합니다."""
    weekday_map = {0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일", 4: "금요일", 5: "토요일", 6: "일요일"}
    now = datetime.now()
    target_day = now.strftime("%d") # "08" 형식
    today_str = now.strftime("%Y년 %m월 %d일") + f" ({weekday_map[now.weekday()]})"
    
    print(f"🔍 {today_str} ({target_day}일) 식단을 크롤링 중입니다...")
    
    # 1. 학생식당(서관) - CONTENTS_NO=3
    student_menu = get_menu_by_contents_no(3, target_day) or {}
    
    # 2. 교직원식당 - CONTENTS_NO=2
    staff_menu = get_menu_by_contents_no(2, target_day) or {}
    
    # 중식에서 한식/양식 분리 (학생식당)
    lunch_text = student_menu.get("중식", "")
    lunch_korean = "정보 없음"
    lunch_western = "정보 없음"
    
    if "**한식**" in lunch_text and "**양식**" in lunch_text:
        parts = lunch_text.split("**양식**")
        lunch_korean = parts[0].replace("**한식**", "").strip()
        lunch_western = parts[1].strip()
    elif lunch_text:
        lunch_korean = lunch_text

    return {
        "date": today_str,
        "student_cafeteria": {
            "breakfast": student_menu.get("조식", "정보 없음"),
            "lunch_korean": lunch_korean,
            "lunch_western": lunch_western,
            "snack": student_menu.get("분식", "정보 없음")
        },
        "staff_cafeteria": {
            "lunch": staff_menu.get("중식", "정보 없음")
        }
    }

def format_menu_message(menu):
    """식단 데이터를 텔레그렘 메시지용 텍스트로 변환합니다."""
    message = f"🏫 *신구대학교 오늘의 식단*\n📅 {menu['date']}\n\n"
    
    message += "🍱 *학생식당(서관)*\n"
    message += f"• 조식: {menu['student_cafeteria']['breakfast']}\n"
    message += f"• 중식(한식): {menu['student_cafeteria']['lunch_korean']}\n"
    message += f"• 중식(양식): {menu['student_cafeteria']['lunch_western']}\n"
    message += f"• 분식: {menu['student_cafeteria']['snack']}\n\n"
    
    message += "☕ *교직원식당*\n"
    message += f"• 중식: {menu['staff_cafeteria']['lunch']}\n\n"
    
    message += "맛있게 드세요! 😋"
    return message

def send_to_telegram(text):
    """텔레그렘으로 메시지를 전송합니다."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    data_json = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=data_json, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result.get("ok", False)
    except Exception as e:
        print(f"전송 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    print("📋 식단 정보를 가져오는 중...")
    menu = get_today_menu()
    formatted_text = format_menu_message(menu)
    
    print("🚀 텔레그렘으로 전송 시도 중...")
    if send_to_telegram(formatted_text):
        print("✅ 성공: 오늘의 식단이 텔레그렘으로 전송되었습니다!")
    else:
        print("❌ 실패: 메시지 전송에 실패했습니다.")
