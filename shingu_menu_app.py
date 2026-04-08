import tkinter as tk
from tkinter import messagebox
import urllib.request
import json
import os
from datetime import datetime, timedelta

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

# 날짜 계산 (한국어 요일)
weekday_map = {0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일", 4: "금요일", 5: "토요일", 6: "일요일"}
now = datetime.now()
tomorrow = now + timedelta(days=1)

today_str = now.strftime("%Y년 %m월 %d일") + f" ({weekday_map[now.weekday()]})"
tomorrow_str = tomorrow.strftime("%Y년 %m월 %d일") + f" ({weekday_map[tomorrow.weekday()]})"

from bs4 import BeautifulSoup
import ssl

def get_real_menu(date_obj):
    """웹사이트에서 특정 날짜의 식단을 크롤링합니다."""
    target_day = date_obj.strftime("%d")
    context = ssl._create_unverified_context()
    
    def fetch(contents_no):
        url = f"https://www.shingu.ac.kr/cms/FR_CON/index.do?MENU_ID=1630&CONTENTS_NO={contents_no}"
        try:
            with urllib.request.urlopen(url, context=context) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                items = soup.select('ul.menu_list > li')
                for item in items:
                    day_tag = item.select_one('.date strong')
                    if day_tag and day_tag.text.strip() == target_day:
                        res = []
                        for box in item.select('.menu_box'):
                            t = box.select_one('.type').get_text(strip=True)
                            c = box.select_one('.menu_list').get_text(separator=" ", strip=True)
                            res.append(f"• {t}: {c}")
                        return "\n".join(res)
        except: pass
        return "식단 정보가 없습니다."

    return fetch(3), fetch(2)

print("🌐 최신 식단 정보를 가져오는 중입니다...")
today_student, today_staff = get_real_menu(now)
tomorrow_student, tomorrow_staff = get_real_menu(tomorrow)

# 서버에서 가져온 식단 데이터 (크롤링 결과 캐싱)
MENU_DATA = {
    "today": {
        "date": today_str,
        "student": today_student,
        "staff": today_staff
    },
    "tomorrow": {
        "date": tomorrow_str,
        "student": tomorrow_student,
        "staff": tomorrow_staff
    }
}

class ShinguMenuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🏫 신구대학교 식단 알리미")
        self.root.geometry("500x650")
        self.root.configure(bg="#f0f4f7")

        # 1. 헤더
        header_frame = tk.Frame(root, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="🍱 신구대 학식 알리미", font=("Malgun Gothic", 20, "bold"), 
                 bg="#2c3e50", fg="white").pack(pady=20)

        # 2. 버튼 영역
        btn_frame = tk.Frame(root, bg="#f0f4f7")
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="📅 오늘 식단 보기", font=("Malgun Gothic", 12), width=18, height=2,
                  bg="#3498db", fg="white", activebackground="#2980b9",
                  command=lambda: self.show_and_send_menu("today")).grid(row=0, column=0, padx=10)

        tk.Button(btn_frame, text="🔜 내일 식단 보기", font=("Malgun Gothic", 12), width=18, height=2,
                  bg="#e67e22", fg="white", activebackground="#d35400",
                  command=lambda: self.show_and_send_menu("tomorrow")).grid(row=0, column=1, padx=10)

        # 3. 텍스트 박스
        self.text_area = tk.Text(root, height=18, width=55, font=("Malgun Gothic", 10), 
                                bg="white", relief=tk.FLAT, padx=10, pady=10)
        self.text_area.pack(pady=10)

        # 4. 상태 메시지
        self.status_label = tk.Label(root, text="원하시는 날짜의 버튼을 눌러주세요.", 
                                     font=("Malgun Gothic", 10), bg="#f0f4f7", fg="#7f8c8d")
        self.status_label.pack(pady=10)

    def show_and_send_menu(self, day_key):
        data = MENU_DATA[day_key]
        
        # UI 업데이트
        self.text_area.delete(1.0, tk.END)
        display_text = f"📅 날짜: {data['date']}\n\n"
        display_text += "[학생식당 (서관)]\n" + data['student'] + "\n\n"
        display_text += "[교직원식당]\n" + data['staff'] + "\n\n"
        display_text += "--------------------------------------\n"
        display_text += "텔레그램으로 전송 중입니다..."
        
        self.text_area.insert(tk.END, display_text)
        self.status_label.config(text="텔레그램 전송 중...", fg="#3498db")
        self.root.update()

        # 텔레그램 전송용 텍스트 포맷팅 (HTML 방식이 특수문자에 더 안전합니다)
        telegram_message = f"🏫 <b>신구대학교 {'오늘' if day_key=='today' else '내일'}의 식단</b>\n"
        telegram_message += f"📅 {data['date']}\n\n"
        telegram_message += "🍱 <b>학생식당(서관)</b>\n" + data['student'] + "\n\n"
        telegram_message += "☕ <b>교직원식당</b>\n" + data['staff'] + "\n\n"
        telegram_message += "맛있게 드세요! 😋"

        # 텔레그램 전송
        if self.send_to_telegram(telegram_message):
            self.status_label.config(text="✅ 텔레그램 전송 완료!", fg="#27ae60")
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, display_text.replace("텔레그램으로 전송 중입니다...", "텔레그램으로 전송되었습니다!"))
        else:
            self.status_label.config(text="❌ 전송 실패 (API 데이터 조절 필요)", fg="#e74c3c")

    def send_to_telegram(self, text):
        import ssl
        # SSL 인증서 검증을 건너뛰도록 설정
        context = ssl._create_unverified_context()
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        data_json = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=data_json, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, context=context) as response:
                result = json.loads(response.read().decode())
                if not result.get("ok"):
                    print(f"텔레그램 응답 오류: {result.get('description')}")
                return result.get("ok", False)
        except Exception as e:
            print(f"네트워크/API 오류 발생: {e}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = ShinguMenuApp(root)
    root.mainloop()
