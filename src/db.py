import streamlit as st
from supabase import create_client, Client
from src.config import get_supabase_url, get_supabase_key, get_supabase_service_key


@st.cache_resource
def get_client() -> Client:
    """Anon-key client for regular user operations. Subject to RLS."""
    return create_client(get_supabase_url(), get_supabase_key())


@st.cache_resource
def get_admin_client() -> Client:
    """Service-role client for admin writes. Bypasses RLS entirely.
    Never expose this key to the browser or non-admin users."""
    return create_client(get_supabase_url(), get_supabase_service_key())