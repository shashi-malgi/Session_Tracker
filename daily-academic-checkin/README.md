# Daily Academic Check-In

A Streamlit app for daily class note sharing, student study check-ins, doubts, quizzes, mock tests, analytics, notifications, and exports.

## Stack
- Streamlit UI
- Supabase (tables: users, teachers, class_data, doubts, quizzes, mock_tests, mock_tests_results, study_logs)
- Optional OpenAI for AI features; Whisper for voice transcription; Twilio for SMS; ReportLab for PDF

## Setup
1. Create a `.env` with:
```
SUPABASE_URL=... 
SUPABASE_KEY=...
OPENAI_API_KEY=... # optional
TWILIO_ACCOUNT_SID=... # optional
TWILIO_AUTH_TOKEN=... # optional
TWILIO_FROM_NUMBER=... # optional
```

2. Install Python deps and run app:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

3. Configure Supabase tables and RLS as per the app's expectations.

## Tests
```
pytest -q
```