
# app_v25.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3, bcrypt, json, requests, base64
from datetime import datetime, date

# Optional (SMTP for reset; safe-guarded)
import smtplib, ssl, secrets, string
from email.mime.text import MIMEText

# =============== CONSTANTS ===============
APP_TITLE = "Carioca"
DB_FILE = "carioca_v25.db"
DEFAULT_FDC = "6P4rVEgRsNBnS8bAYqlq2DEDqiaf72txvmATH05g"

# =============== PAGE CONFIG ===============
st.set_page_config(page_title=APP_TITLE, page_icon="🌴", layout="wide")

def css_tropical():
    return '''
    <style>
    .stApp { background: linear-gradient(135deg,#FF7E5F 0%,#FFB88C 40%,#FFD86F 70%,#FF5F6D 100%) fixed; }
    .block-container { backdrop-filter: blur(6px); background-color: rgba(255,255,255,0.88); border-radius: 24px; padding: 2rem 2.2rem; }
    .metric-card { border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.75); border: 1px solid rgba(255,255,255,0.6); }
    .pill { padding: 4px 10px; border-radius: 999px; background: rgba(0,0,0,0.06); font-size: 12px; font-weight: 600; }
    img.muscle { max-width: 140px; border-radius: 12px; border: 1px solid #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.15); }
    .header-avatar { text-align: right; }
    </style>
    '''

def css_minimal():
    return '''
    <style>
    .stApp { background: #f5f7fb; }
    .block-container { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 2rem 2.2rem; }
    .metric-card { border-radius: 12px; padding: 14px; background: #fff; border: 1px solid #e5e7eb; }
    .pill { padding: 3px 8px; border-radius: 12px; background: #eef2ff; font-size: 12px; font-weight: 600; }
    img.muscle { max-width: 140px; border-radius: 12px; border: 1px solid #e5e7eb; }
    .header-avatar { text-align: right; }
    </style>
    '''

# Language files are optional
@st.cache_data
def load_lang():
    try:
        with open("lang_en.json", "r", encoding="utf-8") as f:
            en = json.load(f)
    except Exception:
        en = {}
    try:
        with open("lang_tr.json", "r", encoding="utf-8") as f:
            tr = json.load(f)
    except Exception:
        tr = {}
    return {"en": en, "tr": tr}
