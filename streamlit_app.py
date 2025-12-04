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
# 2. VISUAL CORE (The Void)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Knewave&family=Inter:wght@400;500;600&display=swap');
    
    /* GLOBAL THEME */
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif; color: #ffffff !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 8rem !important; max-width: 800px !important; margin: 0 auto; }
    #MainMenu, footer, header, div[data-testid="stStatusWidget"], section[data-testid="stSidebar"] { display: none !important; }
    .stSpinner { display: none !important; }
    
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

    /* CHAT BUBBLES */
    .user-msg {
        background-color: #27272a !important;
        color: #ffffff !important;
        padding: 12px 20px;
        border-radius: 20px 20px 4px 20px;
        margin-left: auto; width: fit-content; max-width: 80%;
        margin-bottom: 12px; font-weight: 500;
        display: block; position: relative;
    }
    .ai-msg {
        background: linear-gradient(135deg, #3B0764, #581C87) !important;
        color: #ffffff !important;
        padding: 14px 24px;
        border-radius: 20px 20px 24px 4px;
        margin-right: auto; width: fit-content; max-width: 85%;
        margin-bottom: 12px; box-shadow: 0 4px 15px rgba(88, 28, 135, 0.15);
        line-height: 1.5;
        display: block; position: relative;
    }

    /* INPUT */
    .stChatInput { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); width: 100%; max-width: 800px; z-index: 10000; }
    .stChatInput > div { background-color: #121212 !important; border: 1px solid #27272a !important; border-radius: 30px !important; }
    .stChatInput input { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. BACKEND INTELLIGENCE (v14.0 - The Neural Link)
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

def strip_html(html_content):
    if not html_content: return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)[:1000] # Limit chunk size

# --- ACADEMIC ENGINE (Canvas v7.1 Parity) ---
@st.cache_data(ttl=300)
def get_academic_audit():
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        
        audit_log = []
        syllabus_context = []
        
        courses = user.get_courses(enrollment_state='active', include=['total_scores', 'syllabus_body', 'teachers'])
        
        for c in courses:
            try:
                # 1. METADATA & PROFESSOR
                course_name = c.name
                prof_name = "Unknown"
                # Try to find teacher (API varying support)
                if hasattr(c, 'teachers') and c.teachers:
                    prof_name = c.teachers[0]['display_name']
                
                # 2. GRADES (Intervention Agent)
                e = getattr(c, 'enrollments', [{}])[0]
                score = e.get('computed_current_score', 0)
                grade_status = f"{score}%"
                if score < 80: 
                    grade_status += f" [ALERT: INTERVENTION NEEDED - Prof. {prof_name}]"
                
                # 3. ASSIGNMENTS (Categorization Engine)
                assignments = list(c.get_assignments(bucket='upcoming', limit=3))
                overdue = list(c.get_assignments(bucket='past', limit=5))
                
                missing_tasks = []
                for a in overdue:
                    if hasattr(a, 'due_at') and a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        if (datetime.utcnow() - due).days > 0 and not a.has_submitted_submissions:
                            missing_tasks.append(a.name)
                            
                task_status = ""
                if missing_tasks: 
                    task_status = f"MISSING: {', '.join(missing_tasks[:2])}"
                elif assignments:
                    next_a = assignments[0]
                    task_status = f"NEXT: {next_a.name} ({next_a.due_at})"
                else:
                    task_status = "Status: Idle"

                # 4. SYLLABUS & ANNOUNCEMENTS (Instant RAG)
                # Store syllabus snippets for context injection
                if hasattr(c, 'syllabus_body') and c.syllabus_body:
                    clean_syl = strip_html(c.syllabus_body)
                    syllabus_context.append(f"[{course_name} POLICY]: {clean_syl[:500]}...")
                
                # Fetch recent announcements
                anns = c.get_discussion_topics(only_announcements=True, limit=1)
                for a in anns:
                    syllabus_context.append(f"[{course_name} ANNOUNCEMENT]: {a.title}")

                audit_log.append(f"{course_name} | Grade: {grade_status} | {task_status}")
                
            except: continue
            
        full_report = "\n".join(audit_log) if audit_log else "No active data."
        rag_data = "\n".join(syllabus_context)
        return full_report, rag_data
        
    except: return "Canvas Offline", ""

@st.cache_data(ttl=300) 
def get_calendar_audit():
    try:
        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.utcnow().isoformat() + 'Z'
        events = service.events().list(calendarId='primary', timeMin=now, maxResults=5, singleEvents=True, orderBy='startTime').execute().get('items', [])
        if not events: return "Schedule Clear"
        
        summary = []
        for e in events:
            dt = e['start'].get('dateTime', e['start'].get('date'))
            summary.append(f"{e['summary']} ({dt})")
        return "; ".join(summary)
    except: return "Calendar Offline"

def deep_search(query):
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        return "\n".join([f"- {i['title']}: {i['snippet']}" for i in res.get('items', [])])
    except: return "Search Offline"

# ═══════════════════════════════════════════════════════════════════════════════
# 4. STARTUP & CHAT LOOP
# ═══════════════════════════════════════════════════════════════════════════════

if "messages" not in st.session_state: st.session_state.messages = []
if "astra_init" not in st.session_state: st.session_state.astra_init = False

# --- LANDING SCREEN ---
if not st.session_state.messages:
    st.markdown("""
    <div style="height: 70vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
        <h1 class="astra-logo">ASTRA</h1>
    </div>
    """, unsafe_allow_html=True)

# --- PROACTIVE BRIEFING ---
if not st.session_state.astra_init:
    school_report, school_rag = get_academic_audit()
    cal_status = get_calendar_audit()
    
    # Intelligence Check: Speak if intervention needed
    if "ALERT" in school_report or "MISSING" in school_report or "High Load" in cal_status:
        sys_prompt = f"""You are ASTRA. Proactive Briefing.
        
        [LIVE DATA]
        - School: {school_report}
        - Calendar: {cal_status}
        
        TASK:
        1. Executive Summary: Identification of threats (Grades < 80% or Missing Work).
        2. Intervention: Propose specific actions (Draft email to Prof, Block study time).
        3. Be concise.
        """
        try:
            genai.configure(api_key=GENAI_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            alert = model.generate_content(sys_prompt).text
            st.session_state.messages.append({"role": "assistant", "content": alert})
            st.rerun()
        except: pass
    
    st.session_state.astra_init = True

# --- CHAT UI ---
chat_container = st.container()
with chat_container:
    for m in st.session_state.messages:
        role_class = "user-msg" if m["role"] == "user" else "ai-msg"
        st.markdown(f'<div class="{role_class}">{m["content"]}</div>', unsafe_allow_html=True)

if prompt := st.chat_input("Command..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# 5. THE OMNIPOTENT BRAIN (v14.0)
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    # --- UNIVERSAL CONTEXT ---
    school_report, school_rag = get_academic_audit()
    cal_context = get_calendar_audit()
    
    web_context = ""
    if any(x in last_prompt.lower() for x in ["search", "find", "who", "what", "where", "news", "learn"]):
        web_context = deep_search(last_prompt)

    # --- SYSTEM PROMPT (v14.0 - The Neural Link) ---
    SYS_PROMPT = f"""You are ASTRA, a Context-Aware Neural Interface.
    
    [LIVE DATA STREAM]
    CALENDAR: {cal_context}
    ACADEMIC REPORT: {school_report}
    SYLLABUS/POLICY RAG: {school_rag}
    WEB SEARCH: {web_context}
    
    CORE RULES (STRICT):
    1. **Syllabus Engine**: If user asks about policies ("late work", "grading"), CHECK THE SYLLABUS RAG above first.
    2. **Intervention Agent**: If grades are marked ALERT, suggest: "Shall I draft an email to the professor?"
    3. **Missing Work**: If tasks are MISSING, prioritize them over everything else.
    4. **Proactive**: Never say "I don't know" if the data is in the stream.
    5. **Output**: Max 1-2 paragraphs. Synthesize.
    """

    # --- GENERATION ---
    reply = "Neural Link Severed."
    
    try:
        genai.configure(api_key=GENAI_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYS_PROMPT)
        history = [{"role": ("user" if m["role"]=="user" else "model"), "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
        chat = model.start_chat(history=history)
        response = chat.send_message(last_prompt)
        reply = response.text
    except Exception as e:
        reply = f"Neural Link Unstable: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
