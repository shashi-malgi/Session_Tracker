import streamlit as st
import uuid
import datetime
import logging

class AuthManager:
    def __init__(self, db_manager, t):
        self.db_manager = db_manager
        self.t = t
        self.logger = logging.getLogger(__name__)

    async def authenticate(self):
        if st.session_state.user:
            return st.session_state.user

        st.sidebar.header(self.t("login"))
        with st.sidebar.form("login_form"):
            email = st.text_input(self.t("email"))
            name = st.text_input(self.t("name"))
            role = st.selectbox(self.t("role"), [self.t("student"), self.t("teacher")])
            submit = st.form_submit_button(self.t("login"))

            if submit and email and name and role:
                try:
                    user = await self.db_manager.get_user_by_email(email)
                    if user:
                        if user['role'] != role.lower():
                            st.sidebar.error(self.t("role_mismatch").format(role=user['role']))
                            return None
                    else:
                        user = {
                            "id": str(uuid.uuid4()),
                            "email": email,
                            "name": name,
                            "role": role.lower(),
                            "created_at": datetime.datetime.utcnow().isoformat(),
                            "points": 0,
                            "badges": [],
                            "logs": [],
                            "groups": [],
                            "difficult_topics": [],
                            "onboarded": False,
                            "preferences": {
                                "language": "English",
                                "notifications": True,
                                "dark_mode": True
                            }
                        }
                        await self.db_manager.insert_user(user)
                    
                    if role.lower() == 'teacher':
                        teacher = await self.db_manager.get_teacher_by_email(email)
                        if not teacher:
                            st.sidebar.error(self.t("teacher_not_found"))
                            return None
                        if not teacher['verified']:
                            st.sidebar.error(self.t("teacher_not_verified"))
                            return None
                        user['teacher_credentials'] = teacher

                    st.session_state.user = user
                    st.sidebar.success(self.t("welcome").format(name=user['name'], role=user['role'].capitalize()))
                    self.logger.info(f"User {email} logged in as {role.lower()}")
                    st.rerun()
                    return user
                except Exception as e:
                    self.logger.error(f"Authentication error: {e}")
                    st.sidebar.error(self.t("auth_error").format(error=e))
        return None