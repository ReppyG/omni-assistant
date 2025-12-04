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

# --- ASTRA CONFIGURATION ---
st.set_page_config(page_title="ASTRA", page_icon="✨", layout="wide")

# --- THE VAULT (Secrets) ---
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

# --- CSS STYLING (Knewave & Premium Dark) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Knewave&family=Inter:wght@400;500;600&display=swap');
    
    /* GLOBAL RESET & BACKGROUND */
    .stApp {
        background-color: #020617; /* Slate 950 */
        font-family: 'Inter', sans-serif;
        color: #e2e8f0;
    }
    
    /* REMOVE STREAMLIT PADDING */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 5rem !important;
        max-width: 100% !important;
    }
    
    .stSpinner { display: none !important; }

    /* ANIMATIONS */
    @keyframes gradientMove {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes pulseGlow {
        0% { text-shadow: 0 0 10px rgba(168, 85, 247, 0.5); }
        50% { text-shadow: 0 0 20px rgba(168, 85, 247, 0.8), 0 0 30px rgba(236, 72, 153, 0.6); }
        100% { text-shadow: 0 0 10px rgba(168, 85, 247, 0.5); }
    }

    /* THE ASTRA LOGO (Knewave) */
    .astra-logo {
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6); /* Indigo -> Purple -> Pink */
        background-size: 200% 200%;
        animation: gradientMove 4s ease infinite;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-family: 'Knewave', system-ui; /* USER REQUESTED FONT */
        font-weight: 400;
        font-style: normal;
        letter-spacing: 0.05em;
        filter: drop-shadow(0 0 15px rgba(192, 132, 252, 0.3));
    }

    /* HUD BAR STYLING */
    .hud-wrapper {
        position: fixed; top: 0; left: 0; right: 0;
        height: 20px; z-index: 9999;
    }
    
    .hud-bar {
        position: fixed; top: -140px; left: 0; right: 0;
        background: rgba(15, 23, 42, 0.9); /* Slate 900 */
        backdrop-filter: blur(16px); 
        border-bottom: 1px solid rgba(255, 255, 255, 0.05); 
        padding: 16px 32px;
        display: flex; justify-content: center; gap: 4rem;
        transition: top 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        z-index: 9998;
    }

    .hud-wrapper:hover .hud-bar, .hud-bar:hover { top: 0; }

    .hud-item {
        display: flex; align-items: center; gap: 16px;
        min-width: 200px;
    }

    .icon-box {
        width: 42px; height: 42px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255,255,255,0.08);
        font-size: 1.2rem;
    }

    /* CHAT BUBBLES */
    .user-msg {
        background-color: #334155; /* Slate 700 */
        color: #f1f5f9;
        padding: 14px 24px;
        border-radius: 20px 20px 0 20px;
        margin-left: auto;
        margin-bottom: 16px;
        max-width: 85%;
        width: fit-content;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .ai-msg {
        background-color: #0f172a; /* Slate 900 */
        color: #e2e8f0; 
        padding: 14px 24px;
        border-radius: 20px 20px 20px 0;
        margin-right: auto;
        margin-bottom: 16px;
        max-width: 85%;
        width: fit-content;
        border: 1px solid #1e293b;
    }

    /* INPUT OVERRIDE */
    .stTextInput > div > div { background: transparent !important; border: none !important; }
    .stTextInput input {
        background-color: rgba(30, 41, 59, 0.8) !important;
        color: white !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 14px !important;
        padding: 18px 24px !important;
        font-size: 1rem;
    }
    .stTextInput input:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 1px #818cf8 !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- ADVANCED INTELLIGENCE MODULES ---

@st.cache_data(ttl=900)
def get_weather():
    try:
        loc_formatted = LOCATION.replace(" ", "+")
        r = requests.get(f"https://wttr.in/{loc_formatted}?format=%t+%C")
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
        
        # Return next immediate event for HUD
        ev = events[0]
        start = ev['start'].get('dateTime', ev['start'].get('date'))
        dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        delta = (dt - datetime.now(dt.tzinfo)).total_seconds() / 60
        time_str = dt.strftime("%I:%M %p")
        
        return {
            "title": ev['summary'], "time": time_str, "mins": int(delta),
            "all_events": events # Pass full list for briefing
        }
    except: return None

def get_urgent_task():
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        
        urgent_tasks = []
        
        for course in user.get_courses(enrollment_state='active'):
            try:
                for a in course.get_assignments(bucket='upcoming', limit=5):
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        days = (due - datetime.utcnow()).days
                        if days < 3: # Collect all tasks due in next 3 days
                            urgent_tasks.append({"title": a.name, "course": course.name, "due": "Today" if days < 1 else "Tomorrow" if days < 2 else f"In {days} days"})
            except: continue
            
        if not urgent_tasks: return None
        
        # Return top task for HUD, list for Briefing
        return {"top": urgent_tasks[0], "all": urgent_tasks}
    except: return None

def scrape_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style", "nav", "footer", "aside"]): s.extract()
        text = " ".join(soup.get_text().split())
        return text[:6000]
    except: return None 

def deep_search(query):
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        items = res.get('items', [])
        if not items: return "No results."
        
        # Robust Scraping: Try results until one works
        for item in items:
            content = scrape_text(item['link'])
            if content and len(content) > 200: 
                return f"SOURCE: {item['link']}\nTITLE: {item['title']}\nCONTENT: {content}"
        
        return "Search completed. Firewall blocked extraction."
    except Exception as e: return f"Search Error: {e}"

def get_grade_analytics_df():
    """Generates a Pandas DataFrame of grades for advanced AI analysis"""
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        courses = user.get_courses(enrollment_state='active', include=['total_scores', 'term'])
        
        data = []
        for c in courses:
            try:
                enrollment = getattr(c, 'enrollments', [{}])[0]
                score = enrollment.get('computed_current_score', 0)
                if score is None: score = 0
                grade = enrollment.get('computed_current_grade', 'N/A')
                data.append({"Course": c.name, "Score": score, "Letter": grade})
            except: continue
            
        if not data: return "No grade data available."
        
        df = pd.DataFrame(data)
        stats = f"Average Score: {df['Score'].mean():.1f}% | Lowest: {df['Score'].min()}%"
        return f"{df.to_string()}\n\nSTATISTICS:\n{stats}"
    except: return "Grade Access Denied"

# --- STATE MANAGEMENT ---
if "astra_state" not in st.session_state:
    st.session_state.astra_state = "BOOT" 
    st.session_state.messages = []
    st.session_state.briefing_generated = False

# --- HUD ---
event = get_next_event()
task = get_urgent_task()
temp, cond = get_weather()

hud_html = '<div class="hud-wrapper"><div class="hud-bar">'

if event:
    hud_html += f"""
    <div class="hud-item">
        <div class="icon-box" style="color: #a855f7;">📅</div>
        <div>
            <div style="color: white; font-size: 0.875rem; font-weight: 600;">{event['title']}</div>
            <div style="color: #94a3b8; font-size: 0.75rem;">{event['time']} • {event['mins']}m away</div>
        </div>
    </div>"""

if task and task.get('top'):
    t = task['top']
    hud_html += f"""
    <div class="hud-item">
        <div class="icon-box" style="color: #f43f5e;">⚡</div>
        <div>
            <div style="color: white; font-size: 0.875rem; font-weight: 600;">{t['title']}</div>
            <div style="color: #94a3b8; font-size: 0.75rem;">Due {t['due']}</div>
        </div>
    </div>"""

hud_html += f"""
<div class="hud-item">
    <div class="icon-box" style="color: #38bdf8;">🌤</div>
    <div>
        <div style="color: white; font-size: 0.875rem; font-weight: 600;">{temp}</div>
        <div style="color: #94a3b8; font-size: 0.75rem;">{LOCATION}</div>
    </div>
</div>
</div></div>"""

st.markdown(hud_html, unsafe_allow_html=True)

# --- STARTUP LOGIC ---
if st.session_state.astra_state == "BOOT":
    placeholder = st.empty()
    with placeholder.container():
        # KNEWAVE ANIMATION
        st.markdown("""
        <div style="height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <h1 class="astra-logo" style="font-size: 8rem; margin: 0;">ASTRA</h1>
            <p style="color: #64748b; margin-top: 10px; font-family: monospace; letter-spacing: 2px;">NEURAL INTERFACE V8.5</p>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(2.0)
    placeholder.empty()
    st.session_state.astra_state = "READY"
    st.rerun()

# --- AUTONOMOUS BRIEFING GENERATION ---
if st.session_state.astra_state == "READY" and not st.session_state.briefing_generated:
    with st.spinner("Compiling Morning Briefing..."):
        grade_data = get_grade_analytics_df()
        calendar_context = "No events."
        if event and 'all_events' in event:
            calendar_context = ", ".join([f"{e['summary']} at {e['start'].get('dateTime', 'All Day')}" for e in event['all_events']])
        
        task_context = "No urgent tasks."
        if task and 'all' in task:
            task_context = ", ".join([f"{t['title']} ({t['due']})" for t in task['all']])
            
        briefing_prompt = f"""
        Generate a 'Strategic Briefing' for the user.
        CONTEXT:
        - Weather: {temp}, {cond} in {LOCATION}
        - Upcoming: {calendar_context}
        - Urgent: {task_context}
        - Academics: {grade_data}
        
        INSTRUCTIONS:
        1. Be concise, strategic, and executive.
        2. Highlight the single most critical item.
        3. Do not list everything; summarize the state of affairs.
        4. End with "Ready for deployment."
        """
        
        try:
            genai.configure(api_key=GENAI_KEY)
            model = genai.GenerativeModel('gemini-2.5-pro')
            resp = model.generate_content(briefing_prompt)
            briefing_text = resp.text
            st.session_state.messages.append({"role": "assistant", "content": briefing_text})
            st.session_state.briefing_generated = True
            st.rerun()
        except:
            st.session_state.briefing_generated = True

# --- MAIN CHAT INTERFACE ---

# 1. Render Messages
for m in st.session_state.messages:
    if m["role"] == "user":
        st.markdown(f'<div class="user-msg">{m["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="ai-msg">{m["content"]}</div>', unsafe_allow_html=True)

# 2. Input
if prompt := st.chat_input("Command the System..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# 3. Intelligence Engine (v8.5 Upgrade)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    # SYSTEM PROMPT V8.5 (The "Architect" Logic)
    SYS_PROMPT = """You are ASTRA, a Hyper-Intelligent Academic Architect.
    
    CORE MODES:
    1. **Agent Oracle**: If asked "what if" about grades, calculate the math precisely.
    2. **Study Architect**: If asked to "help me study" or "focus", breakdown the user's request into a step-by-step tactical plan (Topic -> Resources -> Practice).
    3. **Deep Research**: If asked to find info, USE the provided context. Do not halllucinate.
    4. **Professor Mode**: If asked to "quiz me", ask ONE difficult question at a time. Wait for the answer.
    
    STYLE:
    - Precise, Futuristic, Efficient.
    - No fluff. Pure signal.
    """
    
    ctx = ""
    
    # Study Architect Trigger
    if any(x in last_prompt.lower() for x in ["study", "plan", "focus", "help me learn"]):
        ctx += "\n[MODE: STUDY ARCHITECT ACTIVE] - Break this topic down into a tactical learning plan."

    # Smart Router
    if any(x in last_prompt.lower() for x in ["search", "find", "research", "news", "learn", "define"]):
        ctx += f"\n[DEEP WEB DATA]: {deep_search(last_prompt)}"
    
    if any(x in last_prompt.lower() for x in ["grade", "gpa", "score", "pass", "fail", "doing"]):
        ctx += f"\n[ACADEMIC ANALYTICS]: {get_grade_analytics_df()}"
        
    if any(x in last_prompt.lower() for x in ["schedule", "calendar", "event", "busy"]):
        ev = get_next_event()
        if ev and 'all_events' in ev:
            ctx += f"\n[CALENDAR]: " + str(ev['all_events'])

    # Build History
    chat_history = []
    for msg in st.session_state.messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})

    try:
        genai.configure(api_key=GENAI_KEY)
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=SYS_PROMPT)
        chat = model.start_chat(history=chat_history)
        
        final_input = f"SYSTEM CONTEXT: {ctx}\n\nUSER QUERY: {last_prompt}" if ctx else last_prompt
        response = chat.send_message(final_input)
        reply = response.text
        
    except Exception as e:
        reply = f"System Alert: Cognitive Link Unstable ({str(e)})."

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