L = load_lang()
def T(key):
    lang = st.session_state.get("lang", "en")
    return L.get(lang, {}).get(key, key)

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
            email    TEXT,
            fdc_key  TEXT,
            plan_type TEXT,
            meal_structure TEXT,
            age INT, sex TEXT, height_cm REAL, weight_kg REAL, bodyfat REAL,
            birthdate TEXT,
            activity TEXT, target_weight REAL, training_days INT, fasting TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weights(
            username TEXT, dt TEXT, weight REAL
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
    st.markdown(css_tropical(), unsafe_allow_html=True)
    st.sidebar.header("Carioca 🌴")
    lang_pick = st.sidebar.radio("Language", ["en", "tr"],
                                 format_func=lambda x: "English" if x == "en" else "Türkçe",
                                 key="lang")

    left, right = st.columns(2)

    # ---- Login (Enter enabled) ----
    with left:
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pw")
            remember = st.checkbox("Remember Me", value=True, key="remember_me")
            submitted = st.form_submit_button("Login")
        st.markdown("""            <script>
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
                st.error("Invalid credentials")

        st.divider()
        st.subheader("Password Reset")
        email = st.text_input("E-mail")
        if st.button("Send Reset E-mail"):
            if email:
                send_reset_email(email, st.session_state.get("login_user", "user"))
            else:
                st.warning("Please provide an e-mail.")

    # ---- Register ----
    with right:
        st.subheader("Register")
        ru = st.text_input("Username *", key="ru")
        rp = st.text_input("Password *", type="password", key="rp")
        if st.button("Create Account"):
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

if "user" not in st.session_state:
    login_register_ui()
    st.stop()

# =============== LOAD USER ===============
row = conn.execute("""    SELECT username, lang, theme, avatar, email, fdc_key, plan_type, meal_structure,
           age, sex, height_cm, weight_kg, bodyfat, birthdate, activity, target_weight, training_days, fasting
    FROM users WHERE username=?
""", (st.session_state["user"],)).fetchone()

if not row:
    st.warning("User not found. Please login again.")
    for k in ["user", "lang", "theme", "fdc_key"]:
        st.session_state.pop(k, None)
    st.rerun()

(u, lang, theme, avatar, email, fdc_key, plan_type, meal_structure,
 age, sex, height_cm, weight_kg, bodyfat, birthdate, activity,
 target_weight, training_days, fasting) = row

st.session_state.setdefault("lang", lang or "en")
st.session_state.setdefault("theme", theme or "tropical")
st.session_state.setdefault("fdc_key", fdc_key or DEFAULT_FDC)

# =============== THEME TOGGLE ===============
picked_theme = st.sidebar.radio(
    "Theme",
    ["tropical", "minimal"],
    index=0 if (st.session_state["theme"] == "tropical") else 1,
    format_func=lambda x: "🌴 Tropical" if x == "tropical" else "⚪ Minimal",
)
st.session_state["theme"] = picked_theme
st.markdown(css_tropical() if picked_theme == "tropical" else css_minimal(), unsafe_allow_html=True)

# Header with avatar RIGHT
hc1, hc2 = st.columns([8, 1])
with hc1:
    st.title(APP_TITLE)
    st.caption("Personalized plan engine • Theme toggle • OFF + FDC search • v25")
with hc2:
    if avatar:
        st.markdown('<div class="header-avatar">', unsafe_allow_html=True)
        st.image(avatar, width=72)
        st.markdown('</div>', unsafe_allow_html=True)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
st.sidebar.radio("Language", ["en", "tr"], key="lang",
                 format_func=lambda x: "English" if x == "en" else "Türkçe")

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
    return {"sedentary": 1.2, "light": 1.35, "moderate": 1.55, "high": 1.75, "very_high": 1.95}.get(level or "light", 1.35)

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
    "two_plus_one": "2 Main + 1 Snack",
    "three_meals": "3 Meals",
    "four_meals": "4 Meals",
}

# =============== TABS ===============
tabs = st.tabs(["Profile", "Deficit Calculator", "Nutrition", "Workout", "Progress", "Reminders", "Summary"])

# =============== PROFILE ===============
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    with c1:
        min_bd, max_bd = date(1950, 1, 1), date(2035, 12, 31)
        bd_val = pd.to_datetime(birthdate).date() if birthdate else None
        bd_input = st.date_input("Birthdate", value=bd_val, min_value=min_bd, max_value=max_bd)
        if bd_input:
            today = date.today()
            age_calc = today.year - bd_input.year - ((today.month, today.day) < (bd_input.month, bd_input.day))
            age = age_calc

        age = st.number_input("Age", min_value=10, max_value=100, value=int(age) if age else 30)
        sex = st.selectbox("Sex", ["male", "female"], index=0 if (sex or "male") == "male" else 1)
        height_cm = st.number_input("Height (cm)", min_value=120, max_value=230, value=int(height_cm) if height_cm else 175)

        st.write("—")
        st.subheader("Change Username")
        newu = st.text_input("New Username", value=u)
        if st.button("Apply Username"):
            if newu and newu != u:
                try:
                    conn.execute("UPDATE users SET username=? WHERE username= ?", (newu, u))
                    conn.execute("UPDATE weights SET username=? WHERE username= ?", (newu, u))
                    conn.execute("UPDATE food_logs SET username=? WHERE username= ?", (newu, u))
                    conn.execute("UPDATE workout_logs SET username=? WHERE username= ?", (newu, u))
                    conn.commit()
                    st.session_state["user"] = newu
                    st.success("Username updated. Please re-login.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

    with c2:
        weight_kg = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=float(weight_kg) if weight_kg else 80.0, step=0.1)
        bodyfat_val = float(bodyfat) if bodyfat not in (None, "") else 0.0
        bodyfat_in = st.number_input("Body Fat (%)", min_value=0.0, max_value=60.0, value=bodyfat_val, step=0.1)
        bodyfat = bodyfat_in if bodyfat_in > 0 else None
        target_weight = st.number_input("Target Weight (kg)", min_value=30.0, max_value=250.0, value=float(target_weight) if target_weight else 80.0, step=0.1)

        st.subheader("Avatar")
        photo = st.file_uploader("Upload Photo", type=["png", "jpg", "jpeg"])
        if photo:
            b64 = base64.b64encode(photo.read()).decode("utf-8")
            avatar = f"data:image/{photo.type.split('/')[-1]};base64,{b64}"

    with c3:
        activity = st.selectbox("Activity Level", ["sedentary", "light", "moderate", "high", "very_high"],
                                index=["sedentary", "light", "moderate", "high", "very_high"].index(activity or "light"))
        training_days = st.slider("Training Days / Week", 1, 7, int(training_days) if training_days else 5)
        fasting = st.selectbox("Fasting", ["16:8 Intermittent Fasting"])
        plan_type = st.selectbox("Training Plan", list(PLAN_LABELS.keys()),
                                 index=list(PLAN_LABELS.keys()).index(plan_type or "full_body"),
                                 format_func=lambda k: PLAN_LABELS[k])
        meal_structure = st.selectbox("Meal Structure", list(MEAL_LABELS.keys()),
                                      index=list(MEAL_LABELS.keys()).index(meal_structure or "two_plus_one"),
                                      format_func=lambda k: MEAL_LABELS[k])
        email = st.text_input("E-mail", value=email or "")
        fdc_key = st.text_input("USDA FDC API Key (optional)",
                                value=st.session_state.get("fdc_key") or DEFAULT_FDC,
                                help="If provided, FDC results are included.")

    if st.button("Save Profile", type="primary"):
        conn.execute(
            """            UPDATE users SET
                lang=?, theme=?, avatar=?, email=?, fdc_key=?, plan_type=?, meal_structure=?,
                age=?, sex=?, height_cm=?, weight_kg=?, bodyfat=?, birthdate=?, activity=?,
                target_weight=?, training_days=?, fasting=?
            WHERE username=?
            """,
            (
                st.session_state["lang"], st.session_state["theme"], avatar, email, fdc_key, plan_type, meal_structure,
                age, sex, height_cm, weight_kg, bodyfat, (bd_input.isoformat() if bd_input else None), activity,
                target_weight, training_days, fasting, u,
            ),
        )
        conn.commit()
        st.session_state["fdc_key"] = fdc_key
        st.success("Profile updated")

    # Metrics
    bmr = mifflin_st_jeor(sex, weight_kg, height_cm, age)
    tdee = bmr * activity_factor(activity)
    wcal = round(tdee * 0.75)
    rcal = round((bmr * 1.35) * 0.75)
    pc_w, cc_w, fc_w = macro_split(wcal, workout=True, weight=weight_kg)
    pc_r, cc_r, fc_r = macro_split(rcal, workout=False, weight=weight_kg)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("BMR", f"{int(bmr)} kcal")
    k2.metric("TDEE", f"{int(tdee)} kcal")
    k3.metric("Workout Day Target", f"{wcal} kcal")
    k4.metric("Rest Day Target", f"{rcal} kcal")
    st.write("Macros:")
    st.write(f"🏋️ Workout: P {pc_w}g / C {cc_w}g / F {fc_w}g")
    st.write(f"🛌 Rest: P {pc_r}g / C {cc_r}g / F {fc_r}g")

# =============== DEFICIT CALCULATOR ===============
with tabs[1]:
    day_type = st.selectbox("Day Type", ["Workout Day", "Rest Day"])
    deficit = st.slider("Deficit (%)", 5, 35, 25, step=1)
    base_tdee = bmr * activity_factor(activity) if day_type == "Workout Day" else bmr * 1.35
    target_cal = round(base_tdee * (1 - deficit / 100))
    weekly_loss = round(((base_tdee - target_cal) * 7) / 7700, 2)
    weight_3m = round((weight_kg or 80) - weekly_loss * 12, 1)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TDEE", int(base_tdee))
    c2.metric("Target Calories", int(target_cal))
    c3.metric("Weekly Loss", f"{weekly_loss} kg")
    c4.metric("Weight (3 Months)", f"{weight_3m} kg")

# =============== FOOD SEARCH HELPERS ===============
def off_search(q, lang_code="en", page_size=25):
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {"search_terms": q, "search_simple": 1, "action": "process", "json": 1, "page_size": page_size, "cc": "world"}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        out = []
        for p in data.get("products", []):
            n = p.get("nutriments", {}) or {}
            fields = ["energy-kcal_100g", "proteins_100g", "carbohydrates_100g", "fat_100g",
                      "sugars_100g", "fiber_100g", "sodium_100g", "salt_100g"]
            if any(k in n for k in fields):
                out.append({
                    "source": "OFF",
                    "name": p.get(f"product_name_{lang_code}") or p.get("product_name") or
                            p.get(f"generic_name_{lang_code}") or p.get("generic_name") or "Unnamed",
                    "brand": p.get("brands", ""),
                    "kcal_100g": n.get("energy-kcal_100g"),
                    "protein_100g": n.get("proteins_100g"),
                    "carbs_100g": n.get("carbohydrates_100g"),
                    "fat_100g": n.get("fat_100g"),
                    "sugars_100g": n.get("sugars_100g"),
                    "fiber_100g": n.get("fiber_100g"),
                    "sodium_100g": n.get("sodium_100g"),
                    "salt_100g": n.get("salt_100g"),
                })
        return pd.DataFrame(out)
    except Exception:
        return pd.DataFrame()

def fdc_search(q, api_key, page_size=25):
    try:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {"query": q, "pageSize": page_size, "api_key": api_key}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        out = []
        for item in data.get("foods", []):
            n = {x["nutrientName"]: x["value"] for x in item.get("foodNutrients", []) if "value" in x}
            out.append({
                "source": "FDC",
                "name": item.get("description", "Unnamed"),
                "brand": item.get("brandOwner", ""),
                "kcal_100g": n.get("Energy", "") or n.get("Energy (Atwater General Factors)", ""),
                "protein_100g": n.get("Protein", ""),
                "carbs_100g": n.get("Carbohydrate, by difference", ""),
                "fat_100g": n.get("Total lipid (fat)", ""),
                "sugars_100g": n.get("Sugars, total including NLEA", ""),
                "fiber_100g": n.get("Fiber, total dietary", ""),
                "sodium_100g": n.get("Sodium, Na", ""),
                "salt_100g": "",
            })
        return pd.DataFrame(out)
    except Exception:
        return pd.DataFrame()

def macros_from_grams(row, grams):
    factor = grams / 100.0
    vals = {}
    for k in ["kcal", "protein", "carbs", "fat", "sugars", "fiber", "sodium", "salt"]:
        v = row.get(f"{k}_100g")
        vals[k] = (float(v) * factor if isinstance(v, (int, float, str)) and str(v) not in ("", "None", "nan") else 0.0)
    return vals

# =============== NUTRITION ===============
with tabs[2]:
    st.subheader("Log Food")
    picked_date = st.date_input("Date", value=date.today(), format="DD.MM.YYYY")
    meal_sel = st.selectbox("Meal", ["1st Main", "2nd Main", "3rd Main", "1st Snack", "2nd Snack", "3rd Snack"])

    colA, colB, colC = st.columns([3, 1, 1])
    with colA:
        q = st.text_input("Search Food")
    with colB:
        grams = st.number_input("Amount (g)", min_value=1, max_value=2000, value=100)
    with colC:
        lang_pick = st.radio("Result Language", ["en", "tr"], horizontal=True,
                             format_func=lambda x: "English" if x == "en" else "Türkçe")

    df = pd.DataFrame()
    if q:
        df_off = off_search(q, "tr" if lang_pick == "tr" else "en")
        df_fdc = fdc_search(q, st.session_state.get("fdc_key") or DEFAULT_FDC) if st.session_state.get("fdc_key") else pd.DataFrame()
        frames = [x for x in [df_fdc, df_off] if not x.empty]
        if frames:
            df = pd.concat(frames, ignore_index=True)

    st.caption("API Results")
    show_cols = ["source", "name", "brand", "kcal_100g", "protein_100g", "carbs_100g", "fat_100g",
                 "sugars_100g", "fiber_100g", "sodium_100g", "salt_100g"]
    st.dataframe(df[show_cols] if not df.empty else df, use_container_width=True)
    if df.empty and q:
        st.warning("No results — try both English and Turkish terms.")

    if not df.empty:
        sel_idx = st.selectbox("Select Item",
                               list(range(len(df))),
                               format_func=lambda i: f"{df.iloc[i]['name']} ({df.iloc[i]['brand']}) [{df.iloc[i]['source']}]" )
        if st.button("Add to Day"):
            rowf = df.iloc[int(sel_idx)].to_dict()
            vals = macros_from_grams(rowf, grams)
            conn.execute(
                """INSERT INTO food_logs(username, dt, meal, food_name, grams, kcal, protein, carbs, fat, sugars, fiber, sodium, salt)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (st.session_state["user"], picked_date.isoformat(), meal_sel, rowf["name"], grams,
                 vals["kcal"], vals["protein"], vals["carbs"], vals["fat"], vals["sugars"], vals["fiber"], vals["sodium"], vals["salt"]),
            )
            conn.commit()
            st.success("Added")

    weekday_en = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][picked_date.weekday()]
    st.subheader(f"{picked_date.strftime('%d.%m.%Y')} — {weekday_en}")

    logs = pd.read_sql_query(
        """SELECT meal, food_name, grams, kcal, protein, carbs, fat
           FROM food_logs WHERE username=? AND dt=? ORDER BY meal""", conn,
        params=(st.session_state["user"], picked_date.isoformat())
    )
    st.dataframe(logs, use_container_width=True)

    # Targets (from profile)
    is_workout = st.toggle("Today is a Workout Day", value=(picked_date.weekday() in [0, 2, 4]))
    prof = conn.execute("SELECT sex, height_cm, weight_kg, age, activity FROM users WHERE username=?",
                        (st.session_state["user"],)).fetchone()
    p_sex, p_h, p_w, p_age, p_act = prof if prof else ("male", 175, 80.0, 30, "light")
    bmr_today = mifflin_st_jeor(p_sex, p_w, p_h, p_age)
    base_tdee = bmr_today * activity_factor(p_act) if is_workout else bmr_today * 1.35
    target_cal = round(base_tdee * 0.75)
    tp, tc, tf = macro_split(target_cal, workout=is_workout, weight=p_w)

    tot = logs[["kcal", "protein", "carbs", "fat"]].sum() if not logs.empty else pd.Series({"kcal": 0, "protein": 0, "carbs": 0, "fat": 0})

    # Stacked vertical bars
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Calories"], y=[min(tot["kcal"], target_cal)], name="Intake"))
    over_cal = max(0, tot["kcal"] - target_cal)
    if over_cal > 0:
        fig.add_trace(go.Bar(x=["Calories"], y=[over_cal], name="Over", marker_color="red"))
    fig.add_trace(go.Bar(x=["Protein (g)"], y=[min(tot["protein"], tp)], name="Intake"))
    over_p = max(0, tot["protein"] - tp)
    if over_p > 0:
        fig.add_trace(go.Bar(x=["Protein (g)"], y=[over_p], marker_color="red", showlegend=False))
    fig.add_trace(go.Bar(x=["Carbs (g)"], y=[min(tot["carbs"], tc)], name="Intake"))
    over_c = max(0, tot["carbs"] - tc)
    if over_c > 0:
        fig.add_trace(go.Bar(x=["Carbs (g)"], y=[over_c], marker_color="red", showlegend=False))
    fig.update_layout(barmode="stack", yaxis=dict(range=[0, max(target_cal, tp, tc) + 100]))
    st.plotly_chart(fig, use_container_width=True)

    deficit = (target_cal - float(tot["kcal"]))
    if deficit > 0:
        st.success(f"Daily deficit: {int(deficit)} kcal → ~{round(deficit/7700, 3)} kg fat")
    else:
        st.warning(f"Exceeded by {int(-deficit)} kcal")

