# app_v26.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3, bcrypt, json, requests, base64
from datetime import datetime, date, timedelta

# Optional (SMTP for reset; safe-guarded)
import smtplib, ssl, secrets, string
from email.mime.text import MIMEText

# =============== CONSTANTS ===============
APP_TITLE = "Carioca"
DB_FILE = "carioca_v26.db"
DEFAULT_FDC = "6P4rVEgRsNBnS8bAYqlq2DEDqiaf72txvmATH05g"
DEFAULT_HEADER_URL = "https://images.unsplash.com/photo-1544986581-efac024faf62?q=80&w=1400&auto=format&fit=crop"

# =============== PAGE CONFIG ===============
st.set_page_config(page_title="Carioca", page_icon="🌴", layout="wide")

def css_tropical(header_url: str):
    return f'''
    <style>
    .stApp {{
      background: linear-gradient(135deg,#FF7E5F 0%,#FFB88C 40%,#FFD86F 70%,#FF5F6D 100%) fixed;
    }}
    .block-container {{
      backdrop-filter: blur(6px);
      background-color: rgba(255,255,255,0.88);
      border-radius: 24px;
      padding: 1rem 1rem;
    }}
    @media (min-width: 768px) {{
      .block-container {{ padding: 2rem 2.2rem; }}
    }}
    .metric-card {{ border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.75); border: 1px solid rgba(255,255,255,0.6); }}
    .pill {{ padding: 4px 10px; border-radius: 999px; background: rgba(0,0,0,0.06); font-size: 12px; font-weight: 600; }}
    img.muscle {{ max-width: 140px; border-radius: 12px; border: 1px solid #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.15); }}
    .header-bar {{
      position: relative;
      width: 100%;
      min-height: 90px;
      border-radius: 18px;
      background: url('{header_url}') center center / contain no-repeat;
      background-color: rgba(255,255,255,0.6);
      margin-bottom: 10px;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.6rem 0.8rem;
    }}
    @media (min-width: 768px) {{
      .header-bar {{ min-height: 120px; padding: 0.8rem 1.0rem; }}
    }}
    .header-left {{ display:flex; flex-direction:column; gap:4px; }}
    .header-title {{ font-size: 1.2rem; font-weight: 800; margin:0; }}
    @media (min-width: 768px) {{
      .header-title {{ font-size: 1.6rem; }}
    }}
    .header-sub {{ font-size: .9rem; opacity:.9; }}
    .header-avatar {{ text-align: right; }}
    .header-avatar img {{
      border-radius: 50%;
      border: 2px solid rgba(255,255,255,0.8);
      box-shadow: 0 4px 18px rgba(0,0,0,0.15);
    }}
    </style>
    '''

def css_minimal(header_url: str):
    return f'''
    <style>
    .stApp {{ background: #f5f7fb; }}
    .block-container {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 1rem 1rem; }}
    @media (min-width: 768px) {{
      .block-container {{ padding: 2rem 2.2rem; }}
    }}
    .metric-card {{ border-radius: 12px; padding: 14px; background: #fff; border: 1px solid #e5e7eb; }}
    .pill {{ padding: 3px 8px; border-radius: 12px; background: #eef2ff; font-size: 12px; font-weight: 600; }}
    img.muscle {{ max-width: 140px; border-radius: 12px; border: 1px solid #e5e7eb; }}
    .header-bar {{
      position: relative;
      width: 100%;
      min-height: 90px;
      border-radius: 18px;
      background: url('{header_url}') center center / contain no-repeat;
      background-color: #ffffff;
      margin-bottom: 10px;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.6rem 0.8rem;
    }}
    @media (min-width: 768px) {{
      .header-bar {{ min-height: 120px; padding: 0.8rem 1.0rem; }}
    }}
    .header-left {{ display:flex; flex-direction:column; gap:4px; }}
    .header-title {{ font-size: 1.2rem; font-weight: 800; margin:0; }}
    @media (min-width: 768px) {{
      .header-title {{ font-size: 1.6rem; }}
    }}
    .header-sub {{ font-size: .9rem; opacity:.9; }}
    .header-avatar {{ text-align: right; }}
    .header-avatar img {{
      border-radius: 50%;
      border: 2px solid #e5e7eb;
      box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }}
    </style>
    '''

