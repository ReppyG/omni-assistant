# O.M.N.I. (Operational Matrix & Neural Interface)
**Version:** 3.0 (Executive Class)
**Status:** ACTIVE / DEPLOYED

## 1. System Architecture
* **Core Brain:** Google Gemini 2.5 Pro
* **Hosting:** Streamlit Community Cloud (Serverless)
* **Interface:** Python Streamlit (Chat-Only UI)
* **Memory:** Session State (Ephemeral)

## 2. Capabilities & Tools
* **School:** Canvas LMS API (Read-Only) -> Checks assignments/grades.
* **Search:** Google Custom Search JSON API -> Live web access.
* **Calendar:** Google Calendar API (Read/Write) -> Manages schedule.
* **Storage:** Google Drive API (Read-Only) -> Scans files.

## 3. Deployment Instructions
1.  Clone Repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  **Secrets Management:** The following keys must be in `.streamlit/secrets.toml`:
    * `GENAI_KEY` (Google AI Studio)
    * `CANVAS_API_URL` & `CANVAS_API_KEY`
    * `Google Search_KEY` & `GOOGLE_CX`
    * `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` (OAuth)

## 4. Current State (Phase 5 Snapshot)
* **Integration Level:** High.
* **Auth Strategy:** Headless OAuth via Refresh Token.
* **Next Horizon:** Voice Interface or Visual Dashboard.
