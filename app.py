
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sqlite3, bcrypt, json, requests
from datetime import datetime, timedelta, date

st.set_page_config(
    page_title="Carioca v2 — Tropical/Minimal + Plan Engine",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- THEMES ----------
def css_tropical():
    return """
    <style>
    .stApp { background: linear-gradient(135deg,#FF7E5F 0%,#FFB88C 40%,#FFD86F 70%,#FF5F6D 100%) fixed; color: #1f2937;}
    .block-container { backdrop-filter: blur(6px); background-color: rgba(255,255,255,0.88); border-radius: 24px; padding: 2rem 2.2rem; }
    .metric-card { border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.75); border: 1px solid rgba(255,255,255,0.6); }
    .pill { padding: 4px 10px; border-radius: 999px; background: rgba(0,0,0,0.06); font-size: 12px; font-weight: 600; }
    </style>
    """

def css_minimal():
    return """
    <style>
    .stApp { background: #f5f7fb; color: #111827; }
    .block-container { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 2rem 2.2rem; }
    .metric-card { border-radius: 12px; padding: 14px; background: #fff; border: 1px solid #e5e7eb; }
    .pill { padding: 3px 8px; border-radius: 12px; background: #eef2ff; font-size: 12px; font-weight: 600; }
    </style>
    """

# ---------- Language ----------
@st.cache_data
def load_lang():
    with open("lang_en.json","r", encoding="utf-8") as f:
        en = json.load(f)
    with open("lang_tr.json","r", encoding="utf-8") as f:
        tr = json.load(f)
    return {"en": en, "tr": tr}
L = load_lang()

def T(key):
    lang = st.session_state.get("lang", "en")
    return L[lang].get(key, key)

# ---------- Database ----------
def get_conn():
    conn = sqlite3.connect("carioca_v2.db", check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        pw_hash BLOB NOT NULL,
        lang TEXT DEFAULT 'en',
        theme TEXT DEFAULT 'tropical',
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
        kcal REAL, protein REAL, carbs REAL, fat REAL
    )""")
    conn.commit()
    return conn

conn = get_conn()

# ---------- Auth ----------
def hash_pw(pw: str) -> bytes:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())

def check_pw(pw: str, pw_hash: bytes) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), pw_hash)
    except Exception:
        return False

def login_register_ui():
    st.sidebar.header("Carioca 🌴")
    lang = st.sidebar.radio(T("language"), ["en","tr"], format_func=lambda x: "English" if x=="en" else "Türkçe", key="lang")
    tab_login, tab_register = st.tabs([T("login"), T("register")])
    with tab_login:
        u = st.text_input(T("username"))
        p = st.text_input(T("password"), type="password")
        if st.button(T("login"), use_container_width=True):
            row = conn.execute("SELECT pw_hash, lang FROM users WHERE username=?", (u,)).fetchone()
            if row and check_pw(p, row[0]):
                st.session_state["user"] = u
                if "lang" not in st.session_state:
                    st.session_state["lang"] = row[1] or lang
                st.experimental_rerun()
            else:
                st.error("Invalid credentials / Geçersiz bilgiler")
    with tab_register:
        u = st.text_input(T("username")+" *", key="ru")
        p = st.text_input(T("password")+" *", type="password", key="rp")
        if st.button(T("register"), use_container_width=True):
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

# ---------- Load user ----------
user = st.session_state["user"]
row = conn.execute("SELECT username, lang, theme, plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, activity, target_weight, training_days, fasting FROM users WHERE username=?", (user,)).fetchone()
(u, lang, theme, plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, activity, target_weight, training_days, fasting) = row

# ---------- Theme toggle UI ----------
st.session_state.setdefault("theme", theme or "tropical")
picked_theme = st.sidebar.radio(T("theme"), ["tropical","minimal"], index=0 if (st.session_state["theme"]=="tropical") else 1,
                                format_func=lambda x: "🌴 Tropical" if x=="tropical" else "⚪ Minimal")
st.session_state["theme"] = picked_theme
if picked_theme == "tropical":
    st.markdown(css_tropical(), unsafe_allow_html=True)
else:
    st.markdown(css_minimal(), unsafe_allow_html=True)

st.title(f"🌴 Carioca v2 — {user}")
st.caption("Personalized plan engine • Theme toggle • OpenFoodFacts live search")

# ---------- Sidebar language + logout ----------
if st.sidebar.button(T("logout")):
    st.session_state.clear()
    st.experimental_rerun()
st.session_state.setdefault("lang", st.session_state.get("lang", "en"))
st.sidebar.radio(T("language"), ["en","tr"], key="lang", format_func=lambda x: "English" if x=="en" else "Türkçe")

# ---------- Helper Calcs ----------
def mifflin_st_jeor(sex:str, weight, height_cm, age):
    if sex == "male":
        return 10*weight + 6.25*height_cm - 5*age + 5
    else:
        return 10*weight + 6.25*height_cm - 5*age - 161

def activity_factor(level:str):
    return {"sedentary":1.2,"light":1.35,"moderate":1.55,"high":1.75,"very_high":1.95}.get(level, 1.35)

def macro_split(cal, workout=True, weight=80):
    protein_g = round(2.0 * weight)           # ~2g/kg
    carbs_g = round((1.8 if workout else 0.8) * weight)
    fats_kcal = cal - (protein_g*4 + carbs_g*4)
    fat_g = max(0, round(fats_kcal/9))
    return protein_g, carbs_g, fat_g

# ---------- Tabs ----------
tabs = st.tabs([T("profile"), T("deficit_calc"), T("nutrition"), T("workout"), T("progress")])

# ---------- PROFILE TAB ----------
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.number_input(T("age"), min_value=10, max_value=100, value=int(age) if age else 34)
        sex = st.selectbox(T("sex"), ["male","female"], index=0 if (sex or "male")=="male" else 1, format_func=lambda x: T(x))
        height_cm = st.number_input(T("height_cm"), min_value=120, max_value=230, value=int(height_cm) if height_cm else 180)
    with col2:
        weight_kg = st.number_input(T("weight_kg"), min_value=30.0, max_value=250.0, value=float(weight_kg) if weight_kg else 94.0, step=0.1)
        bodyfat = st.number_input(T("bodyfat_pct"), min_value=0.0, max_value=60.0, value=float(bodyfat) if bodyfat else 27.0, step=0.1)
        target_weight = st.number_input(T("target_weight"), min_value=30.0, max_value=250.0, value=float(target_weight) if target_weight else 82.0, step=0.1)
    with col3:
        activity = st.selectbox(T("activity"), ["sedentary","light","moderate","high","very_high"],
                                index=["sedentary","light","moderate","high","very_high"].index(activity or "light"),
                                format_func=lambda x: T(x))
        training_days = st.slider(T("training_days"), 1, 7, int(training_days) if training_days else 5)
        fasting = st.selectbox(T("fasting"), [T("fasting_16_8")])

    # Plan preferences
    st.subheader(T("plan_engine"))
    colp1, colp2 = st.columns(2)
    with colp1:
        plan_type = st.selectbox(T("plan_type"), ["full_body","ppl","upper_lower","cardio_core"], index=["full_body","ppl","upper_lower","cardio_core"].index(plan_type or "full_body"),
                                 format_func=lambda x: T(x))
    with colp2:
        meal_structure = st.selectbox(T("meal_structure"), ["two_plus_one","three_meals","four_meals"], index=["two_plus_one","three_meals","four_meals"].index(meal_structure or "two_plus_one"),
                                      format_func=lambda x: T(x))

    if st.button(T("save"), type="primary"):
        conn.execute("""UPDATE users SET lang=?, theme=?, plan_type=?, meal_structure=?, age=?, sex=?, height_cm=?, weight_kg=?, bodyfat=?, activity=?, target_weight=?, training_days=?, fasting=? WHERE username=?""",
                     (st.session_state["lang"], st.session_state["theme"], plan_type, meal_structure, age, sex, height_cm, weight_kg, bodyfat, activity, target_weight, training_days, fasting, user))
        conn.commit()
        st.success(T("update"))

    # Computed metrics with 25% default deficit
    bmr = mifflin_st_jeor(sex, weight_kg, height_cm, age)
    tdee = bmr * activity_factor(activity)
    wcal = round(tdee * 0.75)  # 25% deficit
    rcal = round((bmr*1.35) * 0.75)

    pc_w, cc_w, fc_w = macro_split(wcal, workout=True, weight=weight_kg)
    pc_r, cc_r, fc_r = macro_split(rcal, workout=False, weight=weight_kg)

    st.subheader("📊 Metrics")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(T("bmr"), f"{int(bmr)} {T('kcal')}")
    c2.metric(T("tdee"), f"{int(tdee)} {T('kcal')}")
    c3.metric(T("workout_day_calories"), f"{wcal} {T('kcal')}")
    c4.metric(T("rest_day_calories"), f"{rcal} {T('kcal')}")

    st.write(T("macros")+":")
    st.write(f"🏋️ {T('workout_day')}: P {pc_w}g / C {cc_w}g / F {fc_w}g")
    st.write(f"🛌 {T('rest_day')}: P {pc_r}g / C {cc_r}g / F {fc_r}g")

# ---------- DEFICIT CALCULATOR TAB ----------
with tabs[1]:
    st.subheader(T("deficit_calc"))
    # access previously computed bmr etc. from profile tab scope
    try:
        day_type = st.selectbox(T("day_type"), [T("workout_day"), T("rest_day")])
        deficit = st.slider(T("deficit_percent"), 5, 35, 25, step=1)
        base_tdee = bmr*activity_factor(activity) if day_type==T("workout_day") else bmr*1.35
        target_cal = round(base_tdee * (1 - deficit/100))
        weekly_loss = round(((base_tdee - target_cal) * 7) / 7700, 2)
        weight_3m = round(weight_kg - weekly_loss * 12, 1)
        st.metric(T("tdee"), f"{int(base_tdee)} {T('kcal')}")
        st.metric(T("target_cal"), f"{int(target_cal)} {T('kcal')}")
        st.metric(T("weekly_loss"), f"{weekly_loss} kg")
        st.metric(T("three_months_weight"), f"{weight_3m} kg")
    except Exception:
        st.info("Fill profile first")

# ---------- OpenFoodFacts Helpers ----------
@st.cache_data(ttl=30)
def off_search(query: str, lang_code: str = "en", page_size: int = 20):
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {"search_terms":query,"search_simple":1,"action":"process","json":1,"page_size":page_size,"cc":"world"}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        prods = data.get("products", [])
        rows = []
        for p in prods:
            nutr = p.get("nutriments", {}) or {}
            kcal = nutr.get("energy-kcal_100g"); prot = nutr.get("proteins_100g")
            carbs = nutr.get("carbohydrates_100g"); fat = nutr.get("fat_100g")
            if None in (kcal, prot, carbs, fat): continue
            name = p.get(f"product_name_{lang_code}") or p.get("product_name") or p.get(f"generic_name_{lang_code}") or p.get("generic_name") or "Unnamed"
            brand = p.get("brands","")
            rows.append({"name":name,"brand":brand,"kcal_100g":float(kcal),"protein_100g":float(prot),"carbs_100g":float(carbs),"fat_100g":float(fat)})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()

def macros_from_grams(row, grams: float):
    factor = grams / 100.0
    return (row["kcal_100g"]*factor, row["protein_100g"]*factor, row["carbs_100g"]*factor, row["fat_100g"]*factor)

# ---------- NUTRITION TAB ----------
with tabs[2]:
    st.subheader(T("log_food"))
    colA, colB, colC = st.columns([3,1,1])
    with colA:
        q = st.text_input(T("search_food"))
    with colB:
        grams = st.number_input(T("amount_g"), min_value=1, max_value=2000, value=100)
    with colC:
        lang_pick = st.radio(T("language"), ["en","tr"], horizontal=True, key="food_lang", format_func=lambda x: "English" if x=="en" else "Türkçe")
    df = off_search(q, "tr" if lang_pick=="tr" else "en") if q else pd.DataFrame()
    st.caption(T("api_results"))
    if df.empty and q:
        st.warning(T("no_results") + " — " + T("search_tip"))
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        sel_idx = st.selectbox(T("select_food"), list(range(len(df))), format_func=lambda i: f"{df.iloc[i]['name']} ({df.iloc[i]['brand']}) — {int(df.iloc[i]['kcal_100g'])} {T('kcal')}/{T('per100')}")
        if st.button(T("add")):
            rowf = df.iloc[int(sel_idx)]
            kcal, p, c, f = macros_from_grams(rowf, grams)
            conn.execute("INSERT INTO food_logs(username, dt, food_name, grams, kcal, protein, carbs, fat) VALUES(?,?,?,?,?,?,?,?)",
                        (user, date.today().isoformat(), rowf['name'], grams, float(kcal), float(p), float(c), float(f)))
            conn.commit()
            st.success(T("added"))
    st.divider()

    # Planned menu generator (uses OFF staples; if no network, it still runs with zeros handled)
    st.subheader(T("menu_suggestion"))
    if st.button(T("generate_menu")):
        # Determine targets by day
        weekday = date.today().weekday()
        is_workout = weekday in [0,2,4]
        target = (round((mifflin_st_jeor(sex, weight_kg, height_cm, age)*activity_factor(activity))*0.75) if is_workout else round((mifflin_st_jeor(sex, weight_kg, height_cm, age)*1.35)*0.75))
        p_target, c_target, f_target = (macro_split(target, workout=is_workout, weight=weight_kg))
        # Try to fetch staples
        staples = ["chicken breast","rice","oats","egg","yogurt","almonds","olive oil","banana","broccoli"]
        pool = pd.concat([off_search(s, "tr" if lang_pick=="tr" else "en", page_size=3) for s in staples], ignore_index=True)
        if pool.empty:
            st.warning("OFF unavailable right now; try again.")
        else:
            # pick representatives
            choose = lambda df, key: df.sort_values(by=key, ascending=False).head(1).iloc[0]
            p_food = choose(pool, "protein_100g")   # protein source
            c_food = choose(pool, "carbs_100g")     # carb source
            f_food = choose(pool, "fat_100g")       # fat source
            # split calories by structure a bit differently
            if meal_structure == "two_plus_one":
                splits = [0.45, 0.45, 0.10]
            elif meal_structure == "three_meals":
                splits = [0.35, 0.35, 0.30]
            else:
                splits = [0.30, 0.30, 0.20, 0.20]  # 4 meals -> extra line
            # grams calculator
            def grams_for_cals(row, cals): return int(cals / max(row["kcal_100g"]/100.0, 0.01))
            # build text
            remaining = target
            lines = []
            parts = len(splits)
            for i, spli in enumerate(splits):
                cals = target * spli
                gp = grams_for_cals(p_food, cals*0.5)
                gc = grams_for_cals(c_food, cals*0.35)
                gf = grams_for_cals(f_food, cals*0.15)
                meal_name = f"Meal {i+1}" if st.session_state["lang"]=="en" else f"Öğün {i+1}"
                lines.append(f"- **{meal_name}**: {gp} g {p_food['name']} + {gc} g {c_food['name']} + {gf} g {f_food['name']}")
            st.markdown("\n".join(lines))

    # Today's log & remaining
    st.subheader(T("today_log"))
    logs = pd.read_sql_query("SELECT food_name, grams, kcal, protein, carbs, fat FROM food_logs WHERE username=? AND dt=?",
                             conn, params=(user, date.today().isoformat()))
    if logs.empty:
        st.info("No entries yet / Kayıt yok")
        totals = pd.Series({"kcal":0,"protein":0,"carbs":0,"fat":0})
    else:
        totals = logs[["kcal","protein","carbs","fat"]].sum()
        st.dataframe(logs, use_container_width=True)
        st.write(f"**{T('total')}**: {int(totals['kcal'])} {T('kcal')}, P {int(totals['protein'])}g / C {int(totals['carbs'])}g / F {int(totals['fat'])}g")
    # Targets compare
    weekday = date.today().weekday(); is_workout = weekday in [0,2,4]
    try:
        target = (round((mifflin_st_jeor(sex, weight_kg, height_cm, age)*activity_factor(activity))*0.75) if is_workout else round((mifflin_st_jeor(sex, weight_kg, height_cm, age)*1.35)*0.75))
        pc, cc, fc = (macro_split(target, workout=is_workout, weight=weight_kg))
        st.write(f"**{T('remaining')}**: {int(target - totals['kcal'])} {T('kcal')}, P {max(0,pc-int(totals['protein']))}g / C {max(0,cc-int(totals['carbs']))}g / F {max(0,fc-int(totals['fat']))}g")
        fig = px.pie(values=[max(totals['protein'],1)*4, max(totals['carbs'],1)*4, max(totals['fat'],1)*9],
                     names=[T('protein'), T('carbs'), T('fat')], title=T("macros"))
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass

# ---------- WORKOUT TAB ----------
with tabs[3]:
    st.subheader(T("workout_plan"))
    # Video links
    vids = {
        "Squat":"https://www.youtube.com/watch?v=aclHkVaku9U",
        "Romanian Deadlift":"https://www.youtube.com/watch?v=Op6A_C2lH_0",
        "Walking Lunge":"https://www.youtube.com/watch?v=wrwwXE_x-pQ",
        "Bench Press":"https://www.youtube.com/watch?v=gRVjAtPip0Y",
        "Barbell Row":"https://www.youtube.com/watch?v=YSx8umUqZ1I",
        "Shoulder Press":"https://www.youtube.com/watch?v=qEwKCR5JCog",
        "Plank":"https://www.youtube.com/watch?v=BQu26ABuVS0",
        "Leg Raise":"https://www.youtube.com/watch?v=JB2oyawG9KI",
        "Deadlift":"https://www.youtube.com/watch?v=op9kVnSso6Q",
        "Pull-up":"https://www.youtube.com/watch?v=eGo4IYlbE5g",
        "Lat Pulldown":"https://www.youtube.com/watch?v=CAwf7n6Luuc",
        "Incline DB Press":"https://www.youtube.com/watch?v=8iPEnn-ltC8",
        "Seated Row":"https://www.youtube.com/watch?v=GZbfZ033f74",
        "Leg Press":"https://www.youtube.com/watch?v=IZxyjW7MPJQ",
        "Leg Curl":"https://www.youtube.com/watch?v=1Tq3QdYUuHs",
        "Calf Raise":"https://www.youtube.com/watch?v=YMmgqO8Jo-k",
        "Side Plank":"https://www.youtube.com/watch?v=K2VljzCC16g",
        "Heavy Bag Boxing":"https://www.youtube.com/watch?v=6k1k3JtGkC4",
        "Treadmill Incline":"https://www.youtube.com/watch?v=2I3ne9CwCWA"
    }

    def show_ex(name, sets_reps):
        url = vids.get(name)
        st.markdown(f"- **{name}** — {sets_reps}  |  [{T('video_guide')}]({url})")

    if plan_type == "full_body":
        st.write("**Mon / Wed / Fri — Full Body**")
        show_ex("Squat","4x8")
        show_ex("Romanian Deadlift","3x10")
        show_ex("Walking Lunge","2x20")
        show_ex("Bench Press","4x8")
        show_ex("Barbell Row","4x10")
        show_ex("Shoulder Press","3x12")
        show_ex("Plank","3 sets (max)")
        show_ex("Leg Raise","3x15")
        show_ex("Treadmill Incline","10 min finisher")
        st.subheader(T("rest_cardio"))
        st.write("**Tue / Thu / Sat — Cardio + Core**")
        show_ex("Treadmill Incline","30–40 min")
        show_ex("Heavy Bag Boxing","3 x 3 min (1 min rest)")
        show_ex("Side Plank","3x30s/side")

    elif plan_type == "ppl":
        st.write("**Mon: Push**")
        show_ex("Bench Press","4x8")
        show_ex("Incline DB Press","3x10")
        show_ex("Shoulder Press","3x12")
        st.write("**Wed: Pull**")
        show_ex("Barbell Row","4x8")
        show_ex("Lat Pulldown","3x12")
        show_ex("Seated Row","3x12")
        st.write("**Fri: Legs**")
        show_ex("Squat","4x8")
        show_ex("Leg Press","4x12")
        show_ex("Leg Curl","3x12")
        show_ex("Calf Raise","3x15")
        st.subheader(T("rest_cardio")); show_ex("Treadmill Incline","30–40 min"); show_ex("Side Plank","3x30s/side")

    elif plan_type == "upper_lower":
        st.write("**Mon & Thu: Upper**")
        show_ex("Bench Press","4x8"); show_ex("Incline DB Press","3x10"); show_ex("Barbell Row","4x10"); show_ex("Shoulder Press","3x12")
        st.write("**Tue & Fri: Lower**")
        show_ex("Squat","4x8"); show_ex("Romanian Deadlift","3x10"); show_ex("Leg Press","4x12"); show_ex("Calf Raise","3x15")
        st.subheader(T("rest_cardio")); show_ex("Treadmill Incline","30–40 min")

    else:  # cardio_core
        st.write("**Mon / Wed / Fri — Cardio & Core**")
        show_ex("Treadmill Incline","40–50 min")
        show_ex("Heavy Bag Boxing","5 x 2 min (1 min rest)")
        show_ex("Plank","3 x max")
        show_ex("Leg Raise","3x15")
        st.subheader("**Tue / Thu — Strength (Light)**")
        show_ex("Squat","3x8"); show_ex("Bench Press","3x8"); show_ex("Barbell Row","3x10")

# ---------- PROGRESS TAB ----------
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
            conn.commit()
            st.success("Saved")
    wdf = pd.read_sql_query("SELECT dt, weight FROM weights WHERE username=?", conn, params=(user,))
    if not wdf.empty:
        wdf["dt"] = pd.to_datetime(wdf["dt"])
        fig = px.line(wdf, x="dt", y="weight", markers=True, title="Weight Trend")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No weight data yet / Kilo kaydı yok")
