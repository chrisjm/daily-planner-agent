"""Chat interface components."""

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from .schedule_display import render_schedule_from_json


def render_chat_messages(state):
    """Render chat messages and schedule if available.

    Args:
        state: Current agent state
    """
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.markdown(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(msg.content)

    # If we have a schedule, render it from JSON
    if state.get("schedule_json"):
        with st.chat_message("assistant"):
            schedule_display = render_schedule_from_json(
                state["schedule_json"], state.get("schedule_metadata", {})
            )
            st.markdown(schedule_display)
