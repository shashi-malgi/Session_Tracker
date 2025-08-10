import pytest
import asyncio
from unittest.mock import Mock
from database import DatabaseManager

@pytest.fixture
def supabase_client():
    client = Mock()
    client.table = Mock(return_value=client)
    client.select = Mock(return_value=client)
    client.eq = Mock(return_value=client)
    client.single = Mock(return_value=client)
    client.execute = Mock()
    client.insert = Mock(return_value=client)
    client.update = Mock(return_value=client)
    return client

@pytest.fixture
def db_manager(supabase_client):
    db = DatabaseManager("mock_url", "mock_key")
    db.supabase = supabase_client
    return db

@pytest.mark.asyncio
async def test_get_user_by_email(db_manager, supabase_client):
    supabase_client.execute.return_value.data = [{"id": "123", "email": "test@example.com"}]
    user = await db_manager.get_user_by_email("test@example.com")
    assert user["id"] == "123"
    assert user["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_manager, supabase_client):
    supabase_client.execute.return_value.data = []
    user = await db_manager.get_user_by_email("notfound@example.com")
    assert user is None

@pytest.mark.asyncio
async def test_insert_user(db_manager, supabase_client):
    supabase_client.execute.return_value.data = [{"id": "456", "email": "new@example.com"}]
    user_data = {"id": "456", "email": "new@example.com", "name": "New User"}
    result = await db_manager.insert_user(user_data)
    assert result["id"] == "456"
    supabase_client.insert.assert_called_with(user_data)

@pytest.mark.asyncio
async def test_update_user(db_manager, supabase_client):
    supabase_client.execute.return_value.data = [{"id": "123", "points": 10}]
    user_data = {"points": 10}
    result = await db_manager.update_user("123", user_data)
    assert result["points"] == 10
    supabase_client.update.assert_called_with(user_data)

@pytest.mark.asyncio
async def test_insert_doubt(db_manager, supabase_client):
    supabase_client.execute.return_value.data = [{"id": "789"}]
    doubt_data = {"id": "789", "user_id": "123", "question": "Test doubt"}
    result = await db_manager.insert_doubt(doubt_data)
    assert result is True
    supabase_client.insert.assert_called_with(doubt_data)