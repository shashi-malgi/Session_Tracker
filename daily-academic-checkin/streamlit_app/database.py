import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from loguru import logger
from supabase import create_client, Client


class DatabaseManager:
	def __init__(self, url: str, key: str) -> None:
		self.client: Client = create_client(url, key)

	# Users
	def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
		resp = self.client.table("users").select("*").eq("email", email).maybe_single().execute()
		return resp.data

	def insert_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("users").insert(user).select("*").single().execute()
		return resp.data

	def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("users").update(updates).eq("id", user_id).select("*").single().execute()
		return resp.data

	# Teachers
	def is_verified_teacher(self, email: str) -> bool:
		resp = self.client.table("teachers").select("verified").eq("email", email).maybe_single().execute()
		data = resp.data
		return bool(data and data.get("verified"))

	# Class data
	def upsert_class_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("class_data").upsert(payload, on_conflict=["date","subject"]).select("*").single().execute()
		return resp.data

	def list_class_data_by_date(self, date_str: str) -> List[Dict[str, Any]]:
		resp = self.client.table("class_data").select("*").eq("date", date_str).order("created_at", desc=True).execute()
		return resp.data or []

	# Doubts
	def insert_doubt(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("doubts").insert(payload).select("*").single().execute()
		return resp.data

	def respond_doubt(self, doubt_id: str, response: str, responder_email: str) -> Dict[str, Any]:
		resp = self.client.table("doubts").update({"response": response, "responder_email": responder_email, "responded_at": datetime.utcnow().isoformat()}).eq("id", doubt_id).select("*").single().execute()
		return resp.data

	def paginate_doubts(self, page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
		offset = (page - 1) * page_size
		count_resp = self.client.table("doubts").select("id", count="exact").execute()
		total = count_resp.count or 0
		resp = self.client.table("doubts").select("*").order("created_at", desc=True).range(offset, offset + page_size - 1).execute()
		return resp.data or [], total

	# Quizzes
	def insert_quiz_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("quizzes").insert(payload).select("*").single().execute()
		return resp.data

	# Mock tests
	def create_mock_test(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("mock_tests").insert(payload).select("*").single().execute()
		return resp.data

	def insert_mock_test_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("mock_tests_results").insert(payload).select("*").single().execute()
		return resp.data

	# Study logs
	def insert_study_log(self, user_id: str, log: Dict[str, Any]) -> Dict[str, Any]:
		resp = self.client.table("study_logs").insert({**log, "user_id": user_id}).select("*").single().execute()
		return resp.data

	def paginate_study_logs(self, user_id: str, page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
		offset = (page - 1) * page_size
		count_resp = self.client.table("study_logs").select("id", count="exact").eq("user_id", user_id).execute()
		total = count_resp.count or 0
		resp = self.client.table("study_logs").select("*").eq("user_id", user_id).order("date", desc=True).range(offset, offset + page_size - 1).execute()
		return resp.data or [], total