import streamlit as st
import google.generativeai as genai
from canvasapi import Canvas
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import requests
import json

# --- A.P.E.X. UI CONFIGURATION ---
st.set_page_config(page_title="O.M.N.I. COMMAND", page_icon="🟣", layout="wide")

# CORE STYLE: Glassmorphism & Neon
st.markdown("""
<style>
    /* Global Reset */
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Courier New', monospace; }
    
    /* Input Field - Stealth Mode */
    .stTextInput>div>div>input {
        background-color: #111; color: #00ffcc; 
        border: 1px solid #333; border-radius: 8px;
        font-family: 'Courier New'; letter-spacing: 1px;
    }
    
    /* The HUD Container */
    .hud-container {
        display: flex; justify-content: space-between; gap: 10px;
        padding: 15px; margin-bottom: 20px;
        background: rgba(20, 20, 20, 0.6);
        border: 1px solid #333; border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    /* HUD Cards */
    .hud-card {
        flex: 1; padding: 10px;
        border-left: 2px solid #333;
        background: rgba(255, 255, 255, 0.03);
    }
    .hud-card.neon-purple { border-left-color: #a855f7; }
    .hud-card.neon-cyan { border-left-color: #00ffcc; }
    .hud-card.neon-red { border-left-color: #ff3366; }
    
    .hud-label { font-size: 0.7rem; color: #888; text-transform: uppercase; letter-spacing: 2px; }
    .hud-value { font-size: 1.1rem; font-weight: bold; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .hud-sub { font-size: 0.8rem; color: #666; }

    /* Hide Streamlit Cruft */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

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
except:
    st.error("CRITICAL: Secrets Missing.")
    st.stop()

# --- INTELLIGENCE FETCHERS (Cached for Speed) ---

@st.cache_data(ttl=300) # Cache for 5 mins to prevent API spam
def get_weather():
    try:
        # Simple text-based weather
        r = requests.get("https://wttr.in/?format=3")
        return r.text.strip()
    except: return "Link Offline"

def get_google_creds():
    return Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

def get_next_calendar_event():
    try:
        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.utcnow().isoformat() + 'Z'
        events = service.events().list(calendarId='primary', timeMin=now, maxResults=1, singleEvents=True, orderBy='startTime').execute().get('items', [])
        if not events: return ("NO EVENTS", "Clear Schedule")
        
        ev = events[0]
        start = ev['start'].get('dateTime', ev['start'].get('date'))
        # Simple date formatting
        try:
            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            time_str = dt.strftime("%I:%M %p")
        except: time_str = start
        return (ev['summary'], time_str)
    except: return ("AUTH ERROR", "Check Token")

def get_top_canvas_task():
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        courses = user.get_courses(enrollment_state='active')
        
        soonest_task = None
        soonest_date = None
        
        for course in courses:
            try:
                # Get assignments due in next 7 days
                assignments = course.get_assignments(bucket='upcoming', limit=3)
                for a in assignments:
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        if soonest_date is None or due < soonest_date:
                            soonest_date = due
                            soonest_task = f"{a.name}"
            except: continue
            
        if soonest_task:
            days_left = (soonest_date - datetime.utcnow()).days
            time_str = "Today" if days_left == 0 else f"In {days_left} Days"
            return (soonest_task, time_str)
        return ("ALL CLEAR", "No Assignments")
    except: return ("CANVAS ERROR", "Check Token")

# --- TOOLKIT FOR AI ---
def google_search(query):
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        return "\n".join([f"- {i['title']}: {i['snippet']}" for i in res.get('items', [])])
    except: return "Search Offline"

def add_calendar_event(summary, start_time_str):
    try:
        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)
        start = datetime.fromisoformat(start_time_str)
        end = start + timedelta(hours=1)
        event = {'summary': summary, 'start': {'dateTime': start.isoformat(), 'timeZone': 'UTC'}, 'end': {'dateTime': end.isoformat(), 'timeZone': 'UTC'}}
        service.events().insert(calendarId='primary', body=event).execute()
        return f"Scheduled: {summary}"
    except Exception as e: return f"Error: {e}"

# --- RENDER HEADS-UP DISPLAY (HUD) ---
# Fetch Data
with st.spinner("Syncing Command Center..."):
    cal_title, cal_time = get_next_calendar_event()
    can_title, can_time = get_top_canvas_task()
    weather_info = get_weather()

# Render HTML HUD
st.markdown(f"""
<div class="hud-container">
    <div class="hud-card neon-purple">
        <div class="hud-label">CALENDAR UPLINK</div>
        <div class="hud-value">{cal_title}</div>
        <div class="hud-sub">{cal_time}</div>
    </div>
    <div class="hud-card neon-red">
        <div class="hud-label">CANVAS TARGET</div>
        <div class="hud-value">{can_title}</div>
        <div class="hud-sub">{can_time}</div>
    </div>
    <div class="hud-card neon-cyan">
        <div class="hud-label">ENVIRONMENT</div>
        <div class="hud-value">{weather_info}</div>
        <div class="hud-sub">Local Sector</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- CHAT ENGINE ---
genai.configure(api_key=GENAI_KEY)
SYS_PROMPT = "You are O.M.N.I. Executive. Be concise, precise, and ruthless. Use data context."

try:
    model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=SYS_PROMPT)
except:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYS_PROMPT)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Direct the Intelligence..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        # Quick Context Grab
        ctx = f"HUD DATA -> Calendar: {cal_title} at {cal_time} | Canvas: {can_title} due {can_time} | Weather: {weather_info}"
        
        # Search if needed
        if "search" in prompt.lower() or "find" in prompt.lower():
            ctx += f"\nSEARCH DATA: {google_search(prompt)}"
        
        # Schedule if needed
        if "schedule" in prompt.lower():
            # Heuristic scheduling for simplicity in single-file
            try:
                # Default to tomorrow 5pm if fuzzy
                next_day = (datetime.now() + timedelta(days=1)).replace(hour=17, minute=0, second=0).isoformat()
                res = add_calendar_event("O.M.N.I. Task", next_day)
                ctx += f"\nACTION: {res}"
            except: pass

        response = model.generate_content(f"CONTEXT: {ctx}\nUSER: {prompt}")
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
