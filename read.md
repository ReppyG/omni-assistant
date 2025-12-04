O.M.N.I. (Operational Matrix & Neural Interface)

System Version: 5.0 (Deep Research Class)
Architect: A.P.E.X. Protocol
Host: Streamlit Community Cloud (Free Tier)

1. THE ARCHITECTURE

Language: Python 3.11+

Framework: Streamlit (Single-File Architecture)

Intelligence: Google Gemini 2.5 Pro (Fallback: Flash)

Styling: Custom CSS Injection (Glassmorphism/Neon)

2. NEURAL CONNECTIONS (API Stack)

Component

Service

Auth Method

Status

Brain

Google Gemini API

API Key (GENAI_KEY)

Active

School

Canvas LMS API

Token (CANVAS_API_KEY)

Active

Search

Google Custom Search

API Key (Google Search_KEY)

Active

Calendar

Google Workspace

OAuth2 (REFRESH_TOKEN)

Read/Write

Drive

Google Workspace

OAuth2 (REFRESH_TOKEN)

Read Only

Weather

wttr.in

HTTP Request

Active

3. FILE STRUCTURE

streamlit_app.py: The Master Brain (UI + Logic + Tools).

requirements.txt: Dependencies (streamlit, google-generativeai, canvasapi, google-api-python-client, google-auth-oauthlib, requests, beautifulsoup4).

.streamlit/secrets.toml: The Vault (Stores all Keys - NEVER COMMIT TO GITHUB).

4. CAPABILITIES

Stealth HUD: Auto-hiding dashboard showing Next Class, Priority Task, and Local Weather.

Deep Research: Scrapes full text from search results to answer complex queries.

Executive Scheduling: Can read your calendar and autonomously schedule events.

School Tracking: Monitors Canvas for upcoming deadlines.

5. RECOVERY PROTOCOL

If Calendar Fails: Regenerate REFRESH_TOKEN using Google OAuth Playground (Scopes: Calendar + Drive). Ensure CLIENT_SECRET matches.

If Canvas Fails: Generate new Token in Canvas -> Account -> Settings.

If Weather Fails: Check WEATHER_LOCATION in Secrets.

6. FUTURE HORIZONS (Unimplemented)

Voice Module: Javascript Speech-to-Text Bridge.

Grade Simulator: Pandas Dataframe analysis of Canvas Grades.

Focus Mode: Blocker for distraction sites.
