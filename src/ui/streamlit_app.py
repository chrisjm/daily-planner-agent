"""Streamlit UI for Executive Function Agent."""

import streamlit as st
import markdown
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
    if "thread_id" not in st.session_state:
        import uuid

        st.session_state.thread_id = str(uuid.uuid4())

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
            "debug_info": "",
            "raw_strategist_response": "",
        }

    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False

    if "waiting_for_clarification" not in st.session_state:
        st.session_state.waiting_for_clarification = False

    # Sidebar with context and thought processes
    st.sidebar.header("📊 Context & Thought Process")
    with st.sidebar:
        if st.session_state.state.get("calendar_context"):
            with st.expander("📅 Calendar Context", expanded=False):
                html_content = markdown.markdown(
                    st.session_state.state["calendar_context"],
                    extensions=["extra", "nl2br"],
                )
                st.markdown(html_content, unsafe_allow_html=True)

        if st.session_state.state.get("todo_context"):
            with st.expander("✅ Todo Context", expanded=False):
                html_content = markdown.markdown(
                    st.session_state.state["todo_context"],
                    extensions=["extra", "nl2br"],
                )
                st.markdown(html_content, unsafe_allow_html=True)

        if st.session_state.state.get("analysis"):
            with st.expander("🧠 Strategic Analysis", expanded=True):
                st.markdown("**Strategist Reasoning:**")
                html_content = markdown.markdown(
                    st.session_state.state["analysis"], extensions=["extra", "nl2br"]
                )
                st.markdown(html_content, unsafe_allow_html=True)

                confidence = st.session_state.state.get("confidence", 0.0)
                st.metric("Confidence Score", f"{confidence:.2%}")

                if confidence < 0.75:
                    st.warning("⚠️ Below threshold (0.75) - requesting clarification")
                else:
                    st.success("✅ Above threshold - proceeding to planning")

                if st.session_state.state.get("missing_info"):
                    st.markdown("**Missing Information:**")
                    st.info(st.session_state.state["missing_info"])

        if st.session_state.state.get("raw_strategist_response"):
            with st.expander("🔍 Debug: Raw Strategist Response", expanded=False):
                st.markdown("**Raw LLM Output:**")
                st.code(
                    st.session_state.state["raw_strategist_response"], language="json"
                )

                st.markdown("**Response Analysis:**")
                raw_resp = st.session_state.state["raw_strategist_response"]
                st.text(f"Length: {len(raw_resp)} chars")
                st.text(f"Starts with: {raw_resp[:50]}")
                st.text(f"Ends with: {raw_resp[-50:]}")

                if raw_resp.strip().startswith("```"):
                    st.info("✅ Response is wrapped in markdown code block")
                elif raw_resp.strip().startswith("{"):
                    st.info("✅ Response starts with JSON object")
                else:
                    st.error(
                        "⚠️ Response doesn't look like JSON or markdown-wrapped JSON"
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

            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("🔄 Gathering context and analyzing..."):
                # Add user message to state for graph processing
                result = st.session_state.graph.invoke(
                    {
                        **st.session_state.state,
                        "messages": [HumanMessage(content=user_input)],
                    },
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )
                st.session_state.state = result

                if result.get("final_schedule"):
                    st.session_state.waiting_for_clarification = False
                else:
                    st.session_state.waiting_for_clarification = True

            st.rerun()

    elif st.session_state.waiting_for_clarification:
        clarification_input = st.chat_input("Please provide clarification...")

        if clarification_input:
            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(clarification_input)

            with st.spinner("🔄 Re-analyzing with your clarification..."):
                # Add clarification message to state for graph processing
                result = st.session_state.graph.invoke(
                    {
                        **st.session_state.state,
                        "messages": [HumanMessage(content=clarification_input)],
                    },
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )
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
            import uuid

            st.session_state.state = {
                "messages": [],
                "calendar_context": "",
                "todo_context": "",
                "user_intent": "",
                "analysis": "",
                "confidence": 0.0,
                "missing_info": "",
                "final_schedule": "",
                "debug_info": "",
                "raw_strategist_response": "",
            }
            st.session_state.conversation_started = False
            st.session_state.waiting_for_clarification = False
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()


if __name__ == "__main__":
    run_app()
