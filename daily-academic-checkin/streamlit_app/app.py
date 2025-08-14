import os
import streamlit as st
from dotenv import load_dotenv

from .database import DatabaseManager
from .auth import AuthManager
from .pages import PageRenderer
from .utils import load_config, load_translations


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:8000")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "public-anon-key")

CONFIG = load_config(os.path.join(os.path.dirname(__file__), "config.yaml"))
TRANSLATIONS = load_translations(os.path.join(os.path.dirname(__file__), "translations.json"))

st.set_page_config(page_title=CONFIG.get("app_name", "App"), layout="wide")

# Inject styles
try:
	with open(os.path.join(os.path.dirname(__file__), "styles.css"), "r", encoding="utf-8") as f:
		st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
	pass


def main() -> None:
	db = DatabaseManager(SUPABASE_URL, SUPABASE_KEY)
	auth = AuthManager(db)
	renderer = PageRenderer(db, auth, CONFIG, TRANSLATIONS)

	renderer.sidebar()

	user = auth.current_user()
	page = st.sidebar.selectbox("Navigate", [
		"Login" if not user else "Daily Check-In",
		"Doubts",
		"Quizzes",
		"Mock Tests",
		"Class Data",
		"History",
		"Analytics",
		"Profile",
		"Onboarding",
		"Settings",
	])

	if page == "Login":
		renderer.page_login()
	elif page == "Daily Check-In":
		renderer.page_daily_checkin()
	elif page == "Doubts":
		renderer.page_doubts()
	elif page == "Quizzes":
		renderer.page_quizzes()
	elif page == "Mock Tests":
		renderer.page_mock_tests()
	elif page == "Class Data":
		renderer.page_class_data()
	elif page == "History":
		renderer.page_history()
	elif page == "Analytics":
		renderer.page_analytics()
	elif page == "Profile":
		renderer.page_profile()
	elif page == "Onboarding":
		renderer.page_onboarding()
	elif page == "Settings":
		renderer.page_settings()


if __name__ == "__main__":
	main()