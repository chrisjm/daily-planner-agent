"""Session state management for Streamlit app."""

import streamlit as st
import uuid


def initialize_session_state(graph):
    """Initialize all session state variables.

    Args:
        graph: The LangGraph instance
    """
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "graph" not in st.session_state:
        st.session_state.graph = graph

    if "state" not in st.session_state:
        st.session_state.state = {
            "messages": [],
            "calendar_context": "",
            "todo_context": "",
            "user_intent": "",
            "analysis": "",
            "confidence": 0.0,
            "missing_info": "",
            "final_schedule": "",
            "schedule_json": [],
            "schedule_metadata": {},
            "debug_info": "",
            "raw_strategist_response": "",
            "suggested_events": [],
            "approved_event_ids": [],
            "pending_calendar_additions": False,
            "cycle_count": 0,
        }

    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False

    if "waiting_for_clarification" not in st.session_state:
        st.session_state.waiting_for_clarification = False

    if "showing_event_suggestions" not in st.session_state:
        st.session_state.showing_event_suggestions = False

    if "added_events" not in st.session_state:
        st.session_state.added_events = []

    if "show_final_report" not in st.session_state:
        st.session_state.show_final_report = False


def reset_session_state():
    """Reset session state for a new planning session."""
    st.session_state.state = {
        "messages": [],
        "calendar_context": "",
        "todo_context": "",
        "user_intent": "",
        "analysis": "",
        "confidence": 0.0,
        "missing_info": "",
        "final_schedule": "",
        "schedule_json": [],
        "schedule_metadata": {},
        "debug_info": "",
        "raw_strategist_response": "",
        "suggested_events": [],
        "approved_event_ids": [],
        "pending_calendar_additions": False,
        "cycle_count": 0,
        "clarification_count": 0,
    }
    st.session_state.conversation_started = False
    st.session_state.waiting_for_clarification = False
    st.session_state.showing_event_suggestions = False
    st.session_state.added_events = []
    st.session_state.show_final_report = False
    st.session_state.thread_id = str(uuid.uuid4())
