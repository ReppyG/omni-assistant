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

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONFIGURATION & SETUP
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="ASTRA",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

# ═══════════════════════════════════════════════════════════════════════════════
# 2. VISUAL CORE (The Void - Fixes Applied)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Knewave&family=Inter:wght@400;500;600&display=swap');
    
    /* GLOBAL THEME */
    .stApp { 
        background-color: #000000 !important; 
        font-family: 'Inter', sans-serif; 
        color: #ffffff !important;
    }
    
    /* LAYOUT CLEANUP */
    .block-container { 
        padding-top: 2rem !important; 
        padding-bottom: 8rem !important; /* Increased for input spacing */
        max-width: 800px !important; 
        margin: 0 auto; 
    }
    
    /* HIDE ALL UI CRUFT */
    #MainMenu, footer, header, div[data-testid="stStatusWidget"], section[data-testid="stSidebar"] { 
        display: none !important; 
        visibility: hidden !important; 
    }
    .stSpinner { display: none !important; }
    
    /* Ensure Markdown is Visible */
    .stMarkdown {
        width: 100% !important;
    }
    
    /* LOGO */
    .astra-logo {
        font-family: 'Knewave', system-ui;
        font-size: 6rem;
        text-align: center;
        margin-top: 15vh;
        margin-bottom: 2rem;
        letter-spacing: 0.05em;
        background: linear-gradient(135deg, #FF69B4 20%, #A020F0 80%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 20px rgba(160, 32, 240, 0.3));
        animation: pulse 4s infinite;
    }
    
    @keyframes pulse { 0% { opacity: 0.9; } 50% { opacity: 1; } 100% { opacity: 0.9; } }

    /* CHAT BUBBLES - High Visibility */
    .user-msg {
        background-color: #27272a !important;
        color: #ffffff !important;
        padding: 12px 20px;
        border-radius: 20px 20px 4px 20px;
        margin-left: auto; 
        width: fit-content; 
        max-width: 80%;
        margin-bottom: 12px; 
        font-weight: 500;
        display: block;
        position: relative;
    }
    
    .ai-msg {
        background: linear-gradient(135deg, #3B0764, #581C87) !important;
        color: #ffffff !important;
        padding: 14px 24px;
        border-radius: 20px 20px 24px 4px;
        margin-right: auto; 
        width: fit-content; 
        max-width: 85%;
        margin-bottom: 12px; 
        box-shadow: 0 4px 15px rgba(88, 28, 135, 0.15);
        line-height: 1.5;
        display: block;
        position: relative;
    }

    /* INPUT */
    .stChatInput { 
        position: fixed; 
        bottom: 30px; 
        left: 50%; 
        transform: translateX(-50%); 
        width: 100%; 
        max-width: 800px; 
        z-index: 10000; /* Ensure on top */
    }
    .stChatInput > div { 
        background-color: #121212 !important; 
        border: 1px solid #27272a !important; 
        border-radius: 30px !important; 
    }
    .stChatInput input { 
        color: #ffffff !important; 
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. THE PROACTIVE BRAIN (Hidden Logic)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=900)
def get_weather():
    try:
        r = requests.get(f"https://wttr.in/{LOCATION.replace(' ', '+')}?format=%t+%C")
        if "Unknown" in r.text: return "Offline"
        return r.text.strip()
    except: return "Offline"

def get_google_creds():
    return Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

def get_calendar_audit():
    """Scans calendar for conflicts and density."""
    try:
        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.utcnow().isoformat() + 'Z'
        events = service.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute().get('items', [])
        
        if not events: return "Schedule Clear"
        
        # Analyze density
        today_events = [e for e in events if e['start'].get('dateTime', '').startswith(datetime.now().strftime('%Y-%m-%d'))]
        if len(today_events) > 4: return f"HIGH LOAD: {len(today_events)} events today."
        
        # Next event
        next_ev = events[0]
        summary = next_ev.get('summary', 'Event')
        start = next_ev['start'].get('dateTime', next_ev['start'].get('date'))
        return f"Next: {summary} at {start}"
    except: return "Calendar Link Severed"

def get_academic_audit():
    """Scans for grade drops and imminent deadlines."""
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        
        alerts = []
        
        # Check Deadlines (Next 48 Hours)
        for c in user.get_courses(enrollment_state='active'):
            try:
                for a in c.get_assignments(bucket='upcoming', limit=5):
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        if (due - datetime.utcnow()).days < 2:
                            alerts.append(f"URGENT: {a.name} due in {(due - datetime.utcnow()).seconds//3600}h")
            except: continue
            
        # Check Grades (Identify Struggling Classes)
        grades = []
        for c in user.get_courses(enrollment_state='active', include=['total_scores']):
            try:
                e = getattr(c, 'enrollments', [{}])[0]
                score = e.get('computed_current_score', 100)
                if score and score < 75:
                    grades.append(f"RISK: {c.name} is at {score}%")
            except: continue
            
        if not alerts and not grades: return "Academic Status: Optimal"
        return " | ".join(alerts[:3] + grades[:2])
    except: return "Canvas Link Severed"

def deep_search(query):
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        return "\n".join([f"- {i['title']}: {i['snippet']}" for i in res.get('items', [])])
    except: return "Search Offline"

# ═══════════════════════════════════════════════════════════════════════════════
# 4. STARTUP SEQUENCE (The "Agent" Logic)
# ═══════════════════════════════════════════════════════════════════════════════

if "messages" not in st.session_state: st.session_state.messages = []
if "astra_init" not in st.session_state: st.session_state.astra_init = False

# --- LANDING SCREEN (Empty State) ---
if not st.session_state.messages:
    st.markdown("""
    <div style="height: 70vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
        <h1 class="astra-logo">ASTRA</h1>
    </div>
    """, unsafe_allow_html=True)

# --- PROACTIVE SCANNER (Runs Once on Boot) ---
if not st.session_state.astra_init:
    # 1. Silent Scan
    cal_status = get_calendar_audit()
    school_status = get_academic_audit()
    weather = get_weather()
    
    # 2. Decision Matrix: Does the user NEED to be alerted?
    # If there is "URGENT", "RISK", or "HIGH LOAD", the AI speaks first.
    if "URGENT" in school_status or "RISK" in school_status or "HIGH LOAD" in cal_status:
        
        sys_prompt = """You are ASTRA, a proactive executive AI.
        You have just scanned the user's data.
        
        DATA:
        - Calendar: {cal}
        - School: {school}
        - Weather: {wx}
        
        TASK:
        The user has just opened the app. 
        Do NOT say "Hello". 
        IMMEDIATELY brief them on the threat/risk detected in the data.
        Be concise, serious, and strategic. Propose a fix.
        """.format(cal=cal_status, school=school_status, wx=weather)
        
        try:
            genai.configure(api_key=GENAI_KEY)
            # Try Pro first, fallback handled if this part crashes
            model = genai.GenerativeModel('gemini-2.5-flash') 
            alert = model.generate_content(sys_prompt).text
            st.session_state.messages.append({"role": "assistant", "content": alert})
            st.rerun()
        except: pass
    
    st.session_state.astra_init = True

# ═══════════════════════════════════════════════════════════════════════════════
# 5. CHAT LOOP
# ═══════════════════════════════════════════════════════════════════════════════

# Display History
chat_container = st.container()
with chat_container:
    for m in st.session_state.messages:
        role_class = "user-msg" if m["role"] == "user" else "ai-msg"
        st.markdown(f'<div class="{role_class}">{m["content"]}</div>', unsafe_allow_html=True)

# Input
if prompt := st.chat_input("Command..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Logic
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    # --- DYNAMIC INTELLIGENCE ---
    ctx = ""
    lp = last_prompt.lower()
    
    if any(x in lp for x in ["search", "find", "who", "what", "where", "news"]):
        ctx += f"\n[SEARCH PROTOCOL]: {deep_search(last_prompt)}"
    if any(x in lp for x in ["schedule", "calendar", "busy", "free", "tomorrow", "today"]):
        ctx += f"\n[CALENDAR PROTOCOL]: {get_calendar_audit()}"
    if any(x in lp for x in ["due", "grade", "score", "assignment", "test", "exam"]):
        ctx += f"\n[ACADEMIC PROTOCOL]: {get_academic_audit()}"

    SYS_PROMPT = """You are ASTRA. Neural Interface.
    DIRECTIVES:
    1. **Efficiency**: Use minimum words for maximum impact.
    2. **Proactivity**: If schedule is heavy, suggest rescheduling.
    3. **Strategy**: If grades are low, suggest study topics.
    4. **Summarization**: ALWAYS condense findings into 1-2 paragraph summaries. No walls of text.
    """

    # --- FALLBACK GENERATION LOGIC ---
    models_to_try = ['gemini-2.5-pro', 'gemini-2.5-flash']
    reply = "Neural Link Severed."
    
    for model_name in models_to_try:
        try:
            genai.configure(api_key=GENAI_KEY)
            model = genai.GenerativeModel(model_name, system_instruction=SYS_PROMPT)
            
            history = [{"role": ("user" if m["role"]=="user" else "model"), "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
            chat = model.start_chat(history=history)
            
            response = chat.send_message(f"LIVE DATA STREAM: {ctx}\n\nUSER INPUT: {last_prompt}")
            reply = response.text
            break # Success, exit loop
        except Exception as e:
            if "429" in str(e):
                continue # Try next model
            reply = f"Neural Link Unstable: {str(e)}"
            break # Non-quota error, stop trying

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
    
