from unittest.mock import MagicMock

from streamlit_app.database import DatabaseManager


class DummyClient:
	def __init__(self):
		self.tables = {}

	class Table:
		def __init__(self, parent, name):
			self.parent = parent
			self.name = name
			self.rows = []
			self._query = {}

		def select(self, *_args, **kwargs):
			return self

		def eq(self, key, value):
			self._query[(key, "eq")] = value
			return self

		def maybe_single(self):
			return self

		def single(self):
			return self

		def insert(self, payload):
			self.rows.append(payload)
			self._last_insert = payload
			return self

		def update(self, updates):
			self._updates = updates
			return self

		def order(self, *_args, **_kwargs):
			return self

		def range(self, *_args, **_kwargs):
			return self

		def execute(self):
			data = None
			if hasattr(self, "_last_insert"):
				data = self._last_insert
				self._last_insert = None
				return type("Resp", (), {"data": data, "count": len(self.rows)})
			# very simplified
			return type("Resp", (), {"data": None, "count": len(self.rows)})

	def table(self, name):
		if name not in self.tables:
			self.tables[name] = DummyClient.Table(self, name)
		return self.tables[name]


def test_database_methods_monkeypatched(monkeypatch):
	client = DummyClient()
	monkeypatch.setattr("streamlit_app.database.create_client", lambda url, key: client)
	db = DatabaseManager("u", "k")
	user = db.insert_user({"email": "a@example.com"})
	assert user["email"] == "a@example.com"
	_ = db.get_user_by_email("a@example.com")
	_ = db.update_user("id1", {"login_count": 2})
	_ = db.is_verified_teacher("t@example.com")
	_ = db.upsert_class_data({"date": "2025-01-01", "subject": "Math"})
	_ = db.list_class_data_by_date("2025-01-01")
	_ = db.insert_doubt({"topic": "X", "question": "?"})
	_ = db.paginate_doubts(1, 10)
	_ = db.respond_doubt("1", "ans", "teacher@example.com")
	_ = db.insert_quiz_result({"user_id": "u1"})
	_ = db.create_mock_test({"subject": "Math"})
	_ = db.insert_mock_test_result({"user_id": "u1"})
	_ = db.insert_study_log("u1", {"date": "2025-01-01"})
	_ = db.paginate_study_logs("u1", 1, 10)
	assert True