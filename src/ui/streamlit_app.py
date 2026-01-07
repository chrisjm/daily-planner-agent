"""Streamlit UI for Executive Function Agent."""

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from ..agent import create_graph


def run_app():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Executive Function Agent", page_icon="🧠", layout="wide"
    )

    st.title("🧠 Executive Function Agent")
    st.markdown("*Your AI consultant for strategic daily planning*")

    # Initialize session state
    if "graph" not in st.session_state:
        st.session_state.graph = create_graph()

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
        }

    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False

    if "waiting_for_clarification" not in st.session_state:
        st.session_state.waiting_for_clarification = False

    # Sidebar with context
    st.sidebar.header("📊 Context")
    with st.sidebar:
        if st.session_state.state.get("calendar_context"):
            with st.expander("📅 Calendar Context", expanded=False):
                st.text(st.session_state.state["calendar_context"])

        if st.session_state.state.get("todo_context"):
            with st.expander("✅ Todo Context", expanded=False):
                st.text(st.session_state.state["todo_context"])

        if st.session_state.state.get("analysis"):
            with st.expander("🧠 Strategic Analysis", expanded=False):
                st.text(st.session_state.state["analysis"])
                st.metric(
                    "Confidence",
                    f"{st.session_state.state.get('confidence', 0.0):.2%}",
                )

    # Main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💬 Conversation")

        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.state["messages"]:
                if isinstance(msg, HumanMessage):
                    with st.chat_message("user"):
                        st.markdown(msg.content)
                elif isinstance(msg, AIMessage):
                    with st.chat_message("assistant"):
                        st.markdown(msg.content)

    with col2:
        st.subheader("📅 Final Schedule")
        schedule_container = st.container()
        with schedule_container:
            if st.session_state.state.get("final_schedule"):
                st.markdown(st.session_state.state["final_schedule"])
            else:
                st.info("Schedule will appear here once generated")

    # Chat input handling
    if not st.session_state.conversation_started:
        user_input = st.chat_input(
            "What would you like help planning? (e.g., 'Help me plan tomorrow focusing on deep work')"
        )

        if user_input:
            st.session_state.conversation_started = True
            st.session_state.state["user_intent"] = user_input
            st.session_state.state["messages"].append(HumanMessage(content=user_input))

            with st.spinner("🔄 Gathering context and analyzing..."):
                result = st.session_state.graph.invoke(st.session_state.state)
                st.session_state.state = result

                if result.get("final_schedule"):
                    st.session_state.waiting_for_clarification = False
                else:
                    st.session_state.waiting_for_clarification = True

            st.rerun()

    elif st.session_state.waiting_for_clarification:
        clarification_input = st.chat_input("Please provide clarification...")

        if clarification_input:
            st.session_state.state["messages"].append(
                HumanMessage(content=clarification_input)
            )

            with st.spinner("🔄 Re-analyzing with your clarification..."):
                result = st.session_state.graph.invoke(st.session_state.state)
                st.session_state.state = result

                if result.get("final_schedule"):
                    st.session_state.waiting_for_clarification = False
                else:
                    st.session_state.waiting_for_clarification = True

            st.rerun()

    else:
        st.success(
            "✅ Schedule generated! You can start a new conversation by refreshing the page."
        )
        if st.button("🔄 Start New Planning Session"):
            st.session_state.state = {
                "messages": [],
                "calendar_context": "",
                "todo_context": "",
                "user_intent": "",
                "analysis": "",
                "confidence": 0.0,
                "missing_info": "",
                "final_schedule": "",
            }
            st.session_state.conversation_started = False
            st.session_state.waiting_for_clarification = False
            st.rerun()

    # Settings in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Settings")
    st.sidebar.caption("Ensure your `.env` file contains:")
    st.sidebar.code(
        """GOOGLE_API_KEY=...
TODOIST_API_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=..."""
    )


if __name__ == "__main__":
    run_app()
