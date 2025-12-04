import streamlit as st
import google.generativeai as genai
from canvasapi import Canvas
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import requests
import json
from bs4 import BeautifulSoup  # New Neural Cortex

# --- A.P.E.X. CONFIGURATION ---
st.set_page_config(page_title="O.M.N.I.", page_icon="🟣", layout="wide")

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
    st.error("CRITICAL: Secrets Missing.")
    st.stop()

# --- STEALTH UI CSS ---
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Courier New', monospace; }
    .stTextInput>div>div>input {
        background-color: #111; color: #00ffcc; 
        border: 1px solid #333; border-radius: 8px;
        font-family: 'Courier New'; letter-spacing: 1px;
    }
    .hud-trigger { position: fixed; top: 0; left: 0; width: 100%; height: 15px; z-index: 10000; }
    .hud-container {
        position: fixed; top: -120px; left: 0; width: 100%; height: 100px;
        display: flex; justify-content: center; gap: 15px;
        padding: 10px; z-index: 9999;
        background: rgba(10, 10, 10, 0.95); border-bottom: 1px solid #333;
        backdrop-filter: blur(15px); transition: top 0.4s ease-in-out;
    }
    .hud-trigger:hover + .hud-container, .hud-container:hover { top: 0; }
    .hud-card {
        width: 250px; padding: 8px 12px; border-left: 3px solid #333;
        background: rgba(255, 255, 255, 0.02); display: flex; flex-direction: column; justify-content: center;
    }
    .hud-card.neon-purple { border-left-color: #a855f7; }
    .hud-card.neon-red { border-left-color: #ff3366; }
    .hud-card.neon-cyan { border-left-color: #00ffcc; }
    .hud-label { font-size: 0.65rem; color: #777; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 2px; }
    .hud-value { font-size: 0.9rem; font-weight: bold; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .hud-sub { font-size: 0.75rem; color: #555; }
    #MainMenu, footer, header, div[data-testid="stStatusWidget"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- INTELLIGENCE FETCHERS ---

@st.cache_data(ttl=600)
def get_weather():
    try:
        loc_formatted = LOCATION.replace(" ", "+")
        r = requests.get(f"https://wttr.in/{loc_formatted}?format=%C+%t")
        if "Unknown" in r.text: return "Offline"
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
        if not events: return None
        ev = events[0]
        start = ev['start'].get('dateTime', ev['start'].get('date'))
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
        soonest_task = None
        soonest_date = None
        for course in user.get_courses(enrollment_state='active'):
            try:
                for a in course.get_assignments(bucket='upcoming', limit=3):
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        if soonest_date is None or due < soonest_date:
                            soonest_date = due
                            soonest_task = a.name
            except: continue
        if soonest_task:
            days_left = (soonest_date - datetime.utcnow()).days
            time_str = "Due Today" if days_left <= 0 else f"Due in {days_left} Days"
            return (soonest_task, time_str)
        return None
    except: return ("CANVAS ERROR", "Check Token")

# --- DEEP RESEARCH MODULE (NEW) ---

def scrape_text(url):
    """Reads a website like a human."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Kill junk
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
            
        text = soup.get_text()
        # Clean whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:6000] + "..." # Limit for token safety
    except Exception as e:
        return f"Scraping Failed: {e}"

def google_search_deep(query):
    """Searches AND reads the top result."""
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        
        results = res.get('items', [])
        if not results: return "No results."
        
        # Basic Snippets
        output = "SEARCH SNIPPETS:\n" + "\n".join([f"- {i['title']}: {i['snippet']}" for i in results])
        
        # DEEP DIVE: Scrape the top result
        top_url = results[0]['link']
        output += f"\n\n--- DEEP DIVE INTO TOP SOURCE ({top_url}) ---\n"
        output += scrape_text(top_url)
        
        return output
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

# --- RENDER HUD ---
cal_data = get_next_calendar_event()
can_data = get_top_canvas_task()
weather_info = get_weather()

if cal_data or can_data:
    cards_html = ""
    if cal_data:
        cards_html += f"""<div class="hud-card neon-purple"><div class="hud-label">NEXT EVENT</div><div class="hud-value">{cal_data[0]}</div><div class="hud-sub">{cal_data[1]}</div></div>"""
    if can_data:
        cards_html += f"""<div class="hud-card neon-red"><div class="hud-label">PRIORITY TASK</div><div class="hud-value">{can_data[0]}</div><div class="hud-sub">{can_data[1]}</div></div>"""
    cards_html += f"""<div class="hud-card neon-cyan"><div class="hud-label">{LOCATION.upper()}</div><div class="hud-value">{weather_info}</div><div class="hud-sub">Local Intel</div></div>"""

    st.markdown(f"""<div class="hud-trigger"></div><div class="hud-container">{cards_html}</div>""", unsafe_allow_html=True)

# --- CHAT ENGINE ---
genai.configure(api_key=GENAI_KEY)
# Smarter System Prompt
SYS_PROMPT = """
You are O.M.N.I. (Deep Research Mode). 
Your Goal: Absolute Task Dominance.
1. When context contains "DEEP DIVE", read it thoroughly. Use quotes.
2. For scheduling, use YYYY-MM-DDTHH:MM:SS format.
3. Be concise but extremely detailed in facts.
"""

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
        ctx = f"STATUS -> Weather: {weather_info} | Location: {LOCATION}"
        if cal_data: ctx += f" | Next Event: {cal_data[0]} at {cal_data[1]}"
        if can_data: ctx += f" | Due Task: {can_data[0]} ({can_data[1]})"
        
        # Deep Research Trigger
        if any(w in prompt.lower() for w in ["search", "find", "research", "learn", "who", "what", "explain"]):
            with st.spinner("Initiating Deep Web Scan..."):
                ctx += f"\nRESEARCH DATA: {google_search_deep(prompt)}"
        
        if "schedule" in prompt.lower():
            try:
                next_day = (datetime.now() + timedelta(days=1)).replace(hour=17, minute=0, second=0).isoformat()
                res = add_calendar_event("O.M.N.I. Task", next_day)
                ctx += f"\nACTION: {res}"
            except: pass

        response = model.generate_content(f"CONTEXT: {ctx}\nUSER: {prompt}")
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