# =============== i18n (inline) ===============
TEXT = {
    "en": {
        "language": "Language",
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "remember_me": "Remember Me",
        "password_reset": "Password Reset",
        "email": "E-mail",
        "send_reset": "Send Reset E-mail",
        "register": "Register",
        "create_account": "Create Account",
        "logout": "Logout",
        "theme": "Theme",
        "profile": "Profile",
        "deficit_calc": "Deficit Calculator",
        "nutrition": "Nutrition",
        "workout": "Workout",
        "progress": "Progress",
        "reminders": "Reminders",
        "summary": "Summary",
        "birthdate": "Birthdate",
        "age": "Age",
        "sex": "Sex",
        "male": "male",
        "female": "female",
        "height_cm": "Height (cm)",
        "weight_kg": "Weight (kg)",
        "waist_cm": "Waist (cm)",
        "bodyfat_pct": "Body Fat (%)",
        "target_weight": "Target Weight (kg)",
        "avatar": "Avatar",
        "upload_photo": "Upload Photo",
        "header_image": "Header Image (optional)",
        "activity": "Activity Level",
        "training_days": "Training Days / Week",
        "fasting": "Fasting",
        "fasting_12_12": "12:12 Intermittent Fasting",
        "fasting_14_10": "14:10 Intermittent Fasting",
        "fasting_16_8": "16:8 Intermittent Fasting",
        "fasting_18_6": "18:6 Intermittent Fasting",
        "plan_type": "Training Plan",
        "meal_structure": "Meal Structure",
        "two_plus_one": "2 Main + 1 Snack",
        "three_meals": "3 Meals",
        "four_meals": "4 Meals",
        "first_name": "First Name",
        "last_name": "Last Name",
        "username_change": "Username",
        "new_username": "New Username",
        "save_profile": "Save Profile",
        "bmr": "BMR",
        "tdee": "TDEE",
        "workout_day_calories": "Workout Day Target",
        "rest_day_calories": "Rest Day Target",
        "macros": "Macros",
        "day_type": "Day Type",
        "workout_day": "Workout Day",
        "rest_day": "Rest Day",
        "deficit_percent": "Deficit (%)",
        "target_cal": "Target Calories",
        "weekly_loss": "Weekly Loss",
        "three_months_weight": "Weight (3 Months)",
        "log_food": "Log Food",
        "date": "Date",
        "meal": "Meal",
        "search_food": "Search Food",
        "amount_g": "Amount (g)",
        "result_lang": "Result Language",
        "api_results": "API Results",
        "no_results": "No results",
        "search_tip": "Try both English and Turkish terms",
        "select_food": "Select Item",
        "add": "Add to Day",
        "today_log": "Today's Log",
        "total": "Total",
        "kcal": "kcal",
        "protein": "Protein",
        "carbs": "Carbs",
        "fat": "Fat",
        "workout_plan": "Workout Plan",
        "day_picker": "Day",
        "video_guide": "Video Guide",
        "progress_title": "Progress",
        "weight_entry": "Enter Your Weight",
        "add_weight": "Add Weight",
        "timeline": "Timeline",
        "remind_water": "Water Reminder",
        "remind_posture": "Posture Reminder",
        "summary_date": "Summary Date",
        "range": "Range",
        "range_week": "1 Week",
        "range_month": "1 Month",
        "range_6m": "6 Months",
        "range_custom": "Custom",
    },
    "tr": {
        "language": "Dil",
        "login": "Giriş",
        "username": "Kullanıcı Adı",
        "password": "Şifre",
        "remember_me": "Beni Hatırla",
        "password_reset": "Şifre Sıfırlama",
        "email": "E-posta",
        "send_reset": "Sıfırlama E-postası Gönder",
        "register": "Kayıt Ol",
        "create_account": "Hesap Oluştur",
        "logout": "Çıkış",
        "theme": "Tema",
        "profile": "Profil",
        "deficit_calc": "Açık Hesaplayıcı",
        "nutrition": "Beslenme",
        "workout": "Antrenman",
        "progress": "İlerleme",
        "reminders": "Hatırlatıcılar",
        "summary": "Özet",
        "birthdate": "Doğum Tarihi",
        "age": "Yaş",
        "sex": "Cinsiyet",
        "male": "erkek",
        "female": "kadın",
        "height_cm": "Boy (cm)",
        "weight_kg": "Kilo (kg)",
        "waist_cm": "Bel Ölçüsü (cm)",
        "bodyfat_pct": "Yağ Oranı (%)",
        "target_weight": "Hedef Kilo (kg)",
        "avatar": "Profil Fotoğrafı",
        "upload_photo": "Fotoğraf Yükle",
        "header_image": "Header Görseli (opsiyonel)",
        "activity": "Aktivite Düzeyi",
        "training_days": "Haftalık Antrenman Gün Sayısı",
        "fasting": "Aralıklı Oruç",
        "fasting_12_12": "12:12 Aralıklı Oruç",
        "fasting_14_10": "14:10 Aralıklı Oruç",
        "fasting_16_8": "16:8 Aralıklı Oruç",
        "fasting_18_6": "18:6 Aralıklı Oruç",
        "plan_type": "Antrenman Planı",
        "meal_structure": "Öğün Yapısı",
        "two_plus_one": "2 Ana + 1 Ara",
        "three_meals": "3 Öğün",
        "four_meals": "4 Öğün",
        "first_name": "İsim",
        "last_name": "Soyisim",
        "username_change": "Kullanıcı Adı",
        "new_username": "Yeni Kullanıcı Adı",
        "save_profile": "Profili Kaydet",
        "bmr": "BMR",
        "tdee": "TDEE",
        "workout_day_calories": "Antrenman Günü Hedefi",
        "rest_day_calories": "Dinlenme Günü Hedefi",
        "macros": "Makrolar",
        "day_type": "Gün Tipi",
        "workout_day": "Antrenman Günü",
        "rest_day": "Dinlenme Günü",
        "deficit_percent": "Açık (%)",
        "target_cal": "Hedef Kalori",
        "weekly_loss": "Haftalık Kayıp",
        "three_months_weight": "3 Ay Sonrası Kilo",
        "log_food": "Gıda Kaydı",
        "date": "Tarih",
        "meal": "Öğün",
        "search_food": "Gıda Ara",
        "amount_g": "Miktar (g)",
        "result_lang": "Sonuç Dili",
        "api_results": "API Sonuçları",
        "no_results": "Sonuç yok",
        "search_tip": "İngilizce ve Türkçe terimleri deneyin",
        "select_food": "Öğe Seç",
        "add": "Güne Ekle",
        "today_log": "Bugünün Kaydı",
        "total": "Toplam",
        "kcal": "kcal",
        "protein": "Protein",
        "carbs": "Karb",
        "fat": "Yağ",
        "workout_plan": "Antrenman Planı",
        "day_picker": "Gün",
        "video_guide": "Video Rehberi",
        "progress_title": "İlerleme",
        "weight_entry": "Kilonu Gir",
        "add_weight": "Kilo Ekle",
        "timeline": "Zaman / Timeline",
        "remind_water": "Su Hatırlatıcısı",
        "remind_posture": "Duruş Hatırlatıcısı",
        "summary_date": "Özet Tarihi",
        "range": "Aralık",
        "range_week": "1 Hafta",
        "range_month": "1 Ay",
        "range_6m": "6 Ay",
        "range_custom": "Özel",
    }
}
def _(key):  # translate
    lang = st.session_state.get("lang","en")
    return TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"].get(key, key))

