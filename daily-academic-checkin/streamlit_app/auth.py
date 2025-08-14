from typing import Optional, Dict, Any
from datetime import datetime
import streamlit as st
from loguru import logger

from .database import DatabaseManager


class AuthManager:
	def __init__(self, db: DatabaseManager) -> None:
		self.db = db

	def authenticate(self, email: str, name: str, role: str) -> Optional[Dict[str, Any]]:
		user = self.db.get_user_by_email(email)
		if user:
			updates = {
				"login_count": (user.get("login_count") or 0) + 1,
				"last_login_at": datetime.utcnow().isoformat(),
			}
			user = self.db.update_user(user["id"], updates)
		else:
			# On first login, verify teacher eligibility
			if role == "TEACHER" and not self.db.is_verified_teacher(email):
				logger.warning("Unverified teacher attempted login")
				return None
			user = self.db.insert_user({
				"email": email,
				"name": name,
				"role": role,
				"login_count": 1,
				"created_at": datetime.utcnow().isoformat(),
			})
		# Persist session
		st.session_state["user"] = user
		return user

	def logout(self) -> None:
		st.session_state.pop("user", None)

	def current_user(self) -> Optional[Dict[str, Any]]:
		return st.session_state.get("user")

	def require_role(self, role: str) -> bool:
		user = self.current_user()
		return bool(user and user.get("role") == role)