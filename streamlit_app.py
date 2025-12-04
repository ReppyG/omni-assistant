import streamlit as st
import google.generativeai as genai
from canvasapi import Canvas
from googleapiclient.discovery import build
from datetime import datetime

# --- A.P.E.X. CONFIGURATION ---
st.set_page_config(page_title="O.M.N.I.", page_icon="🟣", layout="wide")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stTextInput > div > div > input {
                background-color: #1a1a1a; 
                color: #ffffff; 
                border-radius: 20px;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- THE VAULT (Secrets) ---
try:
    GENAI_KEY = st.secrets["GENAI_KEY"]
    CANVAS_API_URL = st.secrets["CANVAS_API_URL"]
    CANVAS_API_KEY = st.secrets["CANVAS_API_KEY"]
    GOOGLE_SEARCH_KEY = st.secrets["GOOGLE_SEARCH_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
except Exception as e:
    st.error(f"SYSTEM ALERT: Secrets Configuration Incomplete. {e}")
    st.stop()

# --- THE TOOLKIT ---

def google_search(query):
    """Performs an Official Google Search."""
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_SEARCH_KEY)
        res = service.cse().list(q=query, cx=GOOGLE_CX, num=3).execute()
        results = []
        if 'items' in res:
            for item in res['items']:
                title = item.get('title')
                snippet = item.get('snippet')
                link = item.get('link')
                results.append(f"Title: {title}\nSnippet: {snippet}\nLink: {link}\n---")
            return "\n".join(results)
        else:
            return "No results found on Google."
    except Exception as e:
        return f"Google Search Uplink Failed: {e}"

def get_canvas_data(scope="assignments"):
    """Connects to School Canvas LMS."""
    try:
        canvas = Canvas(CANVAS_API_URL, CANVAS_API_KEY)
        user = canvas.get_current_user()
        output = []
        courses = user.get_courses(enrollment_state='active')
        for course in courses:
            try:
                assignments = course.get_assignments(bucket='upcoming')
                for a in assignments:
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        output.append(f"[Course: {course.name}] {a.name} (Due: {due.strftime('%m-%d %H:%M')})")
            except:
                continue
        return "\n".join(output) if output else "No upcoming tasks found."
    except Exception as e:
        return f"Canvas Link Failed: {e}"

# --- THE BRAIN (UPDATED: Gemini 2.5 Pro) ---
genai.configure(api_key=GENAI_KEY)

SYS_PROMPT = """
You are O.M.N.I. (Operational Matrix & Neural Interface). 
You are a commercial-grade, high-efficiency executive assistant.
1. IF the user asks about school/homework -> USE Context Data (Canvas).
2. IF the user asks for info/news/facts -> USE Context Data (Google Search).
3. IF no context is needed -> Just answer efficiently.
4. Format: Clean Markdown. No fluff.
"""

# CRITICAL UPDATE: Using the stable 'gemini-2.5-pro' string without suffix
try:
    model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=SYS_PROMPT)
except:
    # Fallback to Flash if Pro is rate-limited on free tier
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYS_PROMPT)

# --- THE INTERFACE ---
st.markdown("<h1 style='text-align: center; color: #a855f7;'>O.M.N.I.</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Direct the intelligence..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # --- INTELLIGENT ROUTING ---
        context_data = ""
        user_lower = prompt.lower()
        
        if any(w in user_lower for w in ["due", "school", "homework", "assignment", "canvas"]):
            with st.spinner("Connecting to Canvas LMS..."):
                data = get_canvas_data()
                context_data += f"\n[SYSTEM DATA: CANVAS]\n{data}\n"

        elif any(w in user_lower for w in ["search", "find", "what is", "who is", "news", "google"]):
            with st.spinner("Accessing Google Global Index..."):
                data = google_search(prompt)
                context_data += f"\n[SYSTEM DATA: GOOGLE SEARCH]\n{data}\n"

        # --- GENERATION ---
        try:
            chat = model.start_chat(history=[])
            final_prompt = f"USER REQUEST: {prompt}\n\nAVAILABLE CONTEXT:\n{context_data}"
            response = chat.send_message(final_prompt)
            
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            message_placeholder.error(f"Neural Link Severed: {e}")
