"""
Login/Register gate — streamlit-authenticator वापरून (bcrypt password hashing,
cookie-based session). Credentials `auth_config.yaml` मध्ये साठवले जातात.

⚠️ PRODUCTION NOTE: `auth_config.yaml` मधली `cookie.key` value बदला (कुठलीही
random secret string) आणि ती file `.gitignore` मध्ये आधीच आहे — कधीही
GitHub वर commit करू नका, कारण त्यात युजर्सचे hashed passwords असतात.
मोठ्या प्रमाणावर युजर्स असतील तर हे YAML ऐवजी proper database (Postgres)
मध्ये हलवणं योग्य ठरेल — सध्या हे लहान/मध्यम प्रमाणासाठी ठीक आहे.
"""

import os
import yaml
import streamlit as str_app
import streamlit_authenticator as stauth

CONFIG_PATH = "auth_config.yaml"

DEFAULT_CONFIG = {
    "credentials": {"usernames": {}},
    "cookie": {
        "name": "alpha_quant_auth",
        "key": "CHANGE-THIS-SECRET-KEY-IN-PRODUCTION",
        "expiry_days": 30,
    },
}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if loaded:
                return loaded
    return {"credentials": {"usernames": {}}, "cookie": dict(DEFAULT_CONFIG["cookie"])}


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def get_authenticator():
    config = load_config()
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    return authenticator, config


def render_auth_gate():
    """
    Login/Register UI दाखवतं. यशस्वी login शिवाय पुढे जाऊ देत नाही (st.stop()).
    Login झाल्यावर st.session_state['username'] आणि ['name'] उपलब्ध होतात.
    Return: authenticator instance (sidebar मध्ये logout बटणासाठी लागतो).
    """
    authenticator, config = get_authenticator()

    if str_app.session_state.get("authentication_status") is not True:
        tab_login, tab_register = str_app.tabs(["🔑 Login", "🆕 नवीन खातं (Register)"])

        with tab_login:
            try:
                authenticator.login(location="main")
            except Exception as e:
                str_app.error(f"Login error: {e}")

        with tab_register:
            try:
                email, username, name = authenticator.register_user(location="main", captcha=False)
                if email:
                    save_config(config)
                    str_app.success("✅ खातं तयार झालं! आता 'Login' tab वापरून लॉगिन करा.")
            except Exception as e:
                str_app.error(f"Registration error: {e}")

    auth_status = str_app.session_state.get("authentication_status")

    if auth_status is False:
        str_app.error("❌ Username/password चुकीचे आहे.")
        str_app.stop()
    elif auth_status is not True:
        str_app.info("👆 कृपया आधी Login करा किंवा नवीन खातं तयार करा.")
        str_app.stop()

    return authenticator
