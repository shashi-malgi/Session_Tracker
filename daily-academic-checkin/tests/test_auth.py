import builtins
from unittest.mock import MagicMock
from streamlit.runtime.state import SafeSessionState as SessionState
import streamlit as st

from streamlit_app.auth import AuthManager


class DummyDB:
	def __init__(self):
		self.users = {}
		self.teachers = set()

	def get_user_by_email(self, email):
		return self.users.get(email)

	def insert_user(self, user):
		user["id"] = "u1"
		self.users[user["email"]] = user
		return user

	def update_user(self, user_id, updates):
		for email, u in self.users.items():
			if u["id"] == user_id:
				u.update(updates)
				return u

	def is_verified_teacher(self, email):
		return email in self.teachers


def test_existing_user_login(monkeypatch):
	db = DummyDB()
	db.users["a@example.com"] = {"id": "u1", "email": "a@example.com", "login_count": 0}
	auth = AuthManager(db)  # type: ignore
	st.session_state.clear()
	user = auth.authenticate("a@example.com", "A", "STUDENT")
	assert user["login_count"] == 1
	assert st.session_state.get("user")


def test_new_user_registration(monkeypatch):
	db = DummyDB()
	auth = AuthManager(db)  # type: ignore
	st.session_state.clear()
	user = auth.authenticate("b@example.com", "B", "STUDENT")
	assert user["email"] == "b@example.com"
	assert st.session_state.get("user")


def test_verified_teacher_login(monkeypatch):
	db = DummyDB()
	db.teachers.add("t@example.com")
	auth = AuthManager(db)  # type: ignore
	st.session_state.clear()
	user = auth.authenticate("t@example.com", "T", "TEACHER")
	assert user and user["email"] == "t@example.com"


def test_unverified_teacher_rejection(monkeypatch):
	db = DummyDB()
	auth = AuthManager(db)  # type: ignore
	st.session_state.clear()
	user = auth.authenticate("x@example.com", "X", "TEACHER")
	assert user is None