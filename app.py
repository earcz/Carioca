
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sqlite3, bcrypt, json, requests, base64
from datetime import datetime, timedelta, date
import plotly

# email section starts
import smtplib, ssl, secrets, string
from email.mime.text import MIMEText

def send_reset_email(to_email: str, username: str):
    # basit bir token üret
    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    body = f"Merhaba {username},\n\nCarioca şifre sıfırlama kodun: {token}\n\nBu kodu uygulamadaki şifre sıfırlama alanına girerek yeni şifreni oluşturabilirsin."
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
# email section ends

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

def get_conn():
    conn = sqlite3.connect("carioca_v21.db", check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        pw_hash BLOB NOT NULL,
        lang TEXT DEFAULT 'en',
        theme TEXT DEFAULT 'tropical',
        avatar TEXT,
        email TEXT,
        plan_type TEXT DEFAULT 'full_body',
        meal_structure TEXT DEFAULT 'two_plus_one',
        age INT, sex TEXT, height_cm REAL, weight_kg REAL, bodyfat REAL,
        activity TEXT, target_weight REAL, training_days INT, fasting TEXT,
        created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS weights(
        username TEXT, dt TEXT, weight REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS food_logs(
        username TEXT, dt TEXT, food_name TEXT, grams REAL,
        kcal REAL, protein REAL, carbs REAL, fat REAL, sugars REAL, fiber REAL, sodium REAL, salt REAL
    )""")
    conn.commit()
    return conn
conn = get_conn()

def hash_pw(pw:str)->bytes: return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())
def check_pw(pw:str, h:bytes)->bool:
    try: return bcrypt.checkpw(pw.encode(), h)
    except Exception: return False

def login_register_ui():
    st.markdown(css_tropical(), unsafe_allow_html=True)
    st.sidebar.header("Carioca 🌴")
    lang = st.sidebar.radio(T("language"), ["en", "tr"], format_func=lambda x: "English" if x=="en" else "Türkçe", key="lang")
    c1,c2 = st.columns(2)
    with c1:
        st.subheader(T("login"))
        u = st.text_input(T("username"))
        p = st.text_input(T("password"), type="password")
        if st.button(T("login")):
            row = conn.execute("SELECT pw_hash, lang FROM users WHERE username=?", (u,)).fetchone()
            if row and check_pw(p, row[0]):
                if "lang" not in st.session_state: st.session_state["lang"] = row[1] or lang
                st.session_state["user"] = u
                st.rerun()
            else:
                st.error("Invalid credentials / Geçersiz bilgiler")
        st.divider()
        st.subheader(T("password_reset"))
        email = st.text_input(T("email"))
        if st.button(T("send_reset")):
            if email:
                send_reset_email(email, u or "user")
            else:
                st.warning("Lütfen profilinden e-posta ekle veya buraya yaz.")
    with c2:
        st.subheader(T("register"))
        u = st.text_input(T("username")+" *", key="ru")
        p = st.text_input(T("password")+" *", type="password", key="rp")
        if st.button(T("register")):
            if not u or not p:
                st.warning("Fill required fields")
            else:
                try:
                    conn.execute("INSERT INTO users(username, pw_hash, lang, created_at) VALUES(?,?,?,?)",
                                 (u, hash_pw(p), lang, datetime.utcnow().isoformat()))
                    conn.commit()
                    st.success("Registered. Please log in.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

if "user" not in st.session_state:
    login_register_ui()
    st.stop()

user = st.session_state["user"]
row = conn.execute("SELECT username, lang, theme, avatar, email, plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, activity, target_weight, training_days, fasting FROM users WHERE username=?", (user,)).fetchone()
(u, lang, theme, avatar, email, plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, activity, target_weight, training_days, fasting) = row
st.session_state.setdefault("lang", lang or "en")
st.session_state.setdefault("theme", theme or "tropical")

picked_theme = st.sidebar.radio(T("theme"), ["tropical","minimal"], index=0 if (st.session_state["theme"]=="tropical") else 1,
                                format_func=lambda x: "🌴 Tropical" if x=="tropical" else "⚪ Minimal")
st.session_state["theme"] = picked_theme
st.markdown(css_tropical() if picked_theme=="tropical" else css_minimal(), unsafe_allow_html=True)

st.title("Carioca")
st.caption("Personalized plan engine • Theme toggle • OpenFoodFacts + USDA FDC search")

if st.sidebar.button(T("logout")):
    st.session_state.clear(); st.experimental_rerun()
st.sidebar.radio(T("language"), ["en","tr"], key="lang", format_func=lambda x: "English" if x=="en" else "Türkçe")

def mifflin_st_jeor(sex:str, weight, height_cm, age):
    if sex == "male":
        return 10*weight + 6.25*height_cm - 5*age + 5
    else:
        return 10*weight + 6.25*height_cm - 5*age - 161
def activity_factor(level:str): return {"sedentary":1.2,"light":1.35,"moderate":1.55,"high":1.75,"very_high":1.95}.get(level, 1.35)
def macro_split(cal, workout=True, weight=80):
    protein_g = round(2.0 * weight); carbs_g = round((1.8 if workout else 0.8) * weight)
    fat_g = max(0, round((cal - (protein_g*4 + carbs_g*4))/9)); return protein_g, carbs_g, fat_g

tabs = st.tabs([T("profile"), T("deficit_calc"), T("nutrition"), T("workout"), T("progress"), T("reminders")])

with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.number_input(T("age"), min_value=10, max_value=100, value=int(age) if age else 34)
        sex = st.selectbox(T("sex"), ["male","female"], index=0 if (sex or "male")=="male" else 1, format_func=lambda x: T(x))
        height_cm = st.number_input(T("height_cm"), min_value=120, max_value=230, value=int(height_cm) if height_cm else 180)
        st.write("—"); st.subheader(T("change_username"))
        newu = st.text_input(T("new_username"), value=user)
        if st.button("Apply username"):
            if newu and newu != user:
                try:
                    conn.execute("UPDATE users SET username=? WHERE username=?", (newu, user))
                    conn.execute("UPDATE weights SET username=? WHERE username=?", (newu, user))
                    conn.execute("UPDATE food_logs SET username=? WHERE username=?", (newu, user))
                    conn.commit(); st.session_state["user"] = newu; st.success("Username updated. Please re-login.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")
    with col2:
        weight_kg = st.number_input(T("weight_kg"), min_value=30.0, max_value=250.0, value=float(weight_kg) if weight_kg else 94.0, step=0.1)
        bodyfat = st.number_input(T("bodyfat_pct"), min_value=0.0, max_value=60.0, value=float(bodyfat) if bodyfat else 27.0, step=0.1)
        target_weight = st.number_input(T("target_weight"), min_value=30.0, max_value=250.0, value=float(target_weight) if target_weight else 82.0, step=0.1)
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
        plan_type = st.selectbox(T("plan_type"), ["full_body","ppl","upper_lower","cardio_core"], index=["full_body","ppl","upper_lower","cardio_core"].index(plan_type or "full_body"), format_func=lambda x: T(x))
        meal_structure = st.selectbox(T("meal_structure"), ["two_plus_one","three_meals","four_meals"], index=["two_plus_one","three_meals","four_meals"].index(meal_structure or "two_plus_one"), format_func=lambda x: T(x))
        email = st.text_input(T("email"), value=email or "")
        st.text_input(T("use_fdc"), key="fdc_key", help=T("fdc_note"))
    if st.button(T("save"), type="primary"):
        conn.execute("""UPDATE users SET lang=?, theme=?, avatar=?, email=?, plan_type=?, meal_structure=?, age=?, sex=?, height_cm=?, weight_kg=?, bodyfat=?, activity=?, target_weight=?, training_days=?, fasting=? WHERE username=?""",
                     (st.session_state["lang"], st.session_state["theme"], avatar, email, plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, activity, target_weight, training_days, fasting, st.session_state["user"]))
        conn.commit(); st.success(T("update"))
    bmr = mifflin_st_jeor(sex, weight_kg, height_cm, age); tdee = bmr*activity_factor(activity)
    wcal = round(tdee*0.75); rcal = round((bmr*1.35)*0.75)
    pc_w, cc_w, fc_w = macro_split(wcal, workout=True, weight=weight_kg); pc_r, cc_r, fc_r = macro_split(rcal, workout=False, weight=weight_kg)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(T("bmr"), f"{int(bmr)} {T('kcal')}"); c2.metric(T("tdee"), f"{int(tdee)} {T('kcal')}")
    c3.metric(T("workout_day_calories"), f"{wcal} {T('kcal')}"); c4.metric(T("rest_day_calories"), f"{rcal} {T('kcal')}")
    st.write(T("macros")+":"); st.write(f"🏋️ {T('workout_day')}: P {pc_w}g / C {cc_w}g / F {fc_w}g"); st.write(f"🛌 {T('rest_day')}: P {pc_r}g / C {cc_r}g / F {fc_r}g")
    if avatar: st.image(avatar, caption="Avatar", width=120)

with tabs[1]:
    day_type = st.selectbox(T("day_type"), [T("workout_day"), T("rest_day")])
    deficit = st.slider(T("deficit_percent"), 5, 35, 25, step=1)
    base_tdee = bmr*activity_factor(activity) if day_type==T("workout_day") else bmr*1.35
    target_cal = round(base_tdee*(1-deficit/100)); weekly_loss = round(((base_tdee-target_cal)*7)/7700,2); weight_3m = round(weight_kg - weekly_loss*12, 1)
    c1,c2,c3,c4 = st.columns(4); c1.metric(T("tdee"), int(base_tdee)); c2.metric(T("target_cal"), int(target_cal)); c3.metric(T("weekly_loss"), f"{weekly_loss} kg"); c4.metric(T("three_months_weight"), f"{weight_3m} kg")

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
        v=row.get(f"{k}_100g"); vals[k]= (v*factor if isinstance(v,(int,float)) else 0.0)
    return vals

with tabs[2]:
    st.subheader(T("log_food"))
    colA, colB, colC = st.columns([3,1,1])
    with colA:
        q = st.text_input(T("search_food"))
    with colB:
        grams = st.number_input(T("amount_g"), min_value=1, max_value=2000, value=100)
    with colC:
        lang_pick = st.radio(T("language"), ["en","tr"], horizontal=True, key="food_lang", format_func=lambda x: "English" if x=="en" else "Türkçe")
    df = pd.DataFrame()
    if q:
        if st.session_state.get("fdc_key"):
            df = pd.concat([fdc_search(q, st.session_state["fdc_key"]), off_search(q, "tr" if lang_pick=="tr" else "en")], ignore_index=True)
        else:
            df = off_search(q, "tr" if lang_pick=="tr" else "en")
    st.caption(T("api_results"))
    show_cols = ["source","name","brand","kcal_100g","protein_100g","carbs_100g","fat_100g","sugars_100g","fiber_100g","sodium_100g","salt_100g"]
    st.dataframe(df[show_cols] if not df.empty else df, use_container_width=True)
    if df.empty and q: st.warning(T("no_results")+" — "+T("search_tip"))
    if not df.empty:
        sel_idx = st.selectbox(T("select_food"), list(range(len(df))), format_func=lambda i: f"{df.iloc[i]['name']} ({df.iloc[i]['brand']}) [{df.iloc[i]['source']}]")
        if st.button(T("add")):
            rowf = df.iloc[int(sel_idx)].to_dict(); vals = macros_from_grams(rowf, grams)
            conn.execute("INSERT INTO food_logs(username, dt, food_name, grams, kcal, protein, carbs, fat, sugars, fiber, sodium, salt) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                         (user, date.today().isoformat(), rowf['name'], grams, vals["kcal"], vals["protein"], vals["carbs"], vals["fat"], vals["sugars"], vals["fiber"], vals["sodium"], vals["salt"]))
            conn.commit(); st.success(T("added"))
    st.divider(); st.subheader(T("today_log"))
    logs = pd.read_sql_query("SELECT food_name, grams, kcal, protein, carbs, fat, sugars, fiber, sodium, salt FROM food_logs WHERE username=? AND dt=?",
                             conn, params=(user, date.today().isoformat()))
    if logs.empty:
        st.info("No entries yet / Kayıt yok"); totals = pd.Series({"kcal":0,"protein":0,"carbs":0,"fat":0})
    else:
        totals = logs[["kcal","protein","carbs","fat"]].sum()
        st.dataframe(logs, use_container_width=True)
        st.write(f"**{T('total')}**: {int(totals['kcal'])} {T('kcal')}, P {int(totals['protein'])}g / C {int(totals['carbs'])}g / F {int(totals['fat'])}g")
        fig = px.pie(values=[max(totals['protein'],1)*4, max(totals['carbs'],1)*4, max(totals['fat'],1)*9],
                     names=[T('protein'), T('carbs'), T('fat')], title=T('macros'))
        st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.subheader(T("workout_plan"))
    day = st.selectbox(T("day_picker"), ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
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
            "Monday":[("Bench Press","4x8","Chest"),("Shoulder Press","3x12","Shoulders")],
            "Wednesday":[("Barbell Row","4x8","Back"),("Lat Pulldown","3x12","Back")],
            "Friday":[("Squat","4x8","Quads"),("Leg Curl","3x12","Hamstrings/Glutes")]
        }
    elif plan_type=="upper_lower":
        schedule = {
            "Monday":[("Bench Press","4x8","Chest"),("Barbell Row","4x8","Back"),("Shoulder Press","3x12","Shoulders")],
            "Tuesday":[("Squat","4x8","Quads"),("Romanian Deadlift","3x10","Hamstrings/Glutes")],
            "Thursday":[("Incline DB Press","3x10","Chest"),("Seated Row","3x12","Back")],
            "Friday":[("Leg Press","4x12","Quads"),("Leg Curl","3x12","Hamstrings/Glutes")]
        }
    else:
        schedule = {
            "Monday":[("Treadmill Incline","40min","Cardio"),("Plank","3x max","Core")],
            "Wednesday":[("Treadmill Incline","40min","Cardio"),("Leg Raise","3x15","Core")],
            "Friday":[("Treadmill Incline","40min","Cardio"),("Side Plank","3x30s/side","Core")]
        }
    todays = schedule.get(day, [])
    if not todays:
        st.info("Rest / Dinlenme")
    else:
        for i,(name, sr, mg) in enumerate(todays, start=1):
            cols = st.columns([3,2,1])
            with cols[0]:
                st.markdown(f"**{i}. {name}** — {sr}")
                options = [name] + alts.get(name, [])
                _ = st.selectbox(T("alt_exercises"), options, key=f"alt_{i}")
            with cols[1]:
                img = muscles.get(mg)
                if img: st.image(img, caption=mg, width=140)
            with cols[2]:
                st.markdown(f"[{T('video_guide')}]({'https://www.youtube.com/results?search_query=' + name.replace(' ','+')} )")

with tabs[4]:
    st.subheader(T("progress_charts"))
    wcol1, wcol2 = st.columns([2,1])
    with wcol1:
        st.write(T("weight_entry"))
        new_w = st.number_input(T("weight_kg"), min_value=30.0, max_value=300.0, value=float(weight_kg), step=0.1, key="neww")
    with wcol2:
        if st.button(T("add_weight")):
            conn.execute("INSERT INTO weights(username, dt, weight) VALUES(?,?,?)", (user, date.today().isoformat(), float(new_w)))
            conn.execute("UPDATE users SET weight_kg=? WHERE username=?", (float(new_w), user))
            conn.commit(); st.success("Saved")
    wdf = pd.read_sql_query("SELECT dt, weight FROM weights WHERE username=?", conn, params=(user,))
    if not wdf.empty:
        wdf["dt"] = pd.to_datetime(wdf["dt"]); fig = px.line(wdf, x="dt", y="weight", markers=True, title="Weight Trend"); st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No weight data yet / Kilo kaydı yok")

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
