"""
Telegram Bot द्वारे संदेश/फाईल पाठवणं — Telegram चं अधिकृत Bot API वापरून
(कुठलंही वेगळं SDK लागत नाही, थेट HTTP requests).

Setup:
  1. Telegram मध्ये @BotFather शी बोला -> /newbot -> bot token मिळेल
  2. तुमच्या bot ला एक मेसेज पाठवा (किंवा group मध्ये add करा)
  3. https://api.telegram.org/bot<TOKEN>/getUpdates उघडून तुमचा chat_id शोधा
  4. TELEGRAM_BOT_TOKEN आणि TELEGRAM_CHAT_ID GitHub Actions secrets मध्ये टाका

⚠️ हा sandbox मधून api.telegram.org पर्यंत पोहोचता येत नाही — logic बरोबर
आहे (Telegram च्या अधिकृत Bot API डॉक्युमेंटेशन प्रमाणे), पण live call
टेस्ट करता आलेली नाही. पहिल्यांदा GitHub Actions वरून manually ट्रिगर
करून एकदा प्रत्यक्ष पडताळून घ्या.
"""

import requests

from secrets_helper import read_secret

TELEGRAM_BOT_TOKEN = read_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = read_secret("TELEGRAM_CHAT_ID")


def is_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_message(text: str) -> bool:
    if not is_configured():
        print("[Telegram] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID सेट नाहीत — मेसेज वगळला.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text[:4096], "parse_mode": "HTML"}, timeout=10
        )
        resp.raise_for_status()
        print("[Telegram] मेसेज पाठवला.")
        return True
    except Exception as e:
        print(f"[Telegram] send_message अयशस्वी: {e}")
        return False


def send_document(file_bytes: bytes, filename: str, caption: str = "") -> bool:
    """PDF/कुठलीही फाईल Telegram document म्हणून पाठवतो (कमाल ५० MB, आपले PDF त्यापेक्षा खूप लहान असतात)."""
    if not is_configured():
        print("[Telegram] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID सेट नाहीत — फाईल वगळली.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        files = {"document": (filename, file_bytes, "application/pdf")}
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1024]}
        resp = requests.post(url, data=data, files=files, timeout=30)
        resp.raise_for_status()
        print(f"[Telegram] फाईल पाठवली: {filename}")
        return True
    except Exception as e:
        print(f"[Telegram] send_document अयशस्वी: {e}")
        return False
