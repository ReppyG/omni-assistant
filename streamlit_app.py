import streamlit as st
import google.generativeai as genai
from canvasapi import Canvas
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import requests
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
import re
import json
import string
import io

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(page_title="ASTRA", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

# --- THE VAULT ---
try:
    GENAI_KEY = st.secrets["GENAI_KEY"]
    CANVAS_URL = st.secrets["CANVAS_API_URL"]
    CANVAS_KEY = st.secrets["CANVAS_API_KEY"]
    SEARCH_KEY = st.secrets["GOOGLE_SEARCH_KEY"]
    SEARCH_CX = st.secrets["GOOGLE_CX"]
    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REFRESH_TOKEN = st.secrets["GOOGLE_REFRESH_TOKEN"]
    LOCATION = st.secrets.get("WEATHER_LOCATION", "New York, NY")
except:
    st.error("CRITICAL: Secrets Missing. Please update Streamlit Secrets.")
    st.stop()

# --- 2. CSS VISUAL CORE (Knewave & Slate) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Knewave&family=Inter:wght@400;500;600&display=swap');
    
    .stApp { background-color: #020617; font-family: 'Inter', sans-serif; color: #e2e8f0; }
    .block-container { padding-top: 0rem !important; padding-bottom: 5rem !important; max-width: 100% !important; }
    .stSpinner { display: none !important; }
    
    /* ANIMATIONS */
    @keyframes gradientMove { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    
    /* ASTRA LOGO */
    .astra-logo {
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
        background-size: 200% 200%;
        animation: gradientMove 4s ease infinite;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Knewave', system-ui;
        letter-spacing: 0.05em;
        filter: drop-shadow(0 0 15px rgba(192, 132, 252, 0.3));
    }

    /* HUD */
    .hud-wrapper { position: fixed; top: 0; left: 0; right: 0; height: 20px; z-index: 9999; }
    .hud-bar {
        position: fixed; top: -140px; left: 0; right: 0;
        background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(16px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding: 16px 32px; display: flex; justify-content: center; gap: 4rem;
        transition: top 0.4s cubic-bezier(0.16, 1, 0.3, 1); z-index: 9998;
    }
    .hud-wrapper:hover .hud-bar, .hud-bar:hover { top: 0; }
    
    .hud-item { display: flex; align-items: center; gap: 16px; min-width: 200px; }
    .icon-box { width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: rgba(30, 41, 59, 0.5); font-size: 1.2rem; }

    /* CHAT BUBBLES */
    .user-msg { background-color: #334155; color: #f1f5f9; padding: 14px 24px; border-radius: 20px 20px 0 20px; margin-left: auto; max-width: 85%; width: fit-content; margin-bottom: 16px; }
    .ai-msg { background-color: #0f172a; color: #e2e8f0; padding: 14px 24px; border-radius: 20px 20px 20px 0; margin-right: auto; max-width: 85%; width: fit-content; border: 1px solid #1e293b; margin-bottom: 16px; }

    /* INPUT */
    .stTextInput input { background-color: rgba(30, 41, 59, 0.8) !important; color: white !important; border-radius: 14px !important; border: 1px solid rgba(99, 102, 241, 0.2) !important; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #1e293b; }
    
    /* FOCUS MODE OVERLAY */
    .focus-overlay {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: #000; z-index: 10000; display: flex; justify-content: center; align-items: center;
        color: white; font-family: 'Inter'; flex-direction: column;
    }
    
    /* HIDE CRUFT */
    #MainMenu, footer, header, div[data-testid="stStatusWidget"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. BACKEND INTELLIGENCE ---

@st.cache_data(ttl=900)
def get_weather():
    try:
        r = requests.get(f"https://wttr.in/{LOCATION.replace(' ', '+')}?format=%t+%C")
        if "Unknown" in r.text: return ("--", "Offline")
        parts = r.text.strip().split(" ", 1)
        return (parts[0], parts[1] if len(parts) > 1 else "")
    except: return ("--", "Offline")

def get_google_creds():
    return Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

def get_next_event():
    try:
        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.utcnow().isoformat() + 'Z'
        events = service.events().list(calendarId='primary', timeMin=now, maxResults=3, singleEvents=True, orderBy='startTime').execute().get('items', [])
        if not events: return None
        ev = events[0]
        start = ev['start'].get('dateTime', ev['start'].get('date'))
        dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        delta = (dt - datetime.now(dt.tzinfo)).total_seconds() / 60
        time_str = dt.strftime("%I:%M %p")
        return {"title": ev['summary'], "time": time_str, "mins": int(delta), "all": events}
    except: return None

def get_urgent_task():
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        tasks = []
        for c in user.get_courses(enrollment_state='active'):
            try:
                for a in c.get_assignments(bucket='upcoming', limit=3):
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        if (due - datetime.utcnow()).days < 3:
                            tasks.append({"title": a.name, "due": "Today" if (due-datetime.utcnow()).days < 1 else "Soon"})
            except: continue
        return {"top": tasks[0], "all": tasks} if tasks else None
    except: return None

def scrape_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style", "nav", "footer"]): s.extract()
        return " ".join(soup.get_text().split())[:5000]
    except: return None

def deep_search(query):
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        items = res.get('items', [])
        for item in items[:2]: # Try top 2
            content = scrape_text(item['link'])
            if content: return f"SOURCE: {item['link']}\nCONTENT: {content}"
        return "Firewall blocked deep extraction."
    except: return "Search Offline"

def get_grade_analytics_df():
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        data = []
        for c in user.get_courses(enrollment_state='active', include=['total_scores']):
            try:
                e = getattr(c, 'enrollments', [{}])[0]
                data.append({"Course": c.name, "Score": e.get('computed_current_score', 0)})
            except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- 4. STATE MANAGEMENT ---
if "messages" not in st.session_state: st.session_state.messages = []
if "mode" not in st.session_state: st.session_state.mode = "Standard"
if "focus_active" not in st.session_state: st.session_state.focus_active = False
if "focus_end" not in st.session_state: st.session_state.focus_end = None

# --- 5. SIDEBAR: THE NEUROMODULES (Upgrade 11, 21, 61, 70, 71, 72, 73, 80) ---
with st.sidebar:
    st.markdown('<h2 class="astra-logo" style="font-size: 2rem;">ASTRA</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # MODE SWITCHER (Upgrade 3, 4, 5, 29)
    st.subheader("🧠 Cognitive Mode")
    mode = st.selectbox("Select Personality", ["Standard", "Socratic (Questions Only)", "Debate Partner", "ELI5 (Simple)", "Code Debugger", "Pirate"])
    st.session_state.mode = mode
    
    # FOCUS ENGINE (Upgrade 34, 36)
    st.markdown("---")
    st.subheader("⏳ Focus Engine")
    focus_min = st.slider("Pomodoro Minutes", 5, 60, 25)
    if st.button("ACTIVATE FOCUS"):
        st.session_state.focus_active = True
        st.session_state.focus_end = datetime.now() + timedelta(minutes=focus_min)
        st.rerun()
        
    # UTILITIES (Upgrade 61, 70, 21)
    st.markdown("---")
    with st.expander("🛠️ Utilities"):
        tab1, tab2, tab3 = st.tabs(["Calc", "Pass", "GPA"])
        with tab1:
            eq = st.text_input("Equation", key="calc_in")
            if eq: 
                try: st.code(str(eval(eq))) 
                except: st.error("Error")
        with tab2:
            if st.button("Gen Password"):
                chars = string.ascii_letters + string.digits + "!@#$%"
                st.code("".join(random.choice(chars) for i in range(12)))
        with tab3:
            st.caption("GPA Simulator")
            current = st.number_input("Current GPA", 0.0, 4.0, 3.5)
            credits = st.number_input("Total Credits", 0, 120, 30)
            new_grade = st.number_input("New Class Grade (0-4)", 0.0, 4.0, 4.0)
            if st.button("Simulate"):
                new_gpa = ((current * credits) + (new_grade * 3)) / (credits + 3)
                st.success(f"New GPA: {new_gpa:.2f}")

    # SECURITY (Upgrade 72, 73)
    st.markdown("---")
    with st.expander("🛡️ Security"):
        if st.button("Export Chat JSON"):
            json_str = json.dumps(st.session_state.messages, indent=2)
            st.download_button("Download", json_str, "astra_memory.json", "application/json")
        if st.button("SELF DESTRUCT (Clear Memory)", type="primary"):
            st.session_state.messages = []
            st.rerun()

# --- 6. FOCUS MODE OVERLAY ---
if st.session_state.focus_active:
    now = datetime.now()
    if now < st.session_state.focus_end:
        remaining = st.session_state.focus_end - now
        mins, secs = divmod(remaining.seconds, 60)
        st.markdown(f"""
        <div class="focus-overlay">
            <h1 class="astra-logo" style="font-size: 10rem;">FOCUS</h1>
            <h2 style="font-size: 5rem;">{mins:02d}:{secs:02d}</h2>
            <p>Do not break the seal.</p>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(1)
        st.rerun()
    else:
        st.session_state.focus_active = False
        st.rerun()

# --- 7. HUD ---
event = get_next_event()
task = get_urgent_task()
temp, cond = get_weather()

hud_html = '<div class="hud-wrapper"><div class="hud-bar">'
if event:
    hud_html += f"""<div class="hud-item"><div class="icon-box" style="color:#a855f7">📅</div><div><div style="color:white;font-weight:600">{event['title']}</div><div style="color:#94a3b8;font-size:0.75rem">{event['time']} • {event['mins']}m</div></div></div>"""
if task:
    t = task['top']
    hud_html += f"""<div class="hud-item"><div class="icon-box" style="color:#f43f5e">⚡</div><div><div style="color:white;font-weight:600">{t['title']}</div><div style="color:#94a3b8;font-size:0.75rem">Due {t['due']}</div></div></div>"""
hud_html += f"""<div class="hud-item"><div class="icon-box" style="color:#38bdf8">🌤</div><div><div style="color:white;font-weight:600">{temp}</div><div style="color:#94a3b8;font-size:0.75rem">{LOCATION}</div></div></div></div></div>"""
st.markdown(hud_html, unsafe_allow_html=True)

# --- 8. MAIN UI ---
if not st.session_state.messages:
    st.markdown("""
    <div style="height: 70vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
        <h1 class="astra-logo" style="font-size: 8rem; margin: 0;">ASTRA</h1>
        <p style="color: #64748b; margin-top: 10px; font-family: monospace; letter-spacing: 2px;">SINGULARITY CORE V9.0</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for m in st.session_state.messages:
        role_class = "user-msg" if m["role"] == "user" else "ai-msg"
        st.markdown(f'<div class="{role_class}">{m["content"]}</div>', unsafe_allow_html=True)

# --- 9. INPUT & INTELLIGENCE ---
col1, col2 = st.columns([6, 1])
with col1:
    prompt = st.chat_input("Command the System...")
with col2:
    # Voice Input (Upgrade 51)
    audio_val = st.audio_input("Voice")

if audio_val:
    # Basic simulation of transcription if API not available, or use Gemini Multimodal later
    st.toast("Voice received. Processing...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    # BRAIN CONFIG
    genai.configure(api_key=GENAI_KEY)
    
    # MODE SWITCHING LOGIC
    persona = "You are ASTRA, a helpful AI."
    if st.session_state.mode == "Socratic (Questions Only)": persona = "You are Socrates. NEVER give the answer. Only ask guiding questions to lead the user to the truth."
    elif st.session_state.mode == "Debate Partner": persona = "You are a ruthless debater. Take the exact opposite stance of the user and provide 3 counter-arguments."
    elif st.session_state.mode == "ELI5 (Simple)": persona = "Explain everything as if the user is 5 years old. Use simple analogies."
    elif st.session_state.mode == "Code Debugger": persona = "You are a Senior Engineer. Fix the code provided, explain the bug, and optimize it."
    elif st.session_state.mode == "Pirate": persona = "You are a space pirate captain. Use appropriate slang."
    
    SYS_PROMPT = f"""{persona}
    
    TOOLS & CONTEXT:
    1. **Deep Research**: If asked to find info, USE the [DEEP WEB DATA].
    2. **Academic Advisor**: If asked about grades, use [ACADEMIC ANALYTICS].
    3. **Briefing**: Keep it crisp.
    4. **Flashcards**: If asked for flashcards, output a CSV format block.
    5. **Bibliography**: If asked for citations, format in APA7.
    """
    
    ctx = ""
    # Smart Router (Upgrade 8, 22, 23, 24, 26, 49, 50, 89, 90)
    if any(x in last_prompt.lower() for x in ["search", "find", "research", "news", "learn", "define", "buy", "best"]):
        ctx += f"\n[DEEP WEB DATA]: {deep_search(last_prompt)}"
    
    if any(x in last_prompt.lower() for x in ["grade", "gpa", "score", "pass", "fail", "doing"]):
        df = get_grade_analytics_df()
        ctx += f"\n[ACADEMIC ANALYTICS]: \n{df.to_string() if not df.empty else 'No data'}"
        
    if any(x in last_prompt.lower() for x in ["schedule", "calendar", "event", "busy"]):
        ev = get_next_event()
        if ev: ctx += f"\n[CALENDAR]: " + str(ev['all'])

    # Build History
    chat_history = []
    for msg in st.session_state.messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})

    try:
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=SYS_PROMPT)
        chat = model.start_chat(history=chat_history)
        
        final_input = f"SYSTEM CONTEXT: {ctx}\n\nUSER QUERY: {last_prompt}" if ctx else last_prompt
        response = chat.send_message(final_input)
        reply = response.text
        
    except Exception as e:
        reply = f"Cognitive Failure: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
