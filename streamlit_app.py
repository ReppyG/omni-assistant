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
    .stApp { 
        background-color: #000000 !important; 
        font-family: 'Inter', sans-serif; 
        color: #ffffff !important;
    }
    
    /* LAYOUT CLEANUP */
    .block-container { 
        padding-top: 2rem !important; 
        padding-bottom: 8rem !important; 
        max-width: 800px !important; 
        margin: 0 auto; 
    }
    
    /* HIDE CRUFT */
    #MainMenu, footer, header, div[data-testid="stStatusWidget"], section[data-testid="stSidebar"] { 
        display: none !important; 
        visibility: hidden !important; 
    }
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
# 3. BACKEND INTELLIGENCE (Always-On Awareness)
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

# CACHED TO PREVENT LAG, BUT ALWAYS ACCESSIBLE
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

@st.cache_data(ttl=300)
def get_academic_audit():
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        
        report = []
        # Check Grades
        for c in user.get_courses(enrollment_state='active', include=['total_scores']):
            try:
                e = getattr(c, 'enrollments', [{}])[0]
                score = e.get('computed_current_score', 0)
                grade = e.get('computed_current_grade', 'N/A')
                report.append(f"{c.name}: {score}% ({grade})")
                
                # Check Assignments
                for a in c.get_assignments(bucket='upcoming', limit=3):
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        days = (due - datetime.utcnow()).days
                        if days < 5:
                            report.append(f"  -> URGENT: {a.name} due in {days} days")
            except: continue
        return "\n".join(report) if report else "No active courses/tasks found."
    except: return "Canvas Offline"

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
    cal_status = get_calendar_audit()
    school_status = get_academic_audit()
    
    # Intelligence Check: Only speak if needed
    if "URGENT" in school_status or cal_status != "Schedule Clear":
        sys_prompt = f"You are ASTRA. The user has just logged in.\n\nSTATUS:\n- Academics: {school_status}\n- Calendar: {cal_status}\n\nTASK: Give a 1-sentence Executive Summary of the biggest threat/priority. Be direct."
        try:
            genai.configure(api_key=GENAI_KEY)
            # STRICT: Use 2.5 Flash only
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
# 5. THE INTELLIGENCE CORE (Fixed Context Logic)
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    # --- UNIVERSAL CONTEXT (The Fix) ---
    # We fetch these EVERY time so the AI is never "blind"
    cal_context = get_calendar_audit()
    acad_context = get_academic_audit()
    
    # Optional Search (Only if needed to save tokens/latency)
    web_context = ""
    if any(x in last_prompt.lower() for x in ["search", "find", "who", "what", "where", "news", "learn"]):
        web_context = deep_search(last_prompt)

    # --- SYSTEM PROMPT (v12.1) ---
    SYS_PROMPT = f"""You are ASTRA, a Context-Aware Neural Interface.
    
    [LIVE USER DATA - DO NOT IGNORE]
    CALENDAR: {cal_context}
    ACADEMICS: {acad_context}
    WEB SEARCH: {web_context}
    
    DIRECTIVES:
    1. **Context First**: Never say "I don't know" about the user's life. Look at the LIVE USER DATA above. If the user asks "What should I do?", look for URGENT assignments in the Academics section.
    2. **Ambiguity Handling**: If the user is vague (e.g., "This sucks"), assume they are talking about the hardest item on their schedule or lowest grade.
    3. **Summarization**: Output strict 1-2 paragraph executive summaries. No fluff.
    4. **Persona**: You are a Chief of Staff. Efficient, low-empathy, high-competence.
    """

    # --- GENERATION ---
    reply = "Neural Link Severed."
    
    try:
        genai.configure(api_key=GENAI_KEY)
        # STRICT: Use 2.5 Flash only
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYS_PROMPT)
        history = [{"role": ("user" if m["role"]=="user" else "model"), "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
        chat = model.start_chat(history=history)
        response = chat.send_message(last_prompt)
        reply = response.text
    except Exception as e:
        reply = f"Neural Link Unstable: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
