from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime, date
import json
import streamlit as st
import pandas as pd
import altair as alt
from ratelimit import limits, sleep_and_retry

from .database import DatabaseManager
from .auth import AuthManager
from .utils import (
	load_config,
	load_translations,
	send_email,
	send_sms,
	generate_explanation,
	generate_mcqs,
	transcribe_audio,
	export_to_csv,
	export_to_pdf,
	t,
)


class PageRenderer:
	def __init__(self, db: DatabaseManager, auth: AuthManager, config: Dict[str, Any], translations: Dict[str, Dict[str, str]]):
		self.db = db
		self.auth = auth
		self.config = config
		self.translations = translations

	def sidebar(self) -> None:
		st.sidebar.title(self.config.get("app_name", "App"))
		lang = st.sidebar.selectbox("Language", list(self.translations.keys()), index=0)
		st.session_state["lang"] = lang
		st.sidebar.divider()
		if self.auth.current_user():
			st.sidebar.button("Logout", on_click=self.auth.logout)

	def page_login(self) -> None:
		st.title(t("login", st.session_state.get("lang", "en")))
		email = st.text_input("Email")
		name = st.text_input("Name")
		role = st.selectbox("Role", ["STUDENT", "TEACHER"])
		if st.button("Login"):
			user = self.auth.authenticate(email, name, role)
			if not user:
				st.error("Teacher not verified or invalid login")
				return
			st.success("Logged in")
			st.rerun()

	@sleep_and_retry
	@limits(calls=5, period=60)
	def _submit_doubt_rate_limited(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		return self.db.insert_doubt(payload)

	def page_daily_checkin(self) -> None:
		user = self.auth.current_user()
		if not user:
			st.warning("Please login")
			return
		st.header("Daily Study Check-In")
		col1, col2 = st.columns(2)
		with col1:
			date_val = st.date_input("Date", value=date.today())
			subject = st.text_input("Subject")
			topics = st.tags_input("Topics", help="Add topics, press Enter") if hasattr(st, 'tags_input') else st.text_input("Topics (comma separated)")
			if isinstance(topics, str):
				topics_list = [t.strip() for t in topics.split(",") if t.strip()]
			else:
				topics_list = topics
		with col2:
			homework = st.text_area("Homework / Practicals")
			notes = st.text_area("Notes / Explanations")
			voice_file = st.file_uploader("Voice input (optional)", type=["mp3","wav","m4a"])
			if voice_file:
				with open("/tmp/voice.tmp", "wb") as f:
					f.write(voice_file.read())
					transcript = transcribe_audio(f.name)
					notes = (notes or "") + ("\n" + transcript if transcript else "")
		if st.button("Submit Check-In"):
			payload = {
				"date": date_val.isoformat(),
				"subject": subject,
				"topics": topics_list,
				"homework": homework,
				"notes": notes,
				"points": 10,
			}
			self.db.insert_study_log(user["id"], payload)
			st.success("Check-in submitted. +10 points!")

		st.subheader("Today's Class Notes")
		today_data = self.db.list_class_data_by_date(date.today().isoformat())
		for row in today_data:
			st.write(f"Subject: {row.get('subject')}")
			st.write(f"Topics: {', '.join(row.get('topics', []) or [])}")
			st.write(row.get("notes") or "")
			st.divider()

	def page_doubts(self) -> None:
		user = self.auth.current_user()
		if not user:
			st.warning("Please login")
			return
		st.header("Doubts")
		with st.form("submit_doubt"):
			topic = st.text_input("Topic")
			question = st.text_area("Question")
			submitted = st.form_submit_button("Submit Doubt")
			if submitted and topic and question:
				payload = {"topic": topic, "question": question, "email": user["email"], "created_at": datetime.utcnow().isoformat()}
				row = self._submit_doubt_rate_limited(payload)
				st.success("Doubt submitted. +2 points!")
				if self.config.get("notifications", {}).get("email_enabled"):
					send_email("teachers@school.example", "New doubt submitted", f"{topic}: {question}")

		page = st.number_input("Page", min_value=1, value=1)
		data, total = self.db.paginate_doubts(int(page), int(self.config.get("items_per_page", 10)))
		total_pages = max(1, (total + self.config.get("items_per_page", 10) - 1) // self.config.get("items_per_page", 10))
		st.caption(f"Page {int(page)} of {total_pages}")
		for d in data:
			with st.expander(f"{d.get('topic')}: {d.get('question')[:50]}..."):
				st.write(d.get("question"))
				if d.get("response"):
					st.success(f"Answer: {d.get('response')} (by {d.get('responder_email')})")
				elif self.auth.require_role("TEACHER"):
					resp = st.text_area("Your response", key=f"resp_{d['id']}")
					if st.button("Submit Answer", key=f"btn_{d['id']}"):
						self.db.respond_doubt(d["id"], resp, user["email"])
						st.success("Response saved. Email sent to student.")

	def page_quizzes(self) -> None:
		user = self.auth.current_user()
		if not user:
			st.warning("Please login")
			return
		st.header("Quizzes")
		topic = st.text_input("Topic")
		num = st.slider("Number of questions", 3, 10, 5)
		if st.button("Generate Quiz") and topic:
			mcqs = generate_mcqs(topic, num)
			answers = {}
			for i, q in enumerate(mcqs):
				st.write(q["question"])
				ans = st.radio("Choose", ["A","B","C","D"], key=f"q{i}")
				answers[i] = ans
			if st.button("Submit Quiz"):
				score = sum(1 for i, q in enumerate(mcqs) if answers.get(i) == q.get("answer"))
				self.db.insert_quiz_result({"user_id": user["id"], "topic": topic, "score": score, "total": len(mcqs), "created_at": datetime.utcnow().isoformat()})
				st.success(f"Scored {score}/{len(mcqs)}. +5 points!")

	def page_mock_tests(self) -> None:
		user = self.auth.current_user()
		if not user:
			st.warning("Please login")
			return
		st.header("Mock Tests")
		if self.auth.require_role("TEACHER"):
			with st.form("create_mock"):
				subject = st.text_input("Subject")
				topics = st.text_input("Topics (comma separated)")
				num_q = st.slider("Questions", 3, 20, 5)
				duration = st.number_input("Duration (minutes)", 5, 180, 30)
				sub = st.form_submit_button("Create Test")
				if sub:
					payload = {
						"subject": subject,
						"topics": [t.strip() for t in topics.split(",") if t.strip()],
						"num_questions": num_q,
						"duration": duration,
						"created_by": user["email"],
						"created_at": datetime.utcnow().isoformat(),
					}
					self.db.create_mock_test(payload)
					st.success("Test created")
		st.subheader("Take a Test (Demo)")
		topic = st.text_input("Topic for demo test")
		if st.button("Start Test") and topic:
			mcqs = generate_mcqs(topic, 5)
			answers = {}
			for i, q in enumerate(mcqs):
				st.write(q["question"]) 
				ans = st.radio("Choose", ["A","B","C","D"], key=f"t{i}")
				answers[i] = ans
			if st.button("Submit Test"):
				score = sum(1 for i, q in enumerate(mcqs) if answers.get(i) == q.get("answer"))
				self.db.insert_mock_test_result({"user_id": user["id"], "topic": topic, "score": score, "total": len(mcqs), "created_at": datetime.utcnow().isoformat()})
				st.success(f"Scored {score}/{len(mcqs)}. +10 points!")

	def page_class_data(self) -> None:
		user = self.auth.current_user()
		if not user or not self.auth.require_role("TEACHER"):
			st.warning("Teachers only")
			return
		st.header("Class Data Management")
		date_val = st.date_input("Date", value=date.today())
		subject = st.text_input("Subject")
		topics = st.text_input("Topics (comma separated)")
		notes = st.text_area("Notes")
		homework = st.text_area("Homework / Practicals")
		if st.button("Save"):
			payload = {
				"date": date_val.isoformat(),
				"subject": subject,
				"topics": [t.strip() for t in topics.split(",") if t.strip()],
				"notes": notes,
				"homework": homework,
				"created_by": user["email"],
			}
			self.db.upsert_class_data(payload)
			st.success("Saved")

	def page_history(self) -> None:
		user = self.auth.current_user()
		if not user:
			st.warning("Please login")
			return
		st.header("History")
		page = st.number_input("Page", min_value=1, value=1)
		logs, total = self.db.paginate_study_logs(user["id"], int(page), int(self.config.get("items_per_page", 10)))
		for log in logs:
			with st.expander(f"{log.get('date')} — {log.get('subject','(no subject)')}"):
				st.write(f"Topics: {', '.join(log.get('topics', []) or [])}")
				st.write(log.get("notes") or "")
		csv_bytes = export_to_csv("logs.csv", logs)
		st.download_button("Export CSV", data=csv_bytes, file_name="logs.csv", mime="text/csv")
		pdf_bytes = export_to_pdf("Study Logs", [{"heading": f"{l.get('date')} — {l.get('subject','')}", "lines": [l.get('notes','')]} for l in logs])
		st.download_button("Export PDF", data=pdf_bytes, file_name="logs.pdf", mime="application/pdf")

	def page_analytics(self) -> None:
		user = self.auth.current_user()
		if not user:
			st.warning("Please login")
			return
		st.header("Analytics")
		logs, _ = self.db.paginate_study_logs(user["id"], 1, 1000)
		if not logs:
			st.info("No data yet")
			return
		df = pd.DataFrame(logs)
		st.metric("Total sessions", len(df))
		st.metric("Unique subjects", df["subject"].nunique(dropna=True))
		st.subheader("Sessions per day")
		chart = alt.Chart(df).mark_bar().encode(x="date:T", y="count()")
		st.altair_chart(chart, use_container_width=True)
		st.subheader("Subject distribution")
		pie = alt.Chart(df.dropna(subset=["subject"]).groupby("subject").size().reset_index(name="count")).mark_arc().encode(theta="count:Q", color="subject:N")
		st.altair_chart(pie, use_container_width=True)

		st.subheader("Difficult topics (frequency/keywords)")
		df_notes = df.dropna(subset=["notes"])
		rel = df_notes["notes"].str.contains("hard|difficult|struggle", case=False, na=False)
		st.write(df_notes[rel][["date","subject","notes"]].head(10))

	def page_profile(self) -> None:
		user = self.auth.current_user()
		if not user:
			st.warning("Please login")
			return
		st.header("Profile")
		st.json({k: user.get(k) for k in ["name","email","role","created_at","login_count"]})
		st.subheader("Badges")
		st.write("Coming soon")

	def page_onboarding(self) -> None:
		st.header("Onboarding")
		steps = ["Welcome","Set study goals","Preferences","First study session"]
		step = st.number_input("Step", min_value=1, max_value=len(steps), value=1)
		st.progress(int(step/len(steps)*100))
		if step == 1:
			st.write("Welcome to the app!")
		elif step == 2:
			st.write("Set your study goals")
		elif step == 3:
			st.write("Choose language, notifications, theme")
		elif step == 4:
			self.page_daily_checkin()
			st.balloons()

	def page_settings(self) -> None:
		st.header("Settings")
		st.checkbox("Email notifications", value=self.config.get("notifications",{}).get("email_enabled", True))
		st.checkbox("SMS notifications", value=self.config.get("notifications",{}).get("sms_enabled", False))