import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from auth import AuthManager

@pytest.fixture
def db_manager():
    db_manager = AsyncMock()
    db_manager.get_user_by_email = AsyncMock()
    db_manager.insert_user = AsyncMock()
    db_manager.get_teacher_by_email = AsyncMock()
    return db_manager

@pytest.fixture
def t():
    return lambda key: key  # Mock translation function

@pytest.fixture
def auth_manager(db_manager, t):
    return AuthManager(db_manager, t)

@pytest.mark.asyncio
async def test_authenticate_existing_user(auth_manager, db_manager):
    db_manager.get_user_by_email.return_value = {
        "id": "123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "student"
    }
    with patch("streamlit.text_input", side_effect=["test@example.com", "Test User"]):
        with patch("streamlit.selectbox", return_value="student"):
            with patch("streamlit.form_submit_button", return_value=True):
                user = await auth_manager.authenticate()
    assert user["id"] == "123"
    assert user["email"] == "test@example.com"
    assert user["role"] == "student"

@pytest.mark.asyncio
async def test_authenticate_new_user(auth_manager, db_manager):
    db_manager.get_user_by_email.return_value = None
    db_manager.insert_user.return_value = {
        "id": "456",
        "email": "new@example.com",
        "name": "New User",
        "role": "student"
    }
    with patch("streamlit.text_input", side_effect=["new@example.com", "New User"]):
        with patch("streamlit.selectbox", return_value="student"):
            with patch("streamlit.form_submit_button", return_value=True):
                user = await auth_manager.authenticate()
    assert user["id"] == "456"
    assert user["email"] == "new@example.com"
    assert db_manager.insert_user.called

@pytest.mark.asyncio
async def test_authenticate_teacher_verified(auth_manager, db_manager):
    db_manager.get_user_by_email.return_value = {
        "id": "789",
        "email": "teacher@example.com",
        "name": "Teacher",
        "role": "teacher"
    }
    db_manager.get_teacher_by_email.return_value = {
        "email": "teacher@example.com",
        "verified": True
    }
    with patch("streamlit.text_input", side_effect=["teacher@example.com", "Teacher"]):
        with patch("streamlit.selectbox", return_value="teacher"):
            with patch("streamlit.form_submit_button", return_value=True):
                user = await auth_manager.authenticate()
    assert user["id"] == "789"
    assert user["teacher_credentials"]["verified"] == True

@pytest.mark.asyncio
async def test_authenticate_teacher_not_verified(auth_manager, db_manager):
    db_manager.get_user_by_email.return_value = {
        "id": "789",
        "email": "teacher@example.com",
        "name": "Teacher",
        "role": "teacher"
    }
    db_manager.get_teacher_by_email.return_value = {
        "email": "teacher@example.com",
        "verified": False
    }
    with patch("streamlit.text_input", side_effect=["teacher@example.com", "Teacher"]):
        with patch("streamlit.selectbox", return_value="teacher"):
            with patch("streamlit.form_submit_button", return_value=True):
                with patch("streamlit.sidebar.error") as mock_error:
                    user = await auth_manager.authenticate()
                    assert user is None
                    mock_error.assert_called_with("teacher_not_verified")