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

# --- CSS TRANSLATION (React/Tailwind -> CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Righteous&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* GLOBAL RESET & BACKGROUND */
    .stApp {
        background-color: #000000;
        font-family: 'Inter', sans-serif;
    }
    
    /* REMOVE STREAMLIT PADDING */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* ANIMATIONS */
    @keyframes gradientMove {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes slideDown {
        from { transform: translateY(-100%); }
        to { transform: translateY(0); }
    }

    /* GRADIENT TEXT (Matches React) */
    .gradient-text {
        background: linear-gradient(90deg, #FF1493, #FF69B4, #DA70D6, #BA55D3, #9370DB, #8A7FD4);
        background-size: 200% 200%;
        animation: gradientMove 3s ease infinite;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-family: 'Righteous', cursive;
    }

    /* HUD BAR STYLING */
    .hud-wrapper {
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 10px; /* Trigger zone */
        z-index: 9999;
        transition: height 0.3s;
    }
    
    .hud-wrapper:hover {
        height: auto;
    }

    .hud-bar {
        position: fixed;
        top: -100px; /* Hidden by default */
        left: 0; right: 0;
        background: rgba(0, 0, 0, 0.9);
        backdrop-filter: blur(24px); /* backdrop-blur-xl */
        border-bottom: 1px solid rgba(168, 85, 247, 0.2); /* purple-500/20 */
        padding: 12px 24px;
        display: flex;
        justify-content: center;
        gap: 2rem;
        transition: top 0.5s ease-out;
        z-index: 9998;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
    }

    /* Slide Logic: When trigger is hovered, or HUD itself is hovered */
    .hud-wrapper:hover .hud-bar, .hud-bar:hover {
        top: 0;
    }

    .hud-item {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        max-width: 300px;
    }

    .icon-box {
        padding: 8px;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
    }

    /* CHAT BUBBLES */
    .user-msg {
        background: linear-gradient(to right, #db2777, #9333ea); /* pink-600 to purple-600 */
        color: white;
        padding: 12px 24px;
        border-radius: 16px 16px 0 16px;
        margin-left: auto;
        margin-bottom: 16px;
        max-width: 80%;
        width: fit-content;
        font-weight: 500;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .ai-msg {
        background-color: #1f2937; /* gray-800 */
        color: #f3f4f6; /* gray-100 */
        padding: 12px 24px;
        border-radius: 16px 16px 16px 0;
        margin-right: auto;
        margin-bottom: 16px;
        max-width: 80%;
        width: fit-content;
        border: 1px solid #374151;
    }

    /* INPUT OVERRIDE */
    .stTextInput > div > div {
        background: transparent !important;
        border: none !important;
    }
    
    .stTextInput input {
        background-color: rgba(31, 41, 55, 0.8) !important; /* gray-800/80 */
        color: white !important;
        border: 1px solid rgba(168, 85, 247, 0.3) !important; /* purple-500/30 */
        border-radius: 9999px !important;
        padding: 16px 24px !important;
    }
    
    .stTextInput input:focus {
        border-color: #a855f7 !important; /* purple-500 */
        box-shadow: 0 0 0 1px #a855f7 !important;
    }

    /* Hide standard UI elements */
    #MainMenu, footer, header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- BACKEND LOGIC (Python Brain) ---

@st.cache_data(ttl=600)
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
        events = service.events().list(calendarId='primary', timeMin=now, maxResults=1, singleEvents=True, orderBy='startTime').execute().get('items', [])
        if not events: return None
        ev = events[0]
        start = ev['start'].get('dateTime', ev['start'].get('date'))
        dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        delta = (dt - datetime.now(dt.tzinfo)).total_seconds() / 60
        time_str = dt.strftime("%I:%M %p")
        return {"title": ev['summary'], "time": time_str, "mins": int(delta)}
    except: return None

def get_urgent_task():
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        user = canvas.get_current_user()
        for course in user.get_courses(enrollment_state='active'):
            try:
                for a in course.get_assignments(bucket='upcoming', limit=3):
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        days = (due - datetime.utcnow()).days
                        if days < 2: 
                            return {"title": a.name, "due": "Today" if days < 1 else "Tomorrow", "priority": "High"}
            except: continue
        return None
    except: return None

# Deep Search Logic
def scrape_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return " ".join(soup.get_text().split())[:4000]
    except: return "Access Denied"

def deep_search(query):
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        items = res.get('items', [])
        if not items: return "No results."
        top_url = items[0]['link']
        return f"SOURCE: {top_url}\nCONTENT: {scrape_text(top_url)}"
    except Exception as e: return f"Search Error: {e}"

# --- STATE MANAGEMENT ---
if "astra_loaded" not in st.session_state:
    st.session_state.astra_loaded = False
    st.session_state.messages = []

# --- LOADING SCREEN (Replicating React useEffect) ---
if not st.session_state.astra_loaded:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("""
        <div style="height: 100vh; display: flex; justify-content: center; align-items: center; flex-direction: column;">
            <h1 class="gradient-text" style="font-size: 8rem; margin: 0; letter-spacing: 0.1em;">ASTRA</h1>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(2.5) # The 2500ms timeout from React
    placeholder.empty()
    st.session_state.astra_loaded = True
    st.rerun()

# --- MAIN APP ---

# 1. Fetch Data
event = get_next_event()
task = get_urgent_task()
temp, cond = get_weather()

# 2. Build HUD HTML (Matching React Structure)
hud_html = '<div class="hud-wrapper"><div class="hud-bar">'

# Event Card
if event:
    hud_html += f"""
    <div class="hud-item">
        <div class="icon-box" style="background: linear-gradient(135deg, rgba(236, 72, 153, 0.2), rgba(168, 85, 247, 0.2));">
            <span style="font-size: 1.2rem;">📅</span>
        </div>
        <div>
            <div style="color: white; font-size: 0.875rem; font-weight: 500;">{event['title']}</div>
            <div style="color: #9ca3af; font-size: 0.75rem;">{event['time']} • {event['mins']} mins away</div>
        </div>
    </div>
    """

# Task Card
if task:
    hud_html += f"""
    <div class="hud-item">
        <div class="icon-box" style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(249, 115, 22, 0.2));">
            <span style="font-size: 1.2rem;">⚠️</span>
        </div>
        <div>
            <div style="color: white; font-size: 0.875rem; font-weight: 500;">{task['title']}</div>
            <div style="color: #9ca3af; font-size: 0.75rem;">Due {task['due']}</div>
        </div>
    </div>
    """

# Weather Card
hud_html += f"""
<div class="hud-item">
    <div class="icon-box" style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(6, 182, 212, 0.2));">
        <span style="font-size: 1.2rem;">☁️</span>
    </div>
    <div>
        <div style="color: white; font-size: 0.875rem; font-weight: 500;">{temp} • {cond}</div>
        <div style="color: #9ca3af; font-size: 0.75rem;">{LOCATION}</div>
    </div>
</div>
"""
hud_html += '</div></div>'
st.markdown(hud_html, unsafe_allow_html=True)

# 3. Main Content Area (Messages or Empty State)
if not st.session_state.messages:
    # Empty State (Replicating React "Your AI assistant is ready")
    st.markdown("""
    <div style="height: 70vh; display: flex; justify-content: center; align-items: center; flex-direction: column;">
        <h1 class="gradient-text" style="font-size: 5rem; margin-bottom: 1rem;">ASTRA</h1>
        <p style="color: #9ca3af; font-size: 1.125rem;">Your AI assistant is ready</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Chat History
    for m in st.session_state.messages:
        if m["role"] == "user":
            st.markdown(f'<div class="user-msg">{m["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-msg">{m["content"]}</div>', unsafe_allow_html=True)

# 4. Input Area (Using Streamlit's chat_input but heavily styled via CSS above)
if prompt := st.chat_input("Ask ASTRA anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# 5. AI Response Generation
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    with st.spinner("Processing..."):
        genai.configure(api_key=GENAI_KEY)
        SYS_PROMPT = "You are ASTRA. Your personality is sleek, efficient, and intelligent. Be concise."
        
        ctx = ""
        # Check Research Trigger
        if any(x in last_prompt.lower() for x in ["search", "find", "research"]):
            ctx += f"\nDEEP SEARCH: {deep_search(last_prompt)}"
            
        try:
            model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=SYS_PROMPT)
            response = model.generate_content(f"CONTEXT: {ctx}\nQUERY: {last_prompt}")
            reply = response.text
        except:
            reply = "I'm ASTRA, your AI assistant. Connection error - please try again."

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
