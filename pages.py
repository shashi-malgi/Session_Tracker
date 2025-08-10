import streamlit as st
import pandas as pd
import altair as alt
import datetime
import uuid
from ratelimit import limits, sleep_and_retry
import logging
import asyncio

class PageRenderer:
    def __init__(self, db_manager, t, config):
        self.db_manager = db_manager
        self.t = t
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.items_per_page = config['app'].get('items_per_page', 10)

    def render_sidebar(self, user):
        st.sidebar.header(f"{self.t('welcome').format(name=user['name'], role=user['role'].capitalize())}")
        if st.sidebar.button(self.t("logout")):
            st.session_state.user = None
            st.rerun()
        language = st.sidebar.selectbox(
            self.t("language"),
            ["English", "Español", "हिन्दी"],
            index=["English", "Español", "हिन्दी"].index(st.session_state.language)
        )
        if language != st.session_state.language:
            st.session_state.language = language
            st.rerun()
        with st.sidebar.expander(self.t("settings")):
            st.session_state.dark_mode = st.checkbox(self.t("dark_mode"), st.session_state.dark_mode)
            st.session_state.notifications_enabled = st.checkbox(self.t("notifications"), st.session_state.notifications_enabled)
        pages = [
            self.t("dashboard"),
            "Check-In",
            self.t("history"),
            self.t("analytics"),
            self.t("profile"),
            self.t("doubts"),
            self.t("export"),
            self.t("class_data"),
            self.t("quizzes"),
            self.t("mock_tests")
        ]
        if user['role'] == 'teacher':
            pages.append(self.t("manage_class"))
        st.session_state.current_page = st.sidebar.radio("Navigation", pages)

    async def render_onboarding(self, user, user_data):
        st.markdown(f"### {self.t('welcome')} 🎉")
        steps = [
            {"title": self.t("welcome"), "content": self.t("welcome_message"), "action": None},
            {"title": self.t("set_goals"), "content": self.t("goals_prompt"), "action": "goals_input"},
            {"title": self.t("choose_preferences"), "content": self.t("preferences_prompt"), "action": "preferences"},
            {"title": self.t("first_checkin"), "content": self.t("first_checkin_prompt"), "action": "first_checkin"}
        ]
        current_step = st.session_state.get('onboarding_step', 0)
        if current_step < len(steps):
            step = steps[current_step]
            st.subheader(f"Step {current_step + 1}: {step['title']}")
            st.write(step['content'])
            if step['action'] == 'goals_input':
                goals = st.text_area(self.t("your_goals"), placeholder=self.t("goals_placeholder"))
                if st.button(self.t("next")) and goals:
                    user_data['goals'] = goals
                    st.session_state.onboarding_step = current_step + 1
                    await self.db_manager.update_user(user['id'], user_data)
                    st.rerun()
            elif step['action'] == 'preferences':
                col1, col2 = st.columns(2)
                with col1:
                    notifications = st.checkbox(self.t("notifications"), value=True)
                    dark_mode = st.checkbox(self.t("dark_mode"), value=True)
                with col2:
                    language = st.selectbox(self.t("language"), ["English", "Español", "हिन्दी"])
                if st.button(self.t("next")):
                    user_data['preferences'] = {
                        'notifications': notifications,
                        'dark_mode': dark_mode,
                        'language': language
                    }
                    st.session_state.language = language
                    st.session_state.onboarding_step = current_step + 1
                    await self.db_manager.update_user(user['id'], user_data)
                    st.rerun()
            elif step['action'] == 'first_checkin':
                with st.form("onboarding_checkin"):
                    subject = st.text_input(self.t("subject"))
                    topics = st.text_input(self.t("topics"))
                    notes = st.text_area(self.t("notes"))
                    if st.form_submit_button(self.t("complete_onboarding")):
                        if subject and topics:
                            first_log = {
                                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                                "subject": subject,
                                "topics": [t.strip() for t in topics.split(",")],
                                "notes": notes,
                                "timestamp": datetime.datetime.utcnow().isoformat()
                            }
                            user_data['logs'].append(first_log)
                            user_data['onboarded'] = True
                            await self.db_manager.update_user(user['id'], user_data)
                            st.success(self.t("onboarding_complete"))
                            st.rerun()
            else:
                if st.button(self.t("next")):
                    st.session_state.onboarding_step = current_step + 1
                    st.rerun()
        st.progress((current_step + 1) / len(steps))

    async def render_history_page(self, user, user_data):
        st.header(self.t("history"))
        logs = user_data.get('logs', []) if user['role'] == 'student' else []
        if not logs:
            st.info(self.t("no_logs"))
            return
        total_pages = (len(logs) + self.items_per_page - 1) // self.items_per_page
        page = st.number_input(self.t("page_number"), min_value=1, max_value=max(total_pages, 1), value=1)
        start_idx = (page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        paginated_logs = logs[start_idx:end_idx]
        for log in reversed(paginated_logs):
            with st.expander(f"{log['date']} - {log.get('subject', self.t('no_subject'))}"):
                st.write(f"**{self.t('topics')}:** {', '.join(log.get('topics', []))}")
                st.write(f"**{self.t('notes')}:** {log.get('notes', self.t('no_notes'))}")
        st.write(f"{self.t('page')} {page} {self.t('of')} {total_pages}")

    @sleep_and_retry
    @limits(calls=5, period=60)  # 5 doubts per minute
    async def render_doubts_page(self, user, user_data):
        st.header(self.t("doubts"))
        st.subheader(self.t("ask_doubt"))
        topics = set(t for log in user_data['logs'] for t in log.get('topics', [])).union(
            t for cd in await self.db_manager.get_class_data() for t in cd.get('topics', [])
        )
        with st.form("doubt_form"):
            topic = st.selectbox(self.t("topic"), list(topics) + ["Other"])
            if topic == "Other":
                topic = st.text_input(self.t("custom_topic"))
            question = st.text_area(self.t("question"), placeholder=self.t("question_placeholder"))
            if st.form_submit_button(self.t("submit_doubt")):
                if topic and question:
                    doubt_data = {
                        "id": str(uuid.uuid4()),
                        "user_id": user['id'],
                        "topic": topic,
                        "question": question,
                        "created_at": datetime.datetime.utcnow().isoformat()
                    }
                    with st.spinner(self.t("submitting_doubt")):
                        if await self.db_manager.insert_doubt(doubt_data):
                            st.markdown(f"<div class='success-message'>{self.t('doubt_submitted')} (+2 {self.t('points')})</div>", unsafe_allow_html=True)
                            user_data['points'] = user_data.get('points', 0) + 2
                            await self.db_manager.update_user(user['id'], user_data)
                            self.logger.info(f"Doubt submitted by user {user['id']}")
                        else:
                            st.error(self.t("doubt_submit_error"))
        st.subheader(self.t("all_doubts"))
        doubts = await self.db_manager.get_doubts()
        if not doubts:
            st.info(self.t("no_doubts"))
            return
        total_pages = (len(doubts) + self.items_per_page - 1) // self.items_per_page
        page = st.number_input(self.t("doubts_page_number"), min_value=1, max_value=max(total_pages, 1), value=1)
        start_idx = (page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        paginated_doubts = doubts[start_idx:end_idx]
        for doubt in reversed(paginated_doubts):
            with st.expander(f"{doubt['topic']} - {doubt['created_at'][:10]}"):
                st.markdown(f"<div class='doubt-card'>**{self.t('question')}:** {doubt['question']}</div>", unsafe_allow_html=True)
                if doubt.get('response'):
                    st.write(f"**{self.t('response')}:** {doubt['response']}")
                    responder = await self.db_manager.get_user_by_id(doubt['response_by'])
                    st.write(f"**{self.t('responded_by')}:** {responder['name']}")
                    st.write(f"**{self.t('responded_at')}:** {doubt['responded_at'][:10]}")
                else:
                    st.info(self.t("no_response"))
                    if user['role'] == 'teacher' and user.get('teacher_credentials', {}).get('verified'):
                        with st.form(f"respond_form_{doubt['id']}"):
                            response_text = st.text_area(f"{self.t('respond_to')} {doubt['topic']}", placeholder=self.t("response_placeholder"))
                            if st.form_submit_button(self.t("respond")):
                                if response_text:
                                    response_data = {
                                        "response": response_text,
                                        "response_by": user['id'],
                                        "responded_at": datetime.datetime.utcnow().isoformat()
                                    }
                                    if await self.db_manager.update_doubt_response(doubt['id'], response_data):
                                        st.success(self.t("response_submitted"))
                                        self.logger.info(f"Response submitted for doubt {doubt['id']}")
                                    else:
                                        st.error(self.t("response_submit_error"))

    async def render_page(self, user, user_data):
        page = st.session_state.current_page
        if page == self.t("history"):
            await self.render_history_page(user, user_data)
        elif page == self.t("doubts"):
            await self.render_doubts_page(user, user_data)
        else:
            st.header(page)
            st.write(f"{self.t('under_construction')} {page}")