# =============== WORKOUT ===============
with tabs[3]:
    st.subheader("Workout Plan")
    day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])

    alts = {
        "Squat": ["Leg Press", "Goblet Squat", "Hack Squat"],
        "Bench Press": ["Incline DB Press", "Push-up", "Machine Chest Press"],
        "Barbell Row": ["Seated Row", "Lat Pulldown", "Dumbbell Row"],
        "Romanian Deadlift": ["Hip Thrust", "Back Extension", "Good Morning"],
        "Shoulder Press": ["Arnold Press", "Machine Shoulder Press", "Push Press"],
        "Walking Lunge": ["Reverse Lunge", "Split Squat", "Step-up"],
        "Deadlift": ["Rack Pull", "Trap Bar Deadlift", "Sumo Deadlift"],
        "Lat Pulldown": ["Pull-up", "Seated Row", "One-arm Pulldown"],
        "Leg Curl": ["Romanian Deadlift", "Glute Ham Raise", "Nordic Curl"],
    }
    muscles = {
        "Quads": "https://i.imgur.com/7j3m3x1.png",
        "Hamstrings/Glutes": "https://i.imgur.com/9jJH4nR.png",
        "Chest": "https://i.imgur.com/7V5vZxj.png",
        "Back": "https://i.imgur.com/2UKo1e8.png",
        "Shoulders": "https://i.imgur.com/9y2tS6I.png",
        "Core": "https://i.imgur.com/YH8cXvE.png",
        "Arms": "https://i.imgur.com/2b3Rkq4.png",
        "Calves": "https://i.imgur.com/4iL3nq8.png",
    }

    if plan_type == "full_body":
        schedule = {
            "Monday":    [("Squat", "4x8", "Quads"), ("Bench Press", "4x8", "Chest"),
                          ("Barbell Row", "4x10", "Back"), ("Shoulder Press", "3x12", "Shoulders")],
            "Wednesday": [("Romanian Deadlift", "3x10", "Hamstrings/Glutes"), ("Incline DB Press", "3x12", "Chest"),
                          ("Seated Row", "3x12", "Back"), ("Walking Lunge", "2x20", "Quads")],
            "Friday":    [("Deadlift", "3x5", "Back"), ("Bench Press", "4x6", "Chest"),
                          ("Lat Pulldown", "3x12", "Back"), ("Leg Curl", "3x12", "Hamstrings/Glutes")],
        }
    elif plan_type == "ppl":
        schedule = {
            "Monday":    [("Bench Press", "4x8", "Chest"), ("Shoulder Press", "3x12", "Shoulders"),
                          ("Lat Pulldown", "3x12", "Back"), ("Push-up", "3x15", "Chest")],
            "Wednesday": [("Barbell Row", "4x8", "Back"), ("Seated Row", "3x12", "Back"),
                          ("Dumbbell Row", "3x12", "Back"), ("Face Pull", "3x15", "Shoulders")],
            "Friday":    [("Squat", "4x8", "Quads"), ("Leg Press", "4x12", "Quads"),
                          ("Leg Curl", "3x12", "Hamstrings/Glutes"), ("Calf Raise", "3x15", "Calves")],
        }
    elif plan_type == "upper_lower":
        schedule = {
            "Monday":    [("Bench Press", "4x8", "Chest"), ("Barbell Row", "4x8", "Back"),
                          ("Shoulder Press", "3x12", "Shoulders"), ("Lat Pulldown", "3x12", "Back")],
            "Tuesday":   [("Squat", "4x8", "Quads"), ("Romanian Deadlift", "3x10", "Hamstrings/Glutes"),
                          ("Leg Press", "4x12", "Quads"), ("Leg Curl", "3x12", "Hamstrings/Glutes")],
            "Thursday":  [("Incline DB Press", "3x10", "Chest"), ("Seated Row", "3x12", "Back"),
                          ("Arnold Press", "3x10", "Shoulders"), ("Push-up", "3x15", "Chest")],
            "Friday":    [("Leg Press", "4x12", "Quads"), ("Walking Lunge", "2x20", "Quads"),
                          ("Leg Curl", "3x12", "Hamstrings/Glutes"), ("Calf Raise", "3x15", "Calves")],
        }
    else:
        schedule = {
            "Monday":    [("Treadmill Incline", "40min", "Cardio"), ("Plank", "3x max", "Core"),
                          ("Leg Raise", "3x15", "Core"), ("Side Plank", "3x30s/side", "Core")],
            "Wednesday": [("Treadmill Incline", "40min", "Cardio"), ("Plank", "3x max", "Core"),
                          ("Leg Raise", "3x15", "Core"), ("Side Plank", "3x30s/side", "Core")],
            "Friday":    [("Treadmill Incline", "40min", "Cardio"), ("Plank", "3x max", "Core"),
                          ("Leg Raise", "3x15", "Core"), ("Side Plank", "3x30s/side", "Core")],
        }

    todays = schedule.get(day, [])
    total_burn = 0
    if not todays:
        st.info("Rest Day")
    else:
        for i, (name, sr, mg) in enumerate(todays, start=1):
            cols = st.columns([3, 2, 2])
            with cols[0]:
                st.markdown(f"**{i}. {name}** — Target: {sr}")
                try:
                    t_sets, t_reps = sr.lower().split("x")
                    t_sets = int(t_sets.strip())
                    t_reps = int(''.join([c for c in t_reps if c.isdigit()]))
                except Exception:
                    t_sets, t_reps = 3, 10
                perf_sets = st.number_input("Sets", 0, 20, t_sets, key=f"s_{i}")
                perf_reps = st.number_input("Reps", 0, 100, t_reps, key=f"r_{i}")
                cal = round(0.1 * perf_sets * perf_reps * (float(weight_kg or 70) / 70.0))
                st.write(f"≈ **{cal} kcal**")
                if st.button("Save", key=f"save_{i}"):
                    conn.execute(
                        """INSERT INTO workout_logs(username, dt, day, exercise, target_sets, target_reps, perf_sets, perf_reps, calories)
                           VALUES(?,?,?,?,?,?,?,?,?)""", (st.session_state["user"], date.today().isoformat(), day, name, t_sets, t_reps, int(perf_sets), int(perf_reps), cal),
                    )
                    conn.commit()
                    st.success(f"{name} saved (+{cal} kcal)")
                total_burn += cal
            with cols[1]:
                img = muscles.get(mg)
                if img:
                    st.image(img, caption=mg, width=140)
            with cols[2]:
                st.markdown(f"[Video Guide]({'https://www.youtube.com/results?search_query=' + name.replace(' ', '+')})")
        st.info(f"**Total Burn (est.): {int(total_burn)} kcal**")

