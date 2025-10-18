
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3, bcrypt, json, requests, base64
from datetime import datetime, timedelta, date

# email
import smtplib, ssl, secrets, string
from email.mime.text import MIMEText

DEFAULT_FDC = "6P4rVEgRsNBnS8bAYqlq2DEDqiaf72txvmATH05g"

# ---- Page head / theme ----
st.set_page_config(page_title="Carioca", page_icon="🌴", layout="wide")
BG_URL = "https://images.unsplash.com/photo-1544986581-efac024faf62?q=80&w=1400&auto=format&fit=crop"
BG_CSS = f"""
<style>
.stApp {{
  background: url('{BG_URL}') no-repeat center center fixed;
  background-size: cover;
}}
.block-container {{ backdrop-filter: blur(6px); background-color: rgba(255,255,255,0.88); border-radius: 24px; padding: 2rem 2.2rem; }}
</style>
"""
st.markdown(BG_CSS, unsafe_allow_html=True)

def css_tropical():
    return """
    <style>
    .stApp { background-image: none !important; background: linear-gradient(135deg,#FF7E5F 0%,#FFB88C 40%,#FFD86F 70%,#FF5F6D 100%) fixed; }
    .block-container { backdrop-filter: blur(6px); background-color: rgba(255,255,255,0.88); border-radius: 24px; padding: 2rem 2.2rem; }
    .metric-card { border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.75); border: 1px solid rgba(255,255,255,0.6); }
    .pill { padding: 4px 10px; border-radius: 999px; background: rgba(0,0,0,0.06); font-size: 12px; font-weight: 600; }
    img.muscle { max-width: 140px; border-radius: 12px; border: 1px solid #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.15); }
    </style>
    """

def css_minimal():
    return """
    <style>
    .stApp { background-image: none !important; background: #f5f7fb; }
    .block-container { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 2rem 2.2rem; }
    .metric-card { border-radius: 12px; padding: 14px; background: #fff; border: 1px solid #e5e7eb; }
    .pill { padding: 3px 8px; border-radius: 12px; background: #eef2ff; font-size: 12px; font-weight: 600; }
    img.muscle { max-width: 140px; border-radius: 12px; border: 1px solid #e5e7eb; }
    </style>
    """

@st.cache_data
def load_lang():
    with open("lang_en.json","r", encoding="utf-8") as f:
        en = json.load(f)
    with open("lang_tr.json","r", encoding="utf-8") as f:
        tr = json.load(f)
    return {"en": en, "tr": tr}
L = load_lang()
def T(key): lang = st.session_state.get("lang","en"); return L[lang].get(key,key)

