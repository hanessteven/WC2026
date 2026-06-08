import streamlit as st
from supabase import create_client, Client
from src.config import get_supabase_url, get_supabase_key


@st.cache_resource
def get_client() -> Client:
    """Return a cached Supabase client. One instance per Streamlit server process."""
    return create_client(get_supabase_url(), get_supabase_key())