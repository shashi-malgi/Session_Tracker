import streamlit as st
import yaml
import logging
from auth import AuthManager
from database import DatabaseManager
from pages import PageRenderer
from utils import load_translations, apply_css
import asyncio

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
with open('config.yaml', 'r') as f:
    CONFIG = yaml.safe_load(f)

# Page configuration
st.set_page_config(
    page_title=CONFIG['app']['title'],
    page_icon=CONFIG['app']['icon'],
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
def init_session_state():
    defaults = {
        'user': None,
        'user_data': {'points': 0, 'badges': [], 'logs': [], 'groups': [], 'difficult_topics': [], 'onboarded': False},
        'language': CONFIG['app']['default_language'],
        'dark_mode': True,
        'notifications_enabled': True,
        'current_page': 'dashboard'
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

async def main():
    try:
        # Apply custom CSS
        apply_css(CONFIG['app']['css_file'])

        # Initialize session state
        init_session_state()

        # Load translations
        translations = load_translations('translations.json')
        t = lambda key: translations.get(st.session_state.language, {}).get(key, key)

        # Initialize managers
        db_manager = DatabaseManager(CONFIG['supabase']['url'], CONFIG['supabase']['key'])
        auth_manager = AuthManager(db_manager, t)
        page_renderer = PageRenderer(db_manager, t, CONFIG)

        # Authenticate user
        user = await auth_manager.authenticate()
        if not user:
            st.markdown(f'<h1 class="main-header">📚 {t("title")}</h1>', unsafe_allow_html=True)
            st.info(t("login_prompt"))
            return

        # Load user data
        user_data = await db_manager.get_user_data(user['id'])
        st.session_state.user_data = user_data

        # Handle onboarding
        if not user_data.get('onboarded', False):
            await page_renderer.render_onboarding(user, user_data)
            return

        # Render sidebar and pages
        page_renderer.render_sidebar(user)
        await page_renderer.render_page(user, user_data)

    except Exception as e:
        logging.error(f"Main app error: {e}")
        st.error(t("app_error").format(error=e))

if __name__ == "__main__":
    asyncio.run(main())