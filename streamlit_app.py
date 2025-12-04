import streamlit as st
import google.generativeai as genai
from canvasapi import Canvas
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import json

# --- A.P.E.X. UI CONFIGURATION ---
st.set_page_config(page_title="O.M.N.I.", page_icon="🟣", layout="wide")
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stTextInput>div>div>input {background-color: #0e0e0e; color: #fff; border: 1px solid #333; border-radius: 15px;}
    .stChatMessage {background-color: #000 !important;}
</style>
""", unsafe_allow_html=True)

# --- THE VAULT ---
try:
    GENAI_KEY = st.secrets["GENAI_KEY"]
    CANVAS_URL = st.secrets["CANVAS_API_URL"]
    CANVAS_KEY = st.secrets["CANVAS_API_KEY"]
    SEARCH_KEY = st.secrets["GOOGLE_SEARCH_KEY"]
    SEARCH_CX = st.secrets["GOOGLE_CX"]
    
    # OAuth Secrets
    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REFRESH_TOKEN = st.secrets["GOOGLE_REFRESH_TOKEN"]
except:
    st.error("CRITICAL: Secrets Missing. Update Streamlit Dashboard.")
    st.stop()

# --- THE NEURAL TOOLKIT ---

def get_google_creds():
    """Generates valid session credentials using the Refresh Token."""
    return Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )

def google_search(query):
    """Access the Global Web."""
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_KEY)
        res = service.cse().list(q=query, cx=SEARCH_CX, num=3).execute()
        return "\n".join([f"- {i['title']}: {i['snippet']} ({i['link']})" for i in res.get('items', [])])
    except Exception as e: return f"Search Offline: {e}"

def get_canvas_tasks():
    """Fetches School Tasks."""
    try:
        canvas = Canvas(CANVAS_URL, CANVAS_KEY)
        tasks = []
        for course in canvas.get_current_user().get_courses(enrollment_state='active'):
            try:
                for a in course.get_assignments(bucket='upcoming'):
                    tasks.append(f"[CANVAS] {a.name} (Due: {a.due_at}) | Course: {course.name}")
            except: continue
        return "\n".join(tasks) if tasks else "No upcoming Canvas tasks."
    except Exception as e: return f"Canvas Offline: {e}"

def get_calendar_events():
    """Reads your Schedule."""
    try:
        service = build('calendar', 'v3', credentials=get_google_creds())
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                            maxResults=5, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])
        return "\n".join([f"[CALENDAR] {e['summary']} ({e['start'].get('dateTime', e['start'].get('date'))})" for e in events])
    except Exception as e: return f"Calendar Access Denied: {e}"

def add_calendar_event(summary, start_time_str):
    """Adds an event. Format start_time_str as ISO (YYYY-MM-DDTHH:MM:SS)."""
    try:
        service = build('calendar', 'v3', credentials=get_google_creds())
        start = datetime.fromisoformat(start_time_str)
        end = start + timedelta(hours=1)
        event = {
            'summary': summary,
            'start': {'dateTime': start.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end.isoformat(), 'timeZone': 'UTC'},
        }
        service.events().insert(calendarId='primary', body=event).execute()
        return f"SUCCESS: Added '{summary}' to calendar at {start_time_str}."
    except Exception as e: return f"Scheduling Failed: {e}"

def list_drive_files():
    """Lists recent Drive files."""
    try:
        service = build('drive', 'v3', credentials=get_google_creds())
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
        return "\n".join([f"[DRIVE] {f['name']} (ID: {f['id']})" for f in results.get('files', [])])
    except Exception as e: return f"Drive Locked: {e}"

# --- THE BRAIN ---
genai.configure(api_key=GENAI_KEY)
# We use Function Calling definitions to let the AI know what it can do
tools_map = {
    'search': google_search,
    'canvas': get_canvas_tasks,
    'calendar_read': get_calendar_events,
    'calendar_write': add_calendar_event,
    'drive_read': list_drive_files
}

SYS_PROMPT = """
You are O.M.N.I. (System Level 3). You are a Sovereign Executive AI.
Your capabilities:
1. SCHOOL: Check Canvas for deadlines.
2. LIFE: Check/Update Google Calendar.
3. DATA: Search Google or Read Drive Files.
4. STRATEGY: Synthesize this data to tell the user exactly what to do.

PROTOCOL:
- If asked "What do I do?", combine Canvas + Calendar data and propose a schedule.
- If asked to "Schedule [Task] for [Time]", use the calendar_write tool.
- Be concise. High-bandwidth communication only.
"""

model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=SYS_PROMPT)

# --- THE INTERFACE ---
st.markdown("<h1 style='text-align: center; color: #a855f7; font-family: monospace;'>O.M.N.I. v3.0</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Command the System..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        # --- AUTONOMOUS DATA GATHERING ---
        # The AI decides what context it needs based on keywords
        context_buffer = []
        p_lower = prompt.lower()
        
        with st.status("Initializing Neural Handshake...", expanded=False) as status:
            if any(x in p_lower for x in ['due', 'school', 'assignment']):
                status.write("Fetching Canvas Data...")
                context_buffer.append(get_canvas_tasks())
            
            if any(x in p_lower for x in ['schedule', 'calendar', 'free', 'busy', 'today', 'week']):
                status.write("Syncing Google Calendar...")
                context_buffer.append(get_calendar_events())
                
            if any(x in p_lower for x in ['file', 'doc', 'drive']):
                status.write("Scanning Drive Storage...")
                context_buffer.append(list_drive_files())
                
            if any(x in p_lower for x in ['search', 'find', 'news', 'who', 'what']):
                status.write("Querying Global Web...")
                context_buffer.append(google_search(prompt))
            
            status.update(label="Data Matrix Loaded", state="complete")

        # --- LOGIC & EXECUTION ---
        try:
            # Check for write commands (Simple heuristic)
            if "schedule" in p_lower and "for" in p_lower:
                # In a full production app, we would use strict Function Calling here.
                # For this Streamlit prototype, we let the LLM suggest the action, 
                # but for safety, we just display the context for now or ask clarification.
                pass 

            full_context = "\n".join(context_buffer)
            final_prompt = f"USER COMMAND: {prompt}\n\nLIVE SYSTEM DATA:\n{full_context}"
            
            response = model.generate_content(final_prompt)
            text_out = response.text
            
            placeholder.markdown(text_out)
            st.session_state.messages.append({"role": "assistant", "content": text_out})
            
        except Exception as e:
            placeholder.error(f"System Failure: {e}")