# =============== PROGRESS ===============
with tabs[4]:
    st.subheader("Progress")
    w1, w2 = st.columns([2, 1])
    with w1:
        st.write("Enter Your Weight")
        new_w = st.number_input("Weight (kg)", min_value=30.0, max_value=300.0,
                                value=float(weight_kg) if weight_kg else 80.0, step=0.1, key="neww")
    with w2:
        if st.button("Add Weight"):
            conn.execute("INSERT INTO weights(username, dt, weight) VALUES(?,?,?)",
                         (st.session_state["user"], date.today().isoformat(), float(new_w)))
            conn.execute("UPDATE users SET weight_kg=? WHERE username=?",
                         (float(new_w), st.session_state["user"]))
            conn.commit()
            st.success("Saved")
    wdf = pd.read_sql_query("SELECT dt, weight FROM weights WHERE username=?",
                            conn, params=(st.session_state["user"],))
    if not wdf.empty:
        wdf["dt"] = pd.to_datetime(wdf["dt"])
        fig = px.line(wdf, x="dt", y="weight", markers=True, title="Weight Trend")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No weight data yet")

# =============== REMINDERS ===============
with tabs[5]:
    st.subheader("Reminders")
    water_on = st.toggle("Water Reminder")
    posture_on = st.toggle("Posture Reminder")
    js = f"""    <script>
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

# =============== SUMMARY ===============
with tabs[6]:
    picked_date = st.date_input("Summary Date", value=date.today(), format="DD.MM.YYYY", key="sum_date")
    st.header(f"Summary — {picked_date.strftime('%d.%m.%Y')}")
    nut = pd.read_sql_query(
        "SELECT SUM(kcal) as kcal, SUM(protein) as protein, SUM(carbs) as carbs FROM food_logs WHERE username=? AND dt=?",
        conn, params=(st.session_state["user"], picked_date.isoformat()),
    )
    eat_k = float(nut.iloc[0]["kcal"] or 0)
    eat_p = float(nut.iloc[0]["protein"] or 0)
    eat_c = float(nut.iloc[0]["carbs"] or 0)
    wrk = pd.read_sql_query(
        "SELECT SUM(calories) as kcal FROM workout_logs WHERE username=? AND dt=?",
        conn, params=(st.session_state["user"], picked_date.isoformat()),
    )
    burn = float(wrk.iloc[0]["kcal"] or 0)

    prof = conn.execute("SELECT sex, height_cm, weight_kg, age, activity FROM users WHERE username=?",
                        (st.session_state["user"],)).fetchone()
    p_sex, p_h, p_w, p_age, p_act = prof if prof else ("male", 175, 80.0, 30, "light")
    bmr_today = mifflin_st_jeor(p_sex, p_w, p_h, p_age)
    is_workout = picked_date.weekday() in [0, 2, 4]
    base_tdee = bmr_today * activity_factor(p_act) if is_workout else bmr_today * 1.35
    target_cal = round(base_tdee * 0.75)
    tp, tc, tf = macro_split(target_cal, workout=is_workout, weight=p_w)

    net_def = (target_cal - eat_k) + burn
    fat = round(net_def / 7700, 3) if net_def > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Intake", f"{int(eat_k)} kcal")
    c2.metric("Burned", f"{int(burn)} kcal")
    c3.metric("Net Deficit", f"{int(net_def)} kcal")
    c4.metric("Est. Fat Loss", f"{fat} kg")

    tot = pd.Series({"kcal": eat_k, "protein": eat_p, "carbs": eat_c})
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Calories"], y=[min(tot["kcal"], target_cal)]))
    over_cal = max(0, tot["kcal"] - target_cal)
    if over_cal > 0:
        fig.add_trace(go.Bar(x=["Calories"], y=[over_cal], marker_color="red"))
    fig.add_trace(go.Bar(x=["Protein (g)"], y=[min(tot["protein"], tp)]))
    over_p = max(0, tot["protein"] - tp)
    if over_p > 0:
        fig.add_trace(go.Bar(x=["Protein (g)"], y=[over_p], marker_color="red", showlegend=False))
    fig.add_trace(go.Bar(x=["Carbs (g)"], y=[min(tot["carbs"], tc)]))
    over_c = max(0, tot["carbs"] - tc)
    if over_c > 0:
        fig.add_trace(go.Bar(x=["Carbs (g)"], y=[over_c], marker_color="red", showlegend=False))
    fig.update_layout(barmode="stack", yaxis=dict(range=[0, max(target_cal, tp, tc) + 100]))
    st.plotly_chart(fig, use_container_width=True)