# ---- DB ----
def get_conn():
    conn = sqlite3.connect("carioca_v22.db", check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        pw_hash BLOB NOT NULL,
        lang TEXT DEFAULT 'en',
        theme TEXT DEFAULT 'tropical',
        avatar TEXT,
        email TEXT,
        fdc_key TEXT,
        plan_type TEXT,
        meal_structure TEXT,
        age INT, sex TEXT, height_cm REAL, weight_kg REAL, bodyfat REAL,
        birthdate TEXT,
        activity TEXT, target_weight REAL, training_days INT, fasting TEXT,
        created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS weights(
        username TEXT, dt TEXT, weight REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS food_logs(
        username TEXT, dt TEXT, meal TEXT, food_name TEXT, grams REAL,
        kcal REAL, protein REAL, carbs REAL, fat REAL, sugars REAL, fiber REAL, sodium REAL, salt REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS workout_logs(
        username TEXT, dt TEXT, day TEXT, exercise TEXT, target_sets INT, target_reps INT,
        perf_sets INT, perf_reps INT, calories REAL
    )""")
    conn.commit()
    return conn
conn = get_conn()

def hash_pw(pw:str)->bytes: return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())
def check_pw(pw:str, h:bytes)->bool:
    try: return bcrypt.checkpw(pw.encode(), h)
    except Exception: return False

# ---- Email reset ----
def send_reset_email(to_email: str, username: str):
    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    body = f"Merhaba {username},\\n\\nCarioca şifre sıfırlama kodun: {token}\\n\\nBu kodu uygulamadaki şifre sıfırlama alanına gir."
    msg = MIMEText(body); msg["Subject"] = "Carioca Şifre Sıfırlama"
    msg["From"] = st.secrets["smtp"]["from"]; msg["To"] = to_email
    context = ssl.create_default_context()
    with smtplib.SMTP(st.secrets["smtp"]["host"], st.secrets["smtp"]["port"]) as server:
        server.starttls(context=context)
        server.login(st.secrets["smtp"]["user"], st.secrets["smtp"]["password"])
        server.sendmail(msg["From"], [to_email], msg.as_string())
    st.success("Reset e-mail gönderildi. Gelen kutunu kontrol et.")

# ---- Login/Register ----
def login_register_ui():
    st.markdown(css_tropical(), unsafe_allow_html=True)  # tropical login
    st.sidebar.header("Carioca 🌴")
    lang = st.sidebar.radio(T("language"), ["en", "tr"], format_func=lambda x: "English" if x=="en" else "Türkçe", key="lang")
    # Login form (Enter submits)
    c1,c2 = st.columns(2)
    with c1:
        st.subheader(T("login"))
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input(T("username"), key="login_user")
            p = st.text_input(T("password"), type="password", key="login_pw")
            remember = st.checkbox(T("remember_me"), value=True)
            submitted = st.form_submit_button(T("login"))
        if submitted:
            row = conn.execute("SELECT pw_hash, lang FROM users WHERE username=?", (u,)).fetchone()
            if row and check_pw(p, row[0]):
                try:
                  st.session_state["lang"] = row[1] or lang
                except st.errors.StreamlitAPIException:
                  st.session_state.update({"lang": row[1] or lang})
                st.session_state["user"] = u
                st.session_state["remember"] = remember
                st.rerun()
            else:
                st.error("Invalid credentials / Geçersiz bilgiler")
        st.divider()
        st.subheader(T("password_reset"))
        email = st.text_input(T("email"))
        if st.button(T("send_reset")):
            if email:
                send_reset_email(email, st.session_state.get("login_user","user"))
            else:
                st.warning("Lütfen profilinden e-posta ekle veya buraya yaz.")
    with c2:
        st.subheader(T("register"))
        ru = st.text_input(T("username")+" *", key="ru")
        rp = st.text_input(T("password")+" *", type="password", key="rp")
        if st.button(T("register")):
            if not ru or not rp:
                st.warning("Fill required fields")
            else:
                try:
                    conn.execute("""INSERT INTO users(username, pw_hash, lang, theme, fdc_key, created_at)
                                    VALUES(?,?,?,?,?,?)""",
                                 (ru, hash_pw(rp), lang, "tropical", DEFAULT_FDC, datetime.utcnow().isoformat()))
                    conn.commit()
                    st.success("Registered. Please log in.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

if "user" not in st.session_state:
    login_register_ui()
    st.stop()

# ---- After login ----
# Load user
row = conn.execute("""SELECT username, lang, theme, avatar, email, fdc_key, plan_type, meal_structure, age, sex, height_cm, weight_kg,
                             bodyfat, birthdate, activity, target_weight, training_days, fasting
                      FROM users WHERE username=?""", (st.session_state["user"],)).fetchone()
(u, lang, theme, avatar, email, fdc_key, plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, birthdate, activity, target_weight, training_days, fasting) = row
st.session_state.setdefault("lang", lang or "en")
st.session_state.setdefault("theme", theme or "tropical")
st.session_state.setdefault("fdc_key", fdc_key or DEFAULT_FDC)

# Theme toggle
picked_theme = st.sidebar.radio(T("theme"), ["tropical","minimal"],
                                index=0 if (st.session_state["theme"]=="tropical") else 1,
                                format_func=lambda x: "🌴 Tropical" if x=="tropical" else "⚪ Minimal")
st.session_state["theme"] = picked_theme
st.markdown(css_tropical() if picked_theme=="tropical" else css_minimal(), unsafe_allow_html=True)

# Header with avatar on right
hc1, hc2 = st.columns([6,1])
with hc1:
    st.title("Carioca")
    st.caption("Personalized plan engine • Theme toggle • OFF + FDC search • v2.2")
with hc2:
    if avatar: st.image(avatar, width=72)

# Top bar: language + logout
if st.sidebar.button(T("logout")):
    st.session_state.clear(); st.rerun()
st.sidebar.radio(T("language"), ["en","tr"], key="lang", format_func=lambda x: "English" if x=="en" else "Türkçe")

# Helpers
def mifflin_st_jeor(sex:str, weight, height_cm, age):
    if age is None: age = 30
    if height_cm is None: height_cm = 175
    if weight is None: weight = 80.0
    if sex == "male":
        return 10*weight + 6.25*height_cm - 5*age + 5
    else:
        return 10*weight + 6.25*height_cm - 5*age - 161
def activity_factor(level:str): return {"sedentary":1.2,"light":1.35,"moderate":1.55,"high":1.75,"very_high":1.95}.get(level or "light", 1.35)
def macro_split(cal, workout=True, weight=80):
    if weight is None: weight = 80
    protein_g = round(2.0 * float(weight))
    carbs_g = round((1.8 if workout else 0.8) * float(weight))
    fat_g = max(0, round((cal - (protein_g*4 + carbs_g*4))/9))
    return protein_g, carbs_g, fat_g

# Tabs
tabs = st.tabs([T("profile"), T("deficit_calc"), T("nutrition"), T("workout"), T("progress"), T("reminders"), T("summary")])

# PROFILE
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        # birthdate-driven age
        bd_val = pd.to_datetime(birthdate).date() if birthdate else None
        bd_input = st.date_input(T("birthdate"), value=bd_val) if True else None
        # derive age
        if bd_input:
            today = date.today()
            age_calc = today.year - bd_input.year - ((today.month, today.day) < (bd_input.month, bd_input.day))
            age = age_calc
        age = st.number_input(T("age"), min_value=10, max_value=100, value=int(age) if age else 30)
        sex = st.selectbox(T("sex"), ["male","female"], index=0 if (sex or "male")=="male" else 1, format_func=lambda x: T(x))
        height_cm = st.number_input(T("height_cm"), min_value=120, max_value=230, value=int(height_cm) if height_cm else 175)
        st.write("—"); st.subheader(T("change_username"))
        newu = st.text_input(T("new_username"), value=u)
        if st.button("Apply username"):
            if newu and newu != u:
                try:
                    conn.execute("UPDATE users SET username=? WHERE username=?", (newu, u))
                    conn.execute("UPDATE weights SET username=? WHERE username=?", (newu, u))
                    conn.execute("UPDATE food_logs SET username=? WHERE username=?", (newu, u))
                    conn.execute("UPDATE workout_logs SET username=? WHERE username=?", (newu, u))
                    conn.commit(); st.session_state["user"] = newu; st.success("Username updated. Please re-login.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")
    with col2:
        weight_kg = st.number_input(T("weight_kg"), min_value=30.0, max_value=250.0, value=float(weight_kg) if weight_kg else 80.0, step=0.1)
        bodyfat_val = float(bodyfat) if bodyfat not in (None,"") else 0.0
        bodyfat_in = st.number_input(T("bodyfat_pct"), min_value=0.0, max_value=60.0, value=bodyfat_val, step=0.1)
        bodyfat = bodyfat_in if bodyfat_in>0 else None
        target_weight = st.number_input(T("target_weight"), min_value=30.0, max_value=250.0, value=float(target_weight) if target_weight else 80.0, step=0.1)
        st.subheader(T("avatar"))
        photo = st.file_uploader(T("upload_photo"), type=["png","jpg","jpeg"])
        if photo:
            b64 = base64.b64encode(photo.read()).decode("utf-8")
            avatar = f"data:image/{photo.type.split('/')[-1]};base64,{b64}"
    with col3:
        activity = st.selectbox(T("activity"), ["sedentary","light","moderate","high","very_high"],
                                index=["sedentary","light","moderate","high","very_high"].index(activity or "light"),
                                format_func=lambda x: T(x))
        training_days = st.slider(T("training_days"), 1, 7, int(training_days) if training_days else 5)
        fasting = st.selectbox(T("fasting"), [T("fasting_16_8")])
        plan_type = st.selectbox(T("plan_type"), ["full_body","ppl","upper_lower","cardio_core"],
                                 index=["full_body","ppl","upper_lower","cardio_core"].index(plan_type or "full_body"), format_func=lambda x: T(x))
        meal_structure = st.selectbox(T("meal_structure"), ["two_plus_one","three_meals","four_meals"],
                                      index=["two_plus_one","three_meals","four_meals"].index(meal_structure or "two_plus_one"), format_func=lambda x: T(x))
        email = st.text_input(T("email"), value=email or "")
        fdc_key = st.text_input(T("use_fdc"), value=st.session_state.get("fdc_key") or DEFAULT_FDC, help=T("fdc_note"))
    if st.button(T("save"), type="primary"):
        conn.execute("""UPDATE users SET lang=?, theme=?, avatar=?, email=?, fdc_key=?, plan_type=?, meal_structure=?, age=?, sex=?, height_cm=?, weight_kg=?, bodyfat=?, birthdate=?, activity=?, target_weight=?, training_days=?, fasting=? WHERE username=?""",
                     (st.session_state["lang"], st.session_state["theme"], avatar, email, fdc_key, plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, (bd_input.isoformat() if bd_input else None), activity, target_weight, training_days, fasting, u))
        conn.commit(); st.session_state["fdc_key"] = fdc_key; st.success(T("update"))
    # metrics
    bmr = mifflin_st_jeor(sex, weight_kg, height_cm, age); tdee = bmr*activity_factor(activity)
    wcal = round(tdee*0.75); rcal = round((bmr*1.35)*0.75)
    pc_w, cc_w, fc_w = macro_split(wcal, workout=True, weight=weight_kg); pc_r, cc_r, fc_r = macro_split(rcal, workout=False, weight=weight_kg)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(T("bmr"), f"{int(bmr)} {T('kcal')}"); c2.metric(T("tdee"), f"{int(tdee)} {T('kcal')}")
    c3.metric(T("workout_day_calories"), f"{wcal} {T('kcal')}"); c4.metric(T("rest_day_calories"), f"{rcal} {T('kcal')}")

# DEFICIT CALC
with tabs[1]:
    day_type = st.selectbox(T("day_type"), [T("workout_day"), T("rest_day")])
    deficit = st.slider(T("deficit_percent"), 5, 35, 25, step=1)
    base_tdee = bmr*activity_factor(activity) if day_type==T("workout_day") else bmr*1.35
    target_cal = round(base_tdee*(1-deficit/100)); weekly_loss = round(((base_tdee-target_cal)*7)/7700,2); weight_3m = round((weight_kg or 80) - weekly_loss*12, 1)
    c1,c2,c3,c4 = st.columns(4); c1.metric(T("tdee"), int(base_tdee)); c2.metric(T("target_cal"), int(target_cal)); c3.metric(T("weekly_loss"), f"{weekly_loss} kg"); c4.metric(T("three_months_weight"), f"{weight_3m} kg")

# Food APIs
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

# NUTRITION
with tabs[2]:
    st.subheader(T("log_food"))
    # Date & Meal
    picked_date = st.date_input("Tarih", value=date.today(), format="DD.MM.YYYY")
    meal_sel = st.selectbox("Öğün", ["1. ana öğün","2. ana öğün","3. ana öğün","1. ara öğün","2. ara öğün","3. ara öğün"])
    colA, colB, colC = st.columns([3,1,1])
    with colA:
        q = st.text_input(T("search_food"))
    with colB:
        grams = st.number_input(T("amount_g"), min_value=1, max_value=2000, value=100)
    with colC:
        lang_pick = st.radio(T("language"), ["en","tr"], horizontal=True, key="food_lang", format_func=lambda x: "English" if x=="en" else "Türkçe")
    df = pd.DataFrame()
    if q:
        df_off = off_search(q, "tr" if lang_pick=="tr" else "en")
        df_fdc = fdc_search(q, st.session_state.get("fdc_key") or DEFAULT_FDC) if st.session_state.get("fdc_key") else pd.DataFrame()
        frames = [x for x in [df_fdc, df_off] if not x.empty]
        if frames: df = pd.concat(frames, ignore_index=True)
    st.caption(T("api_results"))
    show_cols = ["source","name","brand","kcal_100g","protein_100g","carbs_100g","fat_100g","sugars_100g","fiber_100g","sodium_100g","salt_100g"]
    st.dataframe(df[show_cols] if not df.empty else df, use_container_width=True)
    if df.empty and q: st.warning(T("no_results")+" — "+T("search_tip"))
    if not df.empty:
        sel_idx = st.selectbox(T("select_food"), list(range(len(df))), format_func=lambda i: f"{df.iloc[i]['name']} ({df.iloc[i]['brand']}) [{df.iloc[i]['source']}]")
        if st.button(T("add")):
            rowf = df.iloc[int(sel_idx)].to_dict(); vals = macros_from_grams(rowf, grams)
            conn.execute("""INSERT INTO food_logs(username, dt, meal, food_name, grams, kcal, protein, carbs, fat, sugars, fiber, sodium, salt) 
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (u, picked_date.isoformat(), meal_sel, rowf['name'], grams, vals["kcal"], vals["protein"], vals["carbs"], vals["fat"], vals["sugars"], vals["fiber"], vals["sodium"], vals["salt"]))
            conn.commit(); st.success(T("added"))

    # Title as date + weekday TR
    weekday_tr = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"][picked_date.weekday()]
    st.subheader(f"{picked_date.strftime('%d.%m.%Y')} {weekday_tr}")

    logs = pd.read_sql_query("""SELECT meal, food_name, grams, kcal, protein, carbs, fat 
                                FROM food_logs WHERE username=? AND dt=? ORDER BY meal""",
                             conn, params=(u, picked_date.isoformat()))
    st.dataframe(logs, use_container_width=True)

    # Determine target based on workout/rest toggle
    is_workout = st.toggle("Bugün antrenman günü", value=(picked_date.weekday() in [0,2,4]))
    base_tdee = bmr*activity_factor(activity) if is_workout else bmr*1.35
    target_cal = round(base_tdee*0.75)
    tp, tc, tf = macro_split(target_cal, workout=is_workout, weight=weight_kg)

    tot = logs[["kcal","protein","carbs","fat"]].sum() if not logs.empty else pd.Series({"kcal":0,"protein":0,"carbs":0,"fat":0})

    # Stacked vertical bars
    fig = go.Figure()
    # Calorie
    fig.add_trace(go.Bar(x=["Kalori"], y=[min(tot["kcal"], target_cal)], name="Alınan"))
    over_cal = max(0, tot["kcal"]-target_cal)
    if over_cal>0: fig.add_trace(go.Bar(x=["Kalori"], y=[over_cal], name="Aşan", marker_color="red"))
    # Protein
    fig.add_trace(go.Bar(x=["Protein"], y=[min(tot["protein"], tp)], name="Alınan"))
    over_p = max(0, tot["protein"]-tp)
    if over_p>0: fig.add_trace(go.Bar(x=["Protein"], y=[over_p], marker_color="red", showlegend=False))
    # Carbs
    fig.add_trace(go.Bar(x=["Karb"], y=[min(tot["carbs"], tc)], name="Alınan"))
    over_c = max(0, tot["carbs"]-tc)
    if over_c>0: fig.add_trace(go.Bar(x=["Karb"], y=[over_c], marker_color="red", showlegend=False))
    fig.update_layout(barmode="stack", yaxis=dict(range=[0, max(target_cal, tp, tc)+100]))
    st.plotly_chart(fig, use_container_width=True)

    deficit = (target_cal - float(tot["kcal"]))
    if deficit>0:
        st.success(f"Günlük kalori açığı: {int(deficit)} kcal → ~{round(deficit/7700,3)} kg yağ")
    else:
        st.warning(f"Hedefi {int(-deficit)} kcal aştın")

# WORKOUT
with tabs[3]:
    st.subheader(T("workout_plan"))
    day = st.selectbox(T("day_picker"), ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
    # plan
    alts = {
        "Squat":["Leg Press","Goblet Squat","Hack Squat"],
        "Bench Press":["Incline DB Press","Push-up","Machine Chest Press"],
        "Barbell Row":["Seated Row","Lat Pulldown","Dumbbell Row"],
        "Romanian Deadlift":["Hip Thrust","Back Extension","Good Morning"],
        "Shoulder Press":["Arnold Press","Machine Shoulder Press","Push Press"],
        "Walking Lunge":["Reverse Lunge","Split Squat","Step-up"],
        "Deadlift":["Rack Pull","Trap Bar Deadlift","Sumo Deadlift"],
        "Lat Pulldown":["Pull-up","Seated Row","One-arm Pulldown"],
        "Leg Curl":["Romanian Deadlift","Glute Ham Raise","Nordic Curl"]
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

    todays = schedule.get(day, [])
    total_burn = 0
    if not todays:
        st.info("Rest / Dinlenme")
    else:
        for i,(name, sr, mg) in enumerate(todays, start=1):
            cols = st.columns([3,2,2])
            with cols[0]:
                st.markdown(f"**{i}. {name}** — Target: {sr}")
                # parse target
                try:
                    t_sets, t_reps = sr.lower().split("x"); t_sets=int(t_sets.replace("~","").strip()); t_reps=int(''.join([c for c in t_reps if c.isdigit()]))
                except:
                    t_sets, t_reps = 3, 10
                perf_sets = st.number_input("Sets", 0, 20, t_sets, key=f"s_{i}")
                perf_reps = st.number_input("Reps", 0, 100, t_reps, key=f"r_{i}")
                # calorie estimate
                cal = round(0.1 * perf_sets * perf_reps * (float(weight_kg or 70)/70.0))
                st.write(f"≈ **{cal} kcal**")
                if st.button("Kaydet", key=f"save_{i}"):
                    conn.execute("""INSERT INTO workout_logs(username, dt, day, exercise, target_sets, target_reps, perf_sets, perf_reps, calories)
                                    VALUES(?,?,?,?,?,?,?,?,?)""",
                                 (u, date.today().isoformat(), day, name, t_sets, t_reps, int(perf_sets), int(perf_reps), cal))
                    conn.commit(); st.success(f"{name} kaydedildi (+{cal} kcal)")
                total_burn += cal
            with cols[1]:
                img = muscles.get(mg)
                if img: st.image(img, caption=mg, width=140)
            with cols[2]:
                st.markdown(f"[{T('video_guide')}]({'https://www.youtube.com/results?search_query=' + name.replace(' ','+')})")
        st.info(f"**Toplam Yakılan (tahmini): {int(total_burn)} kcal**")

# PROGRESS
with tabs[4]:
    st.subheader(T("progress_charts"))
    wcol1, wcol2 = st.columns([2,1])
    with wcol1:
        st.write(T("weight_entry"))
        new_w = st.number_input(T("weight_kg"), min_value=30.0, max_value=300.0, value=float(weight_kg) if weight_kg else 80.0, step=0.1, key="neww")
    with wcol2:
        if st.button(T("add_weight")):
            conn.execute("INSERT INTO weights(username, dt, weight) VALUES(?,?,?)", (u, date.today().isoformat(), float(new_w)))
            conn.execute("UPDATE users SET weight_kg=? WHERE username=?", (float(new_w), u))
            conn.commit(); st.success("Saved")
    wdf = pd.read_sql_query("SELECT dt, weight FROM weights WHERE username=?", conn, params=(u,))
    if not wdf.empty:
        wdf["dt"] = pd.to_datetime(wdf["dt"]); fig = px.line(wdf, x="dt", y="weight", markers=True, title="Weight Trend"); st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No weight data yet / Kilo kaydı yok")

# REMINDERS
with tabs[5]:
    st.subheader(T("reminders"))
    water_on = st.toggle(T("remind_water"))
    posture_on = st.toggle(T("remind_posture"))
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
      if (waterOn && inRange(h,8,22)) setTimeout(()=>notify("{L['tr']['water_message']}"), 1000);
      if (postureOn && inRange(h,8,21)) setTimeout(()=>notify("{L['tr']['posture_message']}"), 2000);
      if (waterOn) setInterval(()=>{{ const h=(new Date()).getHours(); if(inRange(h,8,22)) notify("{L['tr']['water_message']}"); }}, 2*60*60*1000);
      if (postureOn) setInterval(()=>{{ const h=(new Date()).getHours(); if(inRange(h,8,21)) notify("{L['tr']['posture_message']}"); }}, 3*60*60*1000);
    }}
    schedule();
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)

# SUMMARY
with tabs[6]:
    picked_date = st.date_input("Tarih (Özet)", value=date.today(), format="DD.MM.YYYY", key="sum_date")
    st.header(f"Özet — {picked_date.strftime('%d.%m.%Y')}")
    # totals
    nut = pd.read_sql_query("SELECT SUM(kcal) as kcal, SUM(protein) as protein, SUM(carbs) as carbs FROM food_logs WHERE username=? AND dt=?",
                            conn, params=(u, picked_date.isoformat()))
    eat_k = float(nut.iloc[0]["kcal"] or 0); eat_p=float(nut.iloc[0]["protein"] or 0); eat_c=float(nut.iloc[0]["carbs"] or 0)
    wrk = pd.read_sql_query("SELECT SUM(calories) as kcal FROM workout_logs WHERE username=? AND dt=?", conn, params=(u, picked_date.isoformat()))
    burn = float(wrk.iloc[0]["kcal"] or 0)
    # target
    is_workout = picked_date.weekday() in [0,2,4]
    base_tdee = bmr*activity_factor(activity) if is_workout else bmr*1.35
    target_cal = round(base_tdee*0.75); tp, tc, tf = macro_split(target_cal, workout=is_workout, weight=weight_kg)
    net_def = (target_cal - eat_k) + burn
    fat = round(net_def/7700,3) if net_def>0 else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Alınan", f"{int(eat_k)} kcal"); c2.metric("Yakılan", f"{int(burn)} kcal"); c3.metric("Net Açık", f"{int(net_def)} kcal"); c4.metric("Tah. Yağ", f"{fat} kg")

    # Bars same as nutrition
    tot = pd.Series({"kcal":eat_k,"protein":eat_p,"carbs":eat_c})
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Kalori"], y=[min(tot["kcal"], target_cal)]))
    over_cal = max(0, tot["kcal"]-target_cal)
    if over_cal>0: fig.add_trace(go.Bar(x=["Kalori"], y=[over_cal], marker_color="red"))
    fig.add_trace(go.Bar(x=["Protein"], y=[min(tot["protein"], tp)]))
    over_p = max(0, tot["protein"]-tp)
    if over_p>0: fig.add_trace(go.Bar(x=["Protein"], y=[over_p], marker_color="red", showlegend=False))
    fig.add_trace(go.Bar(x=["Karb"], y=[min(tot["carbs"], tc)]))
    over_c = max(0, tot["carbs"]-tc)
    if over_c>0: fig.add_trace(go.Bar(x=["Karb"], y=[over_c], marker_color="red", showlegend=False))
    fig.update_layout(barmode="stack", yaxis=dict(range=[0, max(target_cal, tp, tc)+100]))
    st.plotly_chart(fig, use_container_width=True)
