"""
Razorpay payment integration — Pro plan साठी.

Setup: Razorpay Dashboard (https://dashboard.razorpay.com) वरून Key ID +
Key Secret घ्या, आणि environment variables म्हणून सेट करा:
    RAZORPAY_KEY_ID=rzp_live_xxxx (किंवा test साठी rzp_test_xxxx)
    RAZORPAY_KEY_SECRET=xxxx
(Streamlit Cloud वर हे App Settings -> Secrets मध्ये टाका.)

⚠️ हा कोड योग्य आणि Razorpay च्या अधिकृत Python SDK पॅटर्नप्रमाणे लिहिलाय,
पण sandbox मधून razorpay.com पर्यंत पोहोचता येत नसल्याने live payment
प्रत्यक्ष टेस्ट करता आलेला नाही. जाण्याआधी Razorpay च्या Test Mode मध्ये
(test API keys + test card) एकदा संपूर्ण flow स्वतः चालवून बघा.
"""

import os
from datetime import date, timedelta

import razorpay

import subscription

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

PRO_PLAN_PRICE_INR = 499
PRO_PLAN_DURATION_DAYS = 30


def is_configured() -> bool:
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def _client():
    if not is_configured():
        return None
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_order(username: str):
    """Razorpay order तयार करतो. Keys सेट नसतील तर None परत देतो (fake order कधीच नाही)."""
    client = _client()
    if client is None:
        return None
    try:
        return client.order.create({
            "amount": PRO_PLAN_PRICE_INR * 100,  # पैसे (paise) मध्ये
            "currency": "INR",
            "notes": {"username": username, "plan": "PRO_MONTHLY"},
        })
    except Exception as e:
        print(f"[payments] order creation failed: {e}")
        return None


def verify_payment(order_id: str, payment_id: str, signature: str) -> bool:
    client = _client()
    if client is None:
        return False
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception as e:
        print(f"[payments] verification error: {e}")
        return False


def activate_pro(username: str):
    expiry = (date.today() + timedelta(days=PRO_PLAN_DURATION_DAYS)).isoformat()
    subscription.set_pro(username, expiry)
