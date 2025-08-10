from supabase import create_client, Client
import streamlit as st
import logging
import asyncio

class DatabaseManager:
    def __init__(self, supabase_url, supabase_key):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.logger = logging.getLogger(__name__)

    @st.cache_data(ttl=300)
    async def get_user_by_email(self, email):
        try:
            response = self.supabase.table("users").select("*").eq("email", email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error fetching user by email: {e}")
            return None

    @st.cache_data(ttl=300)
    async def get_user_by_id(self, user_id):
        try:
            response = self.supabase.table("users").select("*").eq("id", user_id).single().execute()
            return response.data if response.data else {}
        except Exception as e:
            self.logger.error(f"Error fetching user by id: {e}")
            return {}

    @st.cache_data(ttl=300)
    async def get_user_data(self, user_id):
        try:
            response = self.supabase.table("users").select("*").eq("id", user_id).single().execute()
            return response.data if response.data else {}
        except Exception as e:
            self.logger.error(f"Error fetching user data: {e}")
            return {}

    async def insert_user(self, user_data):
        try:
            response = self.supabase.table("users").insert(user_data).execute()
            return response.data[0]
        except Exception as e:
            self.logger.error(f"Error inserting user: {e}")
            raise

    async def update_user(self, user_id, user_data):
        try:
            response = self.supabase.table("users").update(user_data).eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            raise

    @st.cache_data(ttl=300)
    async def get_teacher_by_email(self, email):
        try:
            response = self.supabase.table("teachers").select("*").eq("email", email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error fetching teacher: {e}")
            return None

    @st.cache_data(ttl=600)
    async def get_class_data(self):
        try:
            response = self.supabase.table("class_data").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            self.logger.error(f"Error fetching class data: {e}")
            return []

    async def insert_doubt(self, doubt_data):
        try:
            response = self.supabase.table("doubts").insert(doubt_data).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error inserting doubt: {e}")
            return False

    @st.cache_data(ttl=300)
    async def get_doubts(self, user_id=None):
        try:
            if user_id:
                response = self.supabase.table("doubts").select("*").eq("user_id", user_id).execute()
            else:
                response = self.supabase.table("doubts").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            self.logger.error(f"Error fetching doubts: {e}")
            return []

    async def update_doubt_response(self, doubt_id, response_data):
        try:
            self.supabase.table("doubts").update(response_data).eq("id", doubt_id).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error updating doubt response: {e}")
            return False