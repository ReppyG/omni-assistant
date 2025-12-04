import streamlit as st
import google.generativeai as genai
from canvasapi import Canvas
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import requests
import time
import random
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
    st.error("CRITICAL: Secrets Missing.")
    st.stop()

# --- ASTRA VISUAL CORE (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Righteous&display=swap');
    
    /* Main Background */
    .stApp { background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }
    
    /* ASTRA Gradient Text */
    .gradient-text {
        background: linear-gradient(90deg, #FF1493, #FF69B4, #DA70D6, #BA55D3, #9370DB, #8A7FD4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Righteous', cursive;
        font-weight: bold;
    }
    
    /* Input Field */
    .stTextInput>div>div>input {
        background-color: rgba(30, 30, 30, 0.8); 
        color: #fff; 
        border: 1px solid rgba(138, 127, 212, 0.3); 
        border-radius: 20px;
        padding: 10px 20px;
    }
    
    /* HUD Container (Slide Down) */
    .hud-trigger { position: fixed; top: 0; left: 0; width: 100%; height: 10px; z-index: 9999; }
    .hud-container {
        position: fixed; top: -140px; left: 0; width: 100%; height: 120px;
        display: flex; justify-content: center; align-items: center; gap: 20px;
        background: rgba(0, 0, 0, 0.9);
        border-bottom: 1px solid rgba(138, 127, 212, 0.2);
        backdrop-filter: blur(20px);
        transition: top 0.4s ease-out;
        z-index: 9998;
    }
    .hud-trigger:hover + .hud-container, .hud-container:hover { top: 0; }
    
    /* HUD Cards */
    .hud-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 10px 15px;
        min-width: 200px;
        display: flex; flex-direction: column;
        border-left: 4px solid;
    }
    
    /* Specific Card Colors */
    .card-pink { border-left-color: #FF69B4; } /* Event */
    .card-red { border-left-color: #FF4500; } /* Urgent */
    .card-blue { border-left-color: #00BFFF; } /* Weather */
    
    .hud-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #aaa; margin-bottom: 4px; }
    .hud-main { font-family: 'Righteous', cursive; font-size: 1.1rem; color: #fff; }
    .hud-sub { font-size: 0.8rem; color: #888; }

    /* Hide Streamlit Elements */
    #MainMenu, footer, header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- STARTUP ANIMATION (Session State) ---
if "astra_loaded" not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("""
        <div style="height: 100vh; display: flex; justify-content: center; align-items: center; background: black;">
            <h1 class="gradient-text" style="font-size: 6rem; animation: pulse 2s infinite;">ASTRA</h1>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(2.0) # Fake loading for effect
    placeholder.empty()
    st.session_state.astra_loaded = True

# --- LOGIC CORES (Backend) ---

@st.cache_data(ttl=600)
def get_weather():
    try:
        loc_formatted = LOCATION.replace(" ", "+")
        r = requests.get(f"https://wttr.in/{loc_formatted}?format=%C+%t")
        return r.text.strip() if "Unknown" not in r.text else "Offline"
    except: return "Offline"

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
        # Parse time
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
                        if days < 2: # Urgent if due in < 48 hours
                            return {"title": a.name, "due": "Today" if days < 1 else "Tomorrow"}
            except: continue
        return None
    except: return None

# --- DEEP RESEARCH (Option A Logic) ---
def scrape_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        text = " ".join(soup.get_text().split())
        return text[:5000]
    except: return "Access Denied"

def deep_search(query):
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        items = res.get('items', [])
        if not items: return "No results."
        
        # Scrape Top Result
        top_url = items[0]['link']
        scraped_content = scrape_text(top_url)
        
        return f"SOURCE: {top_url}\nCONTENT: {scraped_content}\n\nOTHER LINKS: " + ", ".join([i['link'] for i in items[1:]])
    except Exception as e: return f"Search Error: {e}"

# --- RENDER HUD ---
event = get_next_event()
task = get_urgent_task()
wx = get_weather()

hud_html = ""
# Pink Card (Event)
if event:
    hud_html += f"""
    <div class="hud-card card-pink">
        <div class="hud-title">UPCOMING EVENT</div>
        <div class="hud-main">{event['title']}</div>
        <div class="hud-sub">{event['time']} • {event['mins']} mins away</div>
    </div>"""

# Red Card (Task)
if task:
    hud_html += f"""
    <div class="hud-card card-red">
        <div class="hud-title">URGENT ASSIGNMENT</div>
        <div class="hud-main">{task['title']}</div>
        <div class="hud-sub">Due {task['due']}</div>
    </div>"""

# Blue Card (Weather)
hud_html += f"""
<div class="hud-card card-blue">
    <div class="hud-title">ENVIRONMENT</div>
    <div class="hud-main">{wx}</div>
    <div class="hud-sub">{LOCATION}</div>
</div>"""

st.markdown(f"""<div class="hud-trigger"></div><div class="hud-container">{hud_html}</div>""", unsafe_allow_html=True)

# --- MAIN UI ---
st.markdown('<h1 class="gradient-text" style="font-size: 4rem; text-align: center; margin-top: 10vh;">ASTRA</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #888;">AI • CANVAS • GOOGLE • DEEP RESEARCH</p>', unsafe_allow_html=True)

# --- CHAT LOOP ---
genai.configure(api_key=GENAI_KEY)
SYS_PROMPT = """You are ASTRA. Your personality is sleek, efficient, and intelligent.
You have access to the user's Gradebook, Calendar, and the Deep Web.
If asked to research, use the DEEP SEARCH tool.
Be concise."""

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat
for m in st.session_state.messages:
    if m["role"] == "user":
        st.markdown(f"""<div style="text-align: right; margin: 10px;"><span style="background: linear-gradient(90deg, #FF1493, #8A7FD4); padding: 10px 15px; border-radius: 15px; color: white;">{m["content"]}</span></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="text-align: left; margin: 10px;"><span style="background: #222; padding: 10px 15px; border-radius: 15px; color: #eee; border: 1px solid #333;">{m["content"]}</span></div>""", unsafe_allow_html=True)

# Input
if prompt := st.chat_input("Ask ASTRA anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun() # Instant UI update

# Response Generation (Running after rerun to keep UI snappy)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    
    with st.spinner("Processing..."):
        # Context Gathering
        ctx = ""
        if "search" in last_prompt.lower() or "research" in last_prompt.lower():
            ctx += f"\nDEEP SEARCH RESULT: {deep_search(last_prompt)}"
        
        # Call Gemini
        try:
            model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=SYS_PROMPT)
            response = model.generate_content(f"CONTEXT: {ctx}\nQUERY: {last_prompt}")
            reply = response.text
        except:
            reply = "Connection severed."

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
