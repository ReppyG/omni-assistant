import streamlit as st
import os
import google.generativeai as genai
from canvasapi import Canvas
from duckduckgo_search import DDGS
from datetime import datetime, timedelta

# --- A.P.E.X. CONFIGURATION (The "Sleek" UI) ---
st.set_page_config(page_title="O.M.N.I.", page_icon="🟣", layout="wide")

# Hide standard Streamlit chrome for that "App" feel
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

# --- THE VAULT (Secrets Management) ---
# We grab keys from Streamlit Secrets (configured later in browser)
try:
    GENAI_KEY = st.secrets["GENAI_KEY"]
    CANVAS_API_URL = st.secrets["CANVAS_API_URL"]
    CANVAS_API_KEY = st.secrets["CANVAS_API_KEY"]
except:
    st.error("SYSTEM ALERT: Critical Keys Missing. Configure Secrets in Streamlit Dashboard.")
    st.stop()

# --- THE TOOLKIT (Virtual Experts) ---

def search_web(query):
    """Real-time web access via DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
        return str(results)
    except Exception as e:
        return f"Search Offline: {e}"

def get_canvas_data(scope="assignments"):
    """Connects to School Canvas LMS."""
    try:
        canvas = Canvas(CANVAS_API_URL, CANVAS_API_KEY)
        user = canvas.get_current_user()
        
        output = []
        if scope == "assignments":
            courses = user.get_courses(enrollment_state='active')
            for course in courses:
                # fetch assignments due in next 14 days
                assignments = course.get_assignments(bucket='upcoming')
                for a in assignments:
                    if a.due_at:
                        due = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                        output.append(f"[Course: {course.name}] {a.name} (Due: {due.strftime('%m-%d %H:%M')})")
        
        return "\n".join(output) if output else "No upcoming tasks found."
    except Exception as e:
        return f"Canvas Link Failed: {e}"

# --- THE BRAIN (Gemini 1.5 Pro) ---
genai.configure(api_key=GENAI_KEY)

# Specialized System Instruction
SYS_PROMPT = """
You are O.M.N.I. (Operational Matrix & Neural Interface). 
You are a ruthless, high-efficiency executive assistant.
Your goal is USER ADVANTAGE.
1. When asked about school, Check Canvas Data first.
2. When asked about facts, Check Web Search.
3. Be concise. Use Markdown. No fluff.
"""

model = genai.GenerativeModel('gemini-1.5-pro-latest', system_instruction=SYS_PROMPT)

# --- THE INTERFACE (Chat Loop) ---

# Title
st.markdown("<h1 style='text-align: center; color: #a855f7;'>O.M.N.I.</h1>", unsafe_allow_html=True)

# Initialize History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input Handling
if prompt := st.chat_input("Direct the intelligence..."):
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. A.P.E.X. Processing (The "Thinking" Phase)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Tool Routing Logic (Simple Version)
        context_data = ""
        if "due" in prompt.lower() or "school" in prompt.lower() or "homework" in prompt.lower():
            with st.spinner("Accessing Canvas LMS Node..."):
                context_data = f"\n[SYSTEM DATA: CANVAS LMS]\n{get_canvas_data()}"
        
        elif "search" in prompt.lower() or "what is" in prompt.lower() or "news" in prompt.lower():
            with st.spinner("Scanning Global Web..."):
                context_data = f"\n[SYSTEM DATA: WEB SEARCH]\n{search_web(prompt)}"

        # 3. Generate Response
        try:
            chat = model.start_chat(history=[]) # Stateless for now to keep it simple, or pass full history
            # We inject the tool data into the prompt for the AI to see
            final_prompt = f"{prompt}\n{context_data}"
            
            response = chat.send_message(final_prompt)
            full_response = response.text
            
            message_placeholder.markdown(full_response)
        except Exception as e:
            message_placeholder.error(f"Neural Link Severed: {e}")

    # 4. Save to Memory
    st.session_state.messages.append({"role": "assistant", "content": full_response})
