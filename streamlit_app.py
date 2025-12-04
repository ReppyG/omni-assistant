import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

st.set_page_config(page_title="DEBUG MODE", layout="wide")

st.title(" 🛠 A.P.E.X. DIAGNOSTIC TOOL")

# 1. LOAD SECRETS
try:
    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REFRESH_TOKEN = st.secrets["GOOGLE_REFRESH_TOKEN"]
    st.success("✅ Secrets Loaded")
except:
    st.error("❌ Secrets Missing! Check Dashboard.")
    st.stop()

# 2. BUILD CREDENTIALS
st.write("---")
st.write("### 1. Testing Credential Construction")
try:
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    st.info(f"Credentials Object Built. Client ID starts with: {CLIENT_ID[:10]}...")
except Exception as e:
    st.error(f"Failed to build creds: {e}")

# 3. TEST CALENDAR CONNECTION
st.write("### 2. Testing Google Link (Real-Time)")
if st.button("RUN CONNECTION TEST"):
    try:
        service = build('calendar', 'v3', credentials=creds)
        # Try to list 1 event
        events_result = service.events().list(calendarId='primary', maxResults=1).execute()
        st.balloons()
        st.success("✅ SUCCESS! CONNECTION ESTABLISHED.")
        st.json(events_result)
    except Exception as e:
        st.error("❌ CONNECTION FAILED")
        st.code(str(e)) # THIS IS THE IMPORTANT PART
        
        # Auto-Diagnosis
        err_str = str(e)
        if "invalid_grant" in err_str:
            st.warning("DIAGNOSIS: The Refresh Token is BAD. It does not match the Client ID/Secret.")
        elif "unauthorized_client" in err_str:
             st.warning("DIAGNOSIS: Client Secret is WRONG.")
        elif "access_denied" in err_str or "service_not_allowed" in err_str:
             st.warning("DIAGNOSIS: SCHOOL BLOCKED IT. Your admin does not allow this app.")
