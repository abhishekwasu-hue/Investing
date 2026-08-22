import streamlit as str_app
import streamlit.components.v1 as components

import payments
import subscription
from auth import render_auth_gate
from app_state import render_disclaimer_banner

str_app.set_page_config(page_title="Upgrade to Pro | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
username = str_app.session_state["username"]

str_app.title("💳 Upgrade to Pro")

tier = subscription.get_tier(username)
if tier == "PRO":
    expiry = subscription.get_expiry(username)
    str_app.success(f"✅ तुम्ही आधीच Pro member आहात (वैध: {expiry} पर्यंत).")
    str_app.stop()

# ---- Plan comparison ----
c1, c2 = str_app.columns(2)
with c1:
    str_app.subheader("🆓 Free")
    str_app.markdown(f"""
    - {subscription.FREE_LIMITS['pdf_report']} PDF Research Reports / दिवस
    - {subscription.FREE_LIMITS['sector_screener']} Sector Screener runs / दिवस
    - Free NSE (delayed) data
    - सगळे Technical/Fundamental पेजेस
    """)
with c2:
    str_app.subheader(f"⭐ Pro — ₹{payments.PRO_PLAN_PRICE_INR}/महिना")
    str_app.markdown("""
    - **Unlimited** PDF Research Reports
    - **Unlimited** Sector Screener runs
    - Priority support
    - भविष्यातील नवीन features आधी
    """)

str_app.markdown("---")

# ---- Razorpay redirect-based callback हाताळणी ----
params = str_app.query_params
if all(k in params for k in ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature")):
    ok = payments.verify_payment(
        params["razorpay_order_id"], params["razorpay_payment_id"], params["razorpay_signature"]
    )
    if ok:
        payments.activate_pro(username)
        str_app.success("🎉 Payment यशस्वी! तुम्ही आता Pro member आहात.")
        str_app.query_params.clear()
        str_app.balloons()
        str_app.stop()
    else:
        str_app.error("❌ Payment verification अयशस्वी झालं. पुन्हा प्रयत्न करा किंवा support ला संपर्क करा.")

if not payments.is_configured():
    str_app.warning(
        "⚠️ Payment gateway अजून सेटअप केलेलं नाही. Razorpay Dashboard वरून API keys घेऊन "
        "`RAZORPAY_KEY_ID` आणि `RAZORPAY_KEY_SECRET` environment variables / Streamlit secrets मध्ये टाका."
    )
    str_app.stop()

order = payments.create_order(username)
if order is None:
    str_app.error("❌ Order तयार करता आला नाही. Razorpay keys तपासा किंवा नंतर प्रयत्न करा.")
    str_app.stop()

checkout_html = f"""
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<button id="rzp-button" style="background:#3182ce;color:white;padding:14px 28px;border:none;
  border-radius:8px;font-size:16px;font-weight:bold;cursor:pointer;">
  Pay ₹{payments.PRO_PLAN_PRICE_INR} & Upgrade to Pro
</button>
<script>
document.getElementById('rzp-button').onclick = function (e) {{
    var options = {{
        "key": "{payments.RAZORPAY_KEY_ID}",
        "amount": "{order['amount']}",
        "currency": "INR",
        "order_id": "{order['id']}",
        "name": "Alpha Quant Pro Terminal",
        "description": "Pro Plan — 1 Month",
        "handler": function (response) {{
            var baseUrl = window.top.location.href.split('?')[0];
            var url = baseUrl
                + "?razorpay_order_id=" + response.razorpay_order_id
                + "&razorpay_payment_id=" + response.razorpay_payment_id
                + "&razorpay_signature=" + response.razorpay_signature;
            window.top.location.href = url;
        }}
    }};
    var rzp = new Razorpay(options);
    rzp.open();
    e.preventDefault();
}}
</script>
"""
components.html(checkout_html, height=90)

str_app.caption(
    "⚠️ Payment Razorpay च्या सुरक्षित checkout द्वारे होतो — कार्ड/UPI माहिती या app मध्ये कधीही साठवली जात नाही."
)