# =============== DB ===============
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            pw_hash  BLOB NOT NULL,
            lang     TEXT DEFAULT 'en',
            theme    TEXT DEFAULT 'tropical',
            avatar   TEXT,
            header_bg TEXT,
            email    TEXT,
            fdc_key  TEXT,
            first_name TEXT,
            last_name TEXT,
            plan_type TEXT,
            meal_structure TEXT,
            age INT, sex TEXT, height_cm REAL, weight_kg REAL, bodyfat REAL,
            waist_cm REAL,
            birthdate TEXT,
            activity TEXT, target_weight REAL, training_days INT, fasting TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weights(
            username TEXT, dt TEXT, weight REAL, waist REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_logs(
            username TEXT, dt TEXT, meal TEXT, food_name TEXT, grams REAL,
            kcal REAL, protein REAL, carbs REAL, fat REAL, sugars REAL, fiber REAL, sodium REAL, salt REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workout_logs(
            username TEXT, dt TEXT, day TEXT, exercise TEXT, target_sets INT, target_reps INT,
            perf_sets INT, perf_reps INT, calories REAL
        )
    """)
    # --- migrations (add columns if missing) ---
    def ensure_column(table, col, type_):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {type_}")
    ensure_column("users","first_name","TEXT")
    ensure_column("users","last_name","TEXT")
    ensure_column("users","waist_cm","REAL")
    ensure_column("users","header_bg","TEXT")
    # weights table waist already present in creation above; but ensure if old DB
    ensure_column("weights","waist","REAL")
    conn.commit()
    return conn
conn = get_conn()

def hash_pw(pw: str) -> bytes:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())

def check_pw(pw: str, h: bytes) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), h)
    except Exception:
        return False

# =============== EMAIL RESET (optional) ===============
def send_reset_email(to_email: str, username: str):
    try:
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        body = f"Merhaba {username},\n\nCarioca şifre sıfırlama kodun: {token}\n\nBu kodu uygulamadaki şifre sıfırlama alanına gir."
        msg = MIMEText(body)
        msg["Subject"] = "Carioca Şifre Sıfırlama"
        msg["From"] = st.secrets["smtp"]["from"]
        msg["To"] = to_email
        context = ssl.create_default_context()
        with smtplib.SMTP(st.secrets["smtp"]["host"], st.secrets["smtp"]["port"]) as server:
            server.starttls(context=context)
            server.login(st.secrets["smtp"]["user"], st.secrets["smtp"]["password"])
            server.sendmail(msg["From"], [to_email], msg.as_string())
        st.success("Reset e-mail gönderildi. Gelen kutunu kontrol et.")
    except Exception:
        st.warning("Şifre sıfırlama e-postası gönderilemedi (SMTP secrets eksik olabilir).")

# =============== LOGIN / REGISTER ===============
def handle_login_success(u, remember, lang_pick, row):
    st.session_state["user"] = u
    st.session_state["remember"] = remember
    st.session_state["lang"] = row[1] or lang_pick
    st.session_state["theme"] = "tropical"
    st.rerun()

def login_register_ui():
    # Login ekranı her zaman tropikal tema
    st.markdown(css_tropical(DEFAULT_HEADER_URL), unsafe_allow_html=True)
    # Üst bar basitleştirilmiş
    st.sidebar.header("Carioca 🌴")
    lang_pick = st.sidebar.radio(_("language"), ["en", "tr"],
                                 format_func=lambda x: "English" if x=="en" else "Türkçe",
                                 key="lang")

    left, right = st.columns(1 if st.session_state.get("mobile") else 2)

    # ---- Login (Enter enabled) ----
    with left:
        st.subheader(_("login"))
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input(_("username"), key="login_user")
            p = st.text_input(_("password"), type="password", key="login_pw")
            remember = st.checkbox(_("remember_me"), value=True, key="remember_me")
            submitted = st.form_submit_button(_("login"))
        # JS fallback: Enter -> click primary button
        st.markdown("""
            <script>
            document.addEventListener('keydown', function(e) {
              if (e.key === 'Enter') {
                const btns = window.parent.document.querySelectorAll('button[kind="primary"]');
                if (btns && btns.length) { btns[0].click(); }
              }
            });
            </script>
        """, unsafe_allow_html=True)

        if submitted and u and p:
            row = conn.execute("SELECT pw_hash, lang FROM users WHERE username=?", (u,)).fetchone()
            if row and check_pw(p, row[0]):
                st.session_state["pending_login"] = (u, remember, lang_pick, row)
                st.rerun()
            else:
                st.error("Invalid credentials / Geçersiz bilgiler")

        st.divider()
        st.subheader(_("password_reset"))
        email = st.text_input(_("email"))
        if st.button(_("send_reset")):
            if email:
                send_reset_email(email, st.session_state.get("login_user","user"))
            else:
                st.warning("Please provide an e-mail.")

    # ---- Register ----
    with (right if not st.session_state.get("mobile") else st.container()):
        st.subheader(_("register"))
        ru = st.text_input(_("username")+" *", key="ru")
        rp = st.text_input(_("password")+" *", type="password", key="rp")
        if st.button(_("create_account")):
            if not ru or not rp:
                st.warning("Fill required fields")
            else:
                try:
                    conn.execute(
                        """INSERT INTO users(username, pw_hash, lang, theme, fdc_key, created_at)
                           VALUES(?,?,?,?,?,?)""",
                        (ru, hash_pw(rp), lang_pick, "tropical", DEFAULT_FDC, datetime.utcnow().isoformat()),
                    )
                    conn.commit()
                    st.success("Registered. Please log in.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

    if "pending_login" in st.session_state:
        u, remember, lang_pick, row = st.session_state.pop("pending_login")
        handle_login_success(u, remember, lang_pick, row)

# Mobile flag (rough)
st.session_state.setdefault("mobile", False)

if "user" not in st.session_state:
    login_register_ui()
    st.stop()

# =============== LOAD USER ===============
row = conn.execute("""
    SELECT username, lang, theme, avatar, header_bg, email, fdc_key, first_name, last_name,
           plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, waist_cm,
           birthdate, activity, target_weight, training_days, fasting
    FROM users WHERE username=?
""", (st.session_state["user"],)).fetchone()

if not row:
    st.warning("User not found. Please login again.")
    for k in ["user", "lang", "theme", "fdc_key"]:
        st.session_state.pop(k, None)
    st.rerun()

(u, lang, theme, avatar, header_bg, email, fdc_key, first_name, last_name,
 plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, waist_cm,
 birthdate, activity, target_weight, training_days, fasting) = row

st.session_state.setdefault("lang", lang or "en")
st.session_state.setdefault("theme", theme or "tropical")
st.session_state.setdefault("fdc_key", fdc_key or DEFAULT_FDC)

# =============== THEME/HEADER ===============
header_image_url = header_bg or DEFAULT_HEADER_URL
picked_theme = st.sidebar.radio(
    _("theme"),
    ["tropical","minimal"],
    index=0 if (st.session_state["theme"]=="tropical") else 1,
    format_func=lambda x: "🌴 Tropical" if x=="tropical" else "⚪ Minimal"
)
st.session_state["theme"] = picked_theme
st.markdown(css_tropical(header_image_url) if picked_theme=="tropical" else css_minimal(header_image_url), unsafe_allow_html=True)

# Top bar
if st.sidebar.button(_("logout")):
    st.session_state.clear(); st.rerun()
st.sidebar.radio(_("language"), ["en","tr"], key="lang", format_func=lambda x: "English" if x=="en" else "Türkçe")

# Header with avatar + name
st.markdown('<div class="header-bar">', unsafe_allow_html=True)
c1, c2 = st.columns([8,1])
with c1:
    full_name = f"{first_name or ''} {last_name or ''}".strip()
    st.markdown(f'<div class="header-left"><div class="header-title">{APP_TITLE}</div><div class="header-sub">{full_name if full_name else ""}</div></div>', unsafe_allow_html=True)
with c2:
    if avatar:
        st.markdown('<div class="header-avatar">', unsafe_allow_html=True)
        st.image(avatar, width=88)
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =============== HELPERS ===============
def mifflin_st_jeor(sex: str, weight, height_cm, age):
    if age is None: age = 30
    if height_cm is None: height_cm = 175
    if weight is None: weight = 80.0
    if sex == "male":
        return 10 * weight + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height_cm - 5 * age - 161

def activity_factor(level: str):
    # WHO-ish factors; labels shown user-friendly below
    return {"Sedentary": 1.2, "Light": 1.35, "Moderate": 1.55, "High": 1.75, "Very High": 1.95}.get(level, 1.35)

def macro_split(cal, workout=True, weight=80):
    if weight is None: weight = 80
    protein_g = round(2.0 * float(weight))
    carbs_g = round((1.8 if workout else 0.8) * float(weight))
    fat_g = max(0, round((cal - (protein_g * 4 + carbs_g * 4)) / 9))
    return protein_g, carbs_g, fat_g

PLAN_LABELS = {
    "full_body": "Full Body",
    "ppl": "Push • Pull • Legs",
    "upper_lower": "Upper / Lower",
    "cardio_core": "Cardio + Core",
}
MEAL_LABELS = {
    "two_plus_one": _("two_plus_one"),
    "three_meals": _("three_meals"),
    "four_meals": _("four_meals"),
}
FASTING_OPTIONS = {
    "12:12": _("fasting_12_12"),
    "14:10": _("fasting_14_10"),
    "16:8": _("fasting_16_8"),
    "18:6": _("fasting_18_6"),
}
# Activity labels with short parenthesis text (2 words max)
ACTIVITY_OPTIONS = [
    "Sedentary (Desk Work)",
    "Light (1 Day)",
    "Moderate (2-3 Days)",
    "High (4-5 Days)",
    "Very High (6-7 Days)",
]
def activity_label_to_key(label: str) -> str:
    return label.split(" (")[0]  # "Sedentary", etc.

# =============== TABS ===============
tabs = st.tabs([_("profile"), _("deficit_calc"), _("nutrition"), _("workout"), _("progress"), _("reminders"), _("summary")])

# =============== PROFILE ===============
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    with c1:
        # Birthdate (1950–2035)
        min_bd, max_bd = date(1950, 1, 1), date(2035, 12, 31)
        bd_val = pd.to_datetime(birthdate).date() if birthdate else None
        bd_input = st.date_input(_("birthdate"), value=bd_val, min_value=min_bd, max_value=max_bd)
        if bd_input:
            today = date.today()
            age_calc = today.year - bd_input.year - ((today.month, today.day) < (bd_input.month, bd_input.day))
            age = age_calc

        first_name = st.text_input(_("first_name"), value=first_name or "")
        last_name = st.text_input(_("last_name"), value=last_name or "")

        age = st.number_input(_("age"), min_value=10, max_value=100, value=int(age) if age else 30)
        sex = st.selectbox(_("sex"), ["male","female"], index=0 if (sex or "male")=="male" else 1)
        height_cm = st.number_input(_("height_cm"), min_value=120, max_value=230, value=int(height_cm) if height_cm else 175)
        waist_cm = st.number_input(_("waist_cm"), min_value=40.0, max_value=200.0, value=float(waist_cm) if waist_cm else 90.0, step=0.1)

        st.write("—"); st.subheader(_("username_change"))
        newu = st.text_input(_("new_username"), value=u)
        if st.button("Apply Username"):
            if newu and newu != u:
                try:
                    conn.execute("UPDATE users SET username=? WHERE username=?", (newu, u))
                    conn.execute("UPDATE weights SET username=? WHERE username=?", (newu, u))
                    conn.execute("UPDATE food_logs SET username=? WHERE username=?", (newu, u))
                    conn.execute("UPDATE workout_logs SET username=? WHERE username=?", (newu, u))
                    conn.commit(); st.session_state["user"] = newu; st.success("Username updated. Please re-login.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

    with c2:
        weight_kg = st.number_input(_("weight_kg"), min_value=30.0, max_value=250.0, value=float(weight_kg) if weight_kg else 80.0, step=0.1)
        bodyfat_val = float(bodyfat) if bodyfat not in (None,"") else 0.0
        bodyfat_in = st.number_input(_("bodyfat_pct"), min_value=0.0, max_value=60.0, value=bodyfat_val, step=0.1)
        bodyfat = bodyfat_in if bodyfat_in>0 else None
        target_weight = st.number_input(_("target_weight"), min_value=30.0, max_value=250.0, value=float(target_weight) if target_weight else 80.0, step=0.1)

        st.subheader(_("avatar"))
        photo = st.file_uploader(_("upload_photo"), type=["png","jpg","jpeg"])
        if photo:
            b64 = base64.b64encode(photo.read()).decode("utf-8")
            avatar = f"data:image/{photo.type.split('/')[-1]};base64,{b64}"

        st.subheader(_("header_image"))
        header_upload = st.file_uploader("", type=["png","jpg","jpeg"], key="header_upl")
        if header_upload:
            hb64 = base64.b64encode(header_upload.read()).decode("utf-8")
            header_bg = f"data:image/{header_upload.type.split('/')[-1]};base64,{hb64}"

    with c3:
        # Activity dropdown with WHO-like labels
        current_act_label = None
        # map stored activity (old) to label
        stored_key = activity if activity else "Light"
        # try to find label starting with stored key
        for lbl in ACTIVITY_OPTIONS:
            if lbl.startswith(stored_key if stored_key[0].isupper() else stored_key.capitalize()):
                current_act_label = lbl; break
        if not current_act_label:
            current_act_label = "Light (1 Day)"
        activity_label = st.selectbox(_("activity"), ACTIVITY_OPTIONS, index=ACTIVITY_OPTIONS.index(current_act_label))

        training_days = st.slider(_("training_days"), 1, 7, int(training_days) if training_days else 5)
        fasting_map_keys = list(FASTING_OPTIONS.keys())
        fasting_label = st.selectbox(_("fasting"), fasting_map_keys,
                                     index=fasting_map_keys.index(fasting) if fasting in fasting_map_keys else fasting_map_keys.index("16:8"),
                                     format_func=lambda k: FASTING_OPTIONS[k])

        plan_type = st.selectbox(_("plan_type"), list(PLAN_LABELS.keys()),
                                 index=list(PLAN_LABELS.keys()).index(plan_type or "full_body"),
                                 format_func=lambda k: PLAN_LABELS[k])
        meal_structure = st.selectbox(_("meal_structure"), list(MEAL_LABELS.keys()),
                                      index=list(MEAL_LABELS.keys()).index(meal_structure or "two_plus_one"),
                                      format_func=lambda k: MEAL_LABELS[k])
        email = st.text_input(_("email"), value=email or "")
        fdc_key = st.text_input("USDA FDC API Key (optional)",
                                value=st.session_state.get("fdc_key") or DEFAULT_FDC,
                                help="If provided, FDC results are included.")

    if st.button(_("save_profile"), type="primary"):
        conn.execute("""
            UPDATE users SET
                first_name=?, last_name=?, lang=?, theme=?, avatar=?, header_bg=?, email=?, fdc_key=?, plan_type=?, meal_structure=?,
                age=?, sex=?, height_cm=?, weight_kg=?, bodyfat=?, waist_cm=?, birthdate=?, activity=?, target_weight=?, training_days=?, fasting=?
            WHERE username=?
        """, (first_name, last_name, st.session_state["lang"], st.session_state["theme"], avatar, header_bg, email, fdc_key, plan_type, meal_structure,
              age, sex, height_cm, weight_kg, bodyfat, waist_cm, (bd_input.isoformat() if bd_input else None),
              activity_label_to_key(activity_label), target_weight, training_days, fasting_label, u))
        conn.commit(); st.session_state["fdc_key"] = fdc_key; st.success("Profile updated")

    # Metrics
    bmr = mifflin_st_jeor(sex, weight_kg, height_cm, age)
    tdee = bmr * activity_factor(activity_label_to_key(activity_label))
    wcal = round(tdee * 0.75); rcal = round((bmr * 1.35) * 0.75)
    pc_w, cc_w, fc_w = macro_split(wcal, workout=True, weight=weight_kg); pc_r, cc_r, fc_r = macro_split(rcal, workout=False, weight=weight_kg)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(_("bmr"), f"{int(bmr)} {_('kcal')}"); k2.metric(_("tdee"), f"{int(tdee)} {_('kcal')}")
    k3.metric(_("workout_day_calories"), f"{wcal} {_('kcal')}"); k4.metric(_("rest_day_calories"), f"{rcal} {_('kcal')}")

# =============== DEFICIT CALCULATOR ===============
with tabs[1]:
    day_type = st.selectbox(_("day_type"), [_("workout_day"), _("rest_day")])
    deficit = st.slider(_("deficit_percent"), 5, 35, 25, step=1)
    base_tdee = bmr * activity_factor(activity_label_to_key(activity_label)) if day_type==_("workout_day") else bmr * 1.35
    target_cal = round(base_tdee*(1-deficit/100))
    weekly_loss = round(((base_tdee-target_cal)*7)/7700,2)
    weight_3m = round((weight_kg or 80) - weekly_loss*12, 1)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(_("tdee"), int(base_tdee)); c2.metric(_("target_cal"), int(target_cal)); c3.metric(_("weekly_loss"), f"{weekly_loss} kg"); c4.metric(_("three_months_weight"), f"{weight_3m} kg")

# =============== FOOD SEARCH HELPERS ===============
def off_search(q, lang_code="en", page_size=25):
    try:
        url="https://world.openfoodfacts.org/cgi/search.pl"
        params={"search_terms":q,"search_simple":1,"action":"process","json":1,"page_size":page_size,"cc":"world"}
        r=requests.get(url,params=params,timeout=10); r.raise_for_status(); data=r.json()
        out=[]
        for p in data.get("products",[]):
            n=p.get("nutriments",{}) or {}
            fields=["energy-kcal_100g","proteins_100g","carbohydrates_100g","fat_100g","sugars_100g","fiber_100g","sodium_100g","salt_100g"]
            if any(k in n for k in fields):
                out.append({
                    "source":"OFF",
                    "name": p.get(f"product_name_{lang_code}") or p.get("product_name") or p.get(f"generic_name_{lang_code}") or p.get("generic_name") or "Unnamed",
                    "brand": p.get("brands",""),
                    "kcal_100g": n.get("energy-kcal_100g"),
                    "protein_100g": n.get("proteins_100g"),
                    "carbs_100g": n.get("carbohydrates_100g"),
                    "fat_100g": n.get("fat_100g"),
                    "sugars_100g": n.get("sugars_100g"),
                    "fiber_100g": n.get("fiber_100g"),
                    "sodium_100g": n.get("sodium_100g"),
                    "salt_100g": n.get("salt_100g")
                })
        return pd.DataFrame(out)
    except Exception:
        return pd.DataFrame()

def fdc_search(q, api_key, page_size=25):
    try:
        url="https://api.nal.usda.gov/fdc/v1/foods/search"
        params={"query":q,"pageSize":page_size,"api_key":api_key}
        r=requests.get(url,params=params,timeout=10); r.raise_for_status(); data=r.json()
        out=[]
        for item in data.get("foods",[]):
            n={x["nutrientName"]:x["value"] for x in item.get("foodNutrients",[]) if "value" in x}
            out.append({
                "source":"FDC",
                "name": item.get("description","Unnamed"),
                "brand": item.get("brandOwner",""),
                "kcal_100g": n.get("Energy","") or n.get("Energy (Atwater General Factors)",""),
                "protein_100g": n.get("Protein",""),
                "carbs_100g": n.get("Carbohydrate, by difference",""),
                "fat_100g": n.get("Total lipid (fat)",""),
                "sugars_100g": n.get("Sugars, total including NLEA",""),
                "fiber_100g": n.get("Fiber, total dietary",""),
                "sodium_100g": n.get("Sodium, Na",""),
                "salt_100g": ""
            })
        return pd.DataFrame(out)
    except Exception:
        return pd.DataFrame()

def macros_from_grams(row, grams):
    factor=grams/100.0
    vals = {}
    for k in ["kcal","protein","carbs","fat","sugars","fiber","sodium","salt"]:
        v=row.get(f"{k}_100g"); vals[k]= (float(v)*factor if isinstance(v,(int,float,str)) and str(v) not in ("","None","nan") else 0.0)
    return vals

# =============== NUTRITION ===============
with tabs[2]:
    st.subheader(_("log_food"))
    picked_date = st.date_input(_("date"), value=date.today(), format="DD.MM.YYYY")
    meal_sel = st.selectbox(_("meal"), ["1st Main","2nd Main","3rd Main","1st Snack","2nd Snack","3rd Snack"] if st.session_state["lang"]=="en"
                                         else ["1. Ana Öğün","2. Ana Öğün","3. Ana Öğün","1. Ara Öğün","2. Ara Öğün","3. Ara Öğün"])

    colA, colB, colC = st.columns([3,1,1])
    with colA:
        q = st.text_input(_("search_food"))
    with colB:
        grams = st.number_input(_("amount_g"), min_value=1, max_value=2000, value=100)
    with colC:
        lang_pick = st.radio(_("result_lang"), ["en","tr"], horizontal=True, format_func=lambda x: "English" if x=="en" else "Türkçe")

    df = pd.DataFrame()
    if q:
        df_off = off_search(q, "tr" if lang_pick=="tr" else "en")
        df_fdc = fdc_search(q, st.session_state.get("fdc_key") or DEFAULT_FDC) if st.session_state.get("fdc_key") else pd.DataFrame()
        frames = [x for x in [df_fdc, df_off] if not x.empty]
        if frames: df = pd.concat(frames, ignore_index=True)

    st.caption(_("api_results"))
    show_cols = ["source","name","brand","kcal_100g","protein_100g","carbs_100g","fat_100g","sugars_100g","fiber_100g","sodium_100g","salt_100g"]
    st.dataframe(df[show_cols] if not df.empty else df, use_container_width=True)
    if df.empty and q: st.warning(_("_".join(["no","results"]))+" — "+_("search_tip"))

    if not df.empty:
        sel_idx = st.selectbox(_("select_food"), list(range(len(df))),
                               format_func=lambda i: f"{df.iloc[i]['name']} ({df.iloc[i]['brand']}) [{df.iloc[i]['source']}]")
        if st.button(_("add")):
            rowf = df.iloc[int(sel_idx)].to_dict(); vals = macros_from_grams(rowf, grams)
            conn.execute(
                """INSERT INTO food_logs(username, dt, meal, food_name, grams, kcal, protein, carbs, fat, sugars, fiber, sodium, salt)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (u, picked_date.isoformat(), meal_sel, rowf["name"], grams, vals["kcal"], vals["protein"], vals["carbs"], vals["fat"], vals["sugars"], vals["fiber"], vals["sodium"], vals["salt"])
            )
            conn.commit(); st.success("Added / Eklendi")

    weekday_lbls = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"] if st.session_state["lang"]=="en" else ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    st.subheader(f"{picked_date.strftime('%d.%m.%Y')} — {weekday_lbls[picked_date.weekday()]}")

    logs = pd.read_sql_query("""SELECT meal, food_name, grams, kcal, protein, carbs, fat 
                                FROM food_logs WHERE username=? AND dt=? ORDER BY meal""",
                             conn, params=(u, picked_date.isoformat()))
    st.dataframe(logs, use_container_width=True)

    # Targets
    is_workout = st.toggle("Today is a Workout Day" if st.session_state["lang"]=="en" else "Bugün antrenman günü", value=(picked_date.weekday() in [0,2,4]))
    prof = conn.execute("SELECT sex, height_cm, weight_kg, age, activity FROM users WHERE username=?", (u,)).fetchone()
    p_sex, p_h, p_w, p_age, p_act = prof if prof else ("male", 175, 80.0, 30, "Light")
    bmr_today = mifflin_st_jeor(p_sex, p_w, p_h, p_age)
    base_tdee = bmr_today*activity_factor(p_act) if is_workout else bmr_today*1.35
    target_cal = round(base_tdee*0.75)
    tp, tc, tf = macro_split(target_cal, workout=is_workout, weight=p_w)

    tot = logs[["kcal","protein","carbs","fat"]].sum() if not logs.empty else pd.Series({"kcal":0,"protein":0,"carbs":0,"fat":0})

    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Calories" if st.session_state["lang"]=="en" else "Kalori"], y=[min(tot["kcal"], target_cal)], name="Intake"))
    over_cal = max(0, tot["kcal"]-target_cal)
    if over_cal>0: fig.add_trace(go.Bar(x=["Calories" if st.session_state["lang"]=="en" else "Kalori"], y=[over_cal], name="Over", marker_color="red"))
    fig.add_trace(go.Bar(x=["Protein (g)"], y=[min(tot["protein"], tp)], name="Intake"))
    over_p = max(0, tot["protein"]-tp)
    if over_p>0: fig.add_trace(go.Bar(x=["Protein (g)"], y=[over_p], marker_color="red", showlegend=False))
    fig.add_trace(go.Bar(x=["Carbs (g)" if st.session_state["lang"]=="en" else "Karb (g)"], y=[min(tot["carbs"], tc)], name="Intake"))
    over_c = max(0, tot["carbs"]-tc)
    if over_c>0: fig.add_trace(go.Bar(x=["Carbs (g)" if st.session_state["lang"]=="en" else "Karb (g)"], y=[over_c], marker_color="red", showlegend=False))
    fig.update_layout(barmode="stack", yaxis=dict(range=[0, max(target_cal, tp, tc)+100]), xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    deficit_val = (target_cal - float(tot["kcal"]))
    if deficit_val>0:
        st.success(("Daily deficit: " if st.session_state["lang"]=="en" else "Günlük kalori açığı: ") + f"{int(deficit_val)} kcal → ~{round(deficit_val/7700,3)} kg fat")
    else:
        st.warning(("Exceeded by " if st.session_state["lang"]=="en" else "Hedefi aştın: ") + f"{int(-deficit_val)} kcal")

# =============== WORKOUT (editable alternatives) ===============
with tabs[3]:
    st.subheader(_("workout_plan"))
    day = st.selectbox(_("day_picker"), ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"] if st.session_state["lang"]=="en"
                        else ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"])
    # Map Turkish day back to English key
    day_map = {"Pazartesi":"Monday","Salı":"Tuesday","Çarşamba":"Wednesday","Perşembe":"Thursday","Cuma":"Friday","Cumartesi":"Saturday","Pazar":"Sunday"}
    day_key = day_map.get(day, day)

    alts = {
        "Squat":["Leg Press","Goblet Squat","Hack Squat","Glute Bridge"],
        "Bench Press":["Incline DB Press","Push-up","Machine Chest Press","Dips"],
        "Barbell Row":["Seated Row","Lat Pulldown","Dumbbell Row","Chest-supported Row"],
        "Romanian Deadlift":["Hip Thrust","Back Extension","Good Morning","Glute Bridge"],
        "Shoulder Press":["Arnold Press","Machine Shoulder Press","Push Press","Lateral Raise"],
        "Walking Lunge":["Reverse Lunge","Split Squat","Step-up","Bulgarian Split Squat"],
        "Deadlift":["Rack Pull","Trap Bar Deadlift","Sumo Deadlift","Romanian Deadlift"],
        "Lat Pulldown":["Pull-up","Seated Row","One-arm Pulldown","Chin-up"],
        "Leg Curl":["Romanian Deadlift","Glute Ham Raise","Nordic Curl","Swiss Ball Curl"]
    }
    muscles = {
        "Quads":"https://i.imgur.com/7j3m3x1.png",
        "Hamstrings/Glutes":"https://i.imgur.com/9jJH4nR.png",
        "Chest":"https://i.imgur.com/7V5vZxj.png",
        "Back":"https://i.imgur.com/2UKo1e8.png",
        "Shoulders":"https://i.imgur.com/9y2tS6I.png",
        "Core":"https://i.imgur.com/YH8cXvE.png",
        "Arms":"https://i.imgur.com/2b3Rkq4.png",
        "Calves":"https://i.imgur.com/4iL3nq8.png"
    }

    # Plan
    if plan_type=="full_body":
        schedule = {
            "Monday":[("Squat","4x8","Quads"),("Bench Press","4x8","Chest"),("Barbell Row","4x10","Back"),("Shoulder Press","3x12","Shoulders")],
            "Wednesday":[("Romanian Deadlift","3x10","Hamstrings/Glutes"),("Incline DB Press","3x12","Chest"),("Seated Row","3x12","Back"),("Walking Lunge","2x20","Quads")],
            "Friday":[("Deadlift","3x5","Back"),("Bench Press","4x6","Chest"),("Lat Pulldown","3x12","Back"),("Leg Curl","3x12","Hamstrings/Glutes")]
        }
    elif plan_type=="ppl":
        schedule = {
            "Monday":[("Bench Press","4x8","Chest"),("Shoulder Press","3x12","Shoulders"),("Lat Pulldown","3x12","Back"),("Push-up","3x15","Chest")],
            "Wednesday":[("Barbell Row","4x8","Back"),("Seated Row","3x12","Back"),("Dumbbell Row","3x12","Back"),("Face Pull","3x15","Shoulders")],
            "Friday":[("Squat","4x8","Quads"),("Leg Press","4x12","Quads"),("Leg Curl","3x12","Hamstrings/Glutes"),("Calf Raise","3x15","Calves")]
        }
    elif plan_type=="upper_lower":
        schedule = {
            "Monday":[("Bench Press","4x8","Chest"),("Barbell Row","4x8","Back"),("Shoulder Press","3x12","Shoulders"),("Lat Pulldown","3x12","Back")],
            "Tuesday":[("Squat","4x8","Quads"),("Romanian Deadlift","3x10","Hamstrings/Glutes"),("Leg Press","4x12","Quads"),("Leg Curl","3x12","Hamstrings/Glutes")],
            "Thursday":[("Incline DB Press","3x10","Chest"),("Seated Row","3x12","Back"),("Arnold Press","3x10","Shoulders"),("Push-up","3x15","Chest")],
            "Friday":[("Leg Press","4x12","Quads"),("Walking Lunge","2x20","Quads"),("Leg Curl","3x12","Hamstrings/Glutes"),("Calf Raise","3x15","Calves")]
        }
    else:
        schedule = {
            "Monday":[("Treadmill Incline","40min","Cardio"),("Plank","3x max","Core"),("Leg Raise","3x15","Core"),("Side Plank","3x30s/side","Core")],
            "Wednesday":[("Treadmill Incline","40min","Cardio"),("Plank","3x max","Core"),("Leg Raise","3x15","Core"),("Side Plank","3x30s/side","Core")],
            "Friday":[("Treadmill Incline","40min","Cardio"),("Plank","3x max","Core"),("Leg Raise","3x15","Core"),("Side Plank","3x30s/side","Core")]
        }

    todays = schedule.get(day_key, [])
    total_burn = 0
    if not todays:
        st.info("Rest / Dinlenme")
    else:
        for i,(name, sr, mg) in enumerate(todays, start=1):
            cols = st.columns([3,2,2])
            with cols[0]:
                # Editable exercise selection (default first)
                options = [name] + alts.get(name, [])
                chosen = st.selectbox(f"{i}.", options, index=0, key=f"ex_{day_key}_{i}")
                st.caption(f"Target: {sr}")
                try:
                    t_sets, t_reps = sr.lower().split("x"); t_sets=int(t_sets.strip()); t_reps=int(''.join([c for c in t_reps if c.isdigit()]))
                except: t_sets, t_reps = 3, 10
                perf_sets = st.number_input("Sets", 0, 20, t_sets, key=f"s_{day_key}_{i}")
                perf_reps = st.number_input("Reps", 0, 100, t_reps, key=f"r_{day_key}_{i}")
                cal = round(0.1 * perf_sets * perf_reps * (float(weight_kg or 70)/70.0))
                st.write(f"≈ **{cal} kcal**")
                if st.button("Save", key=f"save_{day_key}_{i}"):
                    conn.execute("""INSERT INTO workout_logs(username, dt, day, exercise, target_sets, target_reps, perf_sets, perf_reps, calories)
                                    VALUES(?,?,?,?,?,?,?,?,?)""",
                                 (u, date.today().isoformat(), day_key, chosen, t_sets, t_reps, int(perf_sets), int(perf_reps), cal))
                    conn.commit(); st.success(f"{chosen} saved (+{cal} kcal)")
                total_burn += cal
            with cols[1]:
                img = muscles.get(mg)
                if img: st.image(img, caption=mg, width=140)
            with cols[2]:
                st.markdown(f"[{_('video_guide')}]({'https://www.youtube.com/results?search_query=' + chosen.replace(' ','+')})")
        st.info(f"**Total Burn (est.): {int(total_burn)} kcal**")

# =============== PROGRESS (Weight + Waist; delete rows) ===============
with tabs[4]:
    st.subheader(_("progress_title"))
    w1, w2, w3 = st.columns([2,1,1])
    with w1:
        st.write(_("weight_entry"))
        new_w = st.number_input(_("weight_kg"), min_value=30.0, max_value=300.0, value=float(weight_kg) if weight_kg else 80.0, step=0.1, key="neww")
    with w2:
        new_waist = st.number_input(_("waist_cm"), min_value=40.0, max_value=200.0, value=float(waist_cm) if waist_cm else 90.0, step=0.1, key="newwaist")
    with w3:
        if st.button(_("add_weight")):
            conn.execute("INSERT INTO weights(username, dt, weight, waist) VALUES(?,?,?,?)", (u, date.today().isoformat(), float(new_w), float(new_waist)))
            conn.execute("UPDATE users SET weight_kg=?, waist_cm=? WHERE username=?", (float(new_w), float(new_waist), u))
            conn.commit(); st.success("Saved")

    wdf = pd.read_sql_query("SELECT rowid as id, dt, weight, waist FROM weights WHERE username=? ORDER BY dt", conn, params=(u,))
    if not wdf.empty:
        wdf["dt"] = pd.to_datetime(wdf["dt"])
        # line chart: same y-axis
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=wdf["dt"], y=wdf["weight"], mode="lines+markers", name="Weight (kg)"))
        fig.add_trace(go.Scatter(x=wdf["dt"], y=wdf["waist"], mode="lines+markers", name="Waist (cm)"))
        fig.update_layout(xaxis_title=_("timeline"), yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

        st.write("Logs")
        st.dataframe(wdf[["id","dt","weight","waist"]], use_container_width=True)
        del_id = st.number_input("Delete Row ID", min_value=0, step=1, value=0)
        if st.button("Delete"):
            if del_id>0 and del_id in wdf["id"].tolist():
                conn.execute("DELETE FROM weights WHERE rowid=? AND username=?", (int(del_id), u))
                conn.commit(); st.success("Deleted"); st.experimental_rerun()
            else:
                st.warning("Invalid ID")
    else:
        st.info("No weight data yet / Kilo kaydı yok")

# =============== REMINDERS ===============
with tabs[5]:
    st.subheader(_("reminders"))
    water_on = st.toggle(_("remind_water"))
    posture_on = st.toggle(_("remind_posture"))
    js = f"""
    <script>
    const waterOn = {str(water_on).lower()};
    const postureOn = {str(posture_on).lower()};
    function inRange(h, start, end) {{ return h>=start && h<end; }}
    function notify(msg) {{
      if (!('Notification' in window)) return;
      if (Notification.permission !== 'granted') Notification.requestPermission();
      if (Notification.permission === 'granted') new Notification('Carioca', {{ body: msg }});
      try {{ new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg').play(); }} catch(e){{}}
    }}
    function schedule() {{
      const now = new Date(); const h = now.getHours();
      if (waterOn && inRange(h,8,22)) setTimeout(()=>notify("Ceku balım su içtin mi?"), 1000);
      if (postureOn && inRange(h,8,21)) setTimeout(()=>notify("Dik dur eğilme, bu taraftar seninle"), 2000);
      if (waterOn) setInterval(()=>{{ const h=(new Date()).getHours(); if(inRange(h,8,22)) notify("Ceku balım su içtin mi?"); }}, 2*60*60*1000);
      if (postureOn) setInterval(()=>{{ const h=(new Date()).getHours(); if(inRange(h,8,21)) notify("Dik dur eğilme, bu taraftar seninle"); }}, 3*60*60*1000);
    }}
    schedule();
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)

# =============== SUMMARY (range selector) ===============
with tabs[6]:
    st.subheader(_("summary"))
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        sum_date = st.date_input(_("summary_date"), value=date.today(), format="DD.MM.YYYY", key="sum_date")
    with c2:
        range_opt = st.selectbox(_("range"),
                                 [ _("range_week"), _("range_month"), _("range_6m"), _("range_custom") ])
    with c3:
        if range_opt == _("range_custom"):
            start_date = st.date_input("Start", value=sum_date - timedelta(days=7), format="DD.MM.YYYY", key="sum_start")
            end_date = st.date_input("End", value=sum_date, format="DD.MM.YYYY", key="sum_end")
        elif range_opt == _("range_week"):
            start_date, end_date = sum_date - timedelta(days=6), sum_date
        elif range_opt == _("range_month"):
            start_date, end_date = sum_date - timedelta(days=29), sum_date
        else:  # 6m
            start_date, end_date = sum_date - timedelta(days=182), sum_date

    # Aggregate per day
    sdf = pd.DataFrame()
    if start_date and end_date:
        # build date range
        days = pd.date_range(start=start_date, end=end_date, freq="D")
        intake = pd.read_sql_query(
            "SELECT dt, SUM(kcal) as kcal, SUM(protein) as protein, SUM(carbs) as carbs FROM food_logs WHERE username=? AND dt BETWEEN ? AND ? GROUP BY dt",
            conn, params=(u, start_date.isoformat(), end_date.isoformat())
        )
        burn = pd.read_sql_query(
            "SELECT dt, SUM(calories) as kcal FROM workout_logs WHERE username=? AND dt BETWEEN ? AND ? GROUP BY dt",
            conn, params=(u, start_date.isoformat(), end_date.isoformat())
        )
        # ensure all dates
        sdf = pd.DataFrame({"dt": days.date})
        sdf = sdf.merge(intake.rename(columns={"kcal":"intake"}), how="left", left_on="dt", right_on="dt")
        sdf = sdf.merge(burn.rename(columns={"kcal":"burn"}), how="left", left_on="dt", right_on="dt")
        sdf[["intake","protein","carbs","burn"]] = sdf[["intake","protein","carbs","burn"]].fillna(0.0)

        # compute daily target based on profile (approx; workout assumed if have burn>0 or weekday M/W/F)
        def daily_target(day_obj: date) -> int:
            is_w = (burn[burn["dt"]==day_obj.isoformat()].shape[0]>0) or (pd.to_datetime(day_obj).weekday() in [0,2,4])
            base = mifflin_st_jeor(sex, weight_kg, height_cm, age) * (activity_factor(activity_label_to_key(activity_label)) if is_w else 1.35)
            return round(base*0.75)
        sdf["target"] = sdf["dt"].apply(daily_target)
        sdf["net_deficit"] = (sdf["target"] - sdf["intake"]) + sdf["burn"]
        sdf["est_fat_kg"] = sdf["net_deficit"].clip(lower=0) / 7700.0
        sdf["dt"] = pd.to_datetime(sdf["dt"])

        # Chart: bars for net_deficit + line cumulative est fat
        fig = go.Figure()
        fig.add_trace(go.Bar(x=sdf["dt"], y=sdf["net_deficit"], name="Net Deficit (kcal)"))
        fig.add_trace(go.Scatter(x=sdf["dt"], y=sdf["est_fat_kg"].cumsum(), mode="lines+markers", name="Cumulative Est. Fat (kg)"))
        fig.update_layout(xaxis_title=_("timeline"), yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    # Today snapshot
    nut = pd.read_sql_query("SELECT SUM(kcal) as kcal, SUM(protein) as protein, SUM(carbs) as carbs FROM food_logs WHERE username=? AND dt=?",
                            conn, params=(u, sum_date.isoformat()))
    eat_k = float(nut.iloc[0]["kcal"] or 0); eat_p=float(nut.iloc[0]["protein"] or 0); eat_c=float(nut.iloc[0]["carbs"] or 0)
    wrk = pd.read_sql_query("SELECT SUM(calories) as kcal FROM workout_logs WHERE username=? AND dt=?", conn, params=(u, sum_date.isoformat()))
    burn_k = float(wrk.iloc[0]["kcal"] or 0)
    is_workout = sum_date.weekday() in [0,2,4]
    base_tdee = mifflin_st_jeor(sex, weight_kg, height_cm, age) * (activity_factor(activity_label_to_key(activity_label)) if is_workout else 1.35)
    target_cal = round(base_tdee*0.75); tp, tc, tf = macro_split(target_cal, workout=is_workout, weight=weight_kg)
    net_def = (target_cal - eat_k) + burn_k; fat = round(net_def/7700,3) if net_def>0 else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Intake", f"{int(eat_k)} kcal"); c2.metric("Burned", f"{int(burn_k)} kcal"); c3.metric("Net", f"{int(net_def)} kcal"); c4.metric("Est. Fat", f"{fat} kg")
