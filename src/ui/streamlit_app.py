"""Streamlit UI for Executive Function Agent."""

import streamlit as st
import markdown
from langchain_core.messages import HumanMessage, AIMessage

from ..agent import create_graph
from ..agent.nodes import add_approved_events


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
            "suggested_events": [],
            "approved_event_ids": [],
            "pending_calendar_additions": False,
        }

    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False

    if "waiting_for_clarification" not in st.session_state:
        st.session_state.waiting_for_clarification = False

    if "showing_event_suggestions" not in st.session_state:
        st.session_state.showing_event_suggestions = False

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

    # Main conversation area
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

            # Add user message to state for graph processing
            # Only add if not already present to avoid duplicates
            new_message = HumanMessage(content=user_input)
            current_messages = st.session_state.state.get("messages", [])

            # Check if this exact message is already in the list
            if not any(
                isinstance(m, HumanMessage) and m.content == user_input
                for m in current_messages
            ):
                messages_to_send = current_messages + [new_message]
            else:
                messages_to_send = current_messages

            # Use status container for real-time observability
            with st.status("🔄 Processing your request...", expanded=True) as status:
                st.write("📊 Gathering context from Calendar and Todoist...")

                # Stream graph execution to show progress
                final_result = None
                for event in st.session_state.graph.stream(
                    {
                        **st.session_state.state,
                        "messages": messages_to_send,
                    },
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                ):
                    # event is a dict with node name as key
                    for node_name, node_output in event.items():
                        if node_name == "gather_context":
                            st.write("✅ Context gathered")
                            st.write("🧠 Analyzing with strategist...")
                        elif node_name == "strategist":
                            confidence = node_output.get("confidence", 0.0)
                            st.write(
                                f"✅ Analysis complete (confidence: {confidence:.0%})"
                            )
                            if confidence < 0.95:
                                st.write("💬 Generating clarification question...")
                            else:
                                st.write("📅 Creating your schedule...")
                        elif node_name == "ask_clarification":
                            st.write("✅ Clarification question ready")
                        elif node_name == "planner":
                            st.write("✅ Schedule generated")
                            st.write("💡 Analyzing schedule for event suggestions...")
                        elif node_name == "suggest_events":
                            event_count = len(node_output.get("suggested_events", []))
                            if event_count > 0:
                                st.write(f"✅ Found {event_count} event suggestion(s)")
                            else:
                                st.write("✅ No additional events to suggest")

                        # Keep the last output as final result
                        final_result = node_output

                status.update(label="✅ Processing complete!", state="complete")

            # Update state only once after all streaming completes
            st.session_state.state = final_result

            if final_result.get("final_schedule"):
                st.session_state.waiting_for_clarification = False
                # Check if there are suggested events to show
                if (
                    final_result.get("suggested_events")
                    and len(final_result["suggested_events"]) > 0
                ):
                    st.session_state.showing_event_suggestions = True
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
                # Only add if not already present to avoid duplicates
                new_message = HumanMessage(content=clarification_input)
                current_messages = st.session_state.state.get("messages", [])

                # Check if this exact message is already in the list
                if not any(
                    isinstance(m, HumanMessage) and m.content == clarification_input
                    for m in current_messages
                ):
                    messages_to_send = current_messages + [new_message]
                else:
                    messages_to_send = current_messages

                result = st.session_state.graph.invoke(
                    {
                        **st.session_state.state,
                        "messages": messages_to_send,
                    },
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )
                st.session_state.state = result

                if result.get("final_schedule"):
                    st.session_state.waiting_for_clarification = False
                    # Check if there are suggested events to show
                    if (
                        result.get("suggested_events")
                        and len(result["suggested_events"]) > 0
                    ):
                        st.session_state.showing_event_suggestions = True
                else:
                    st.session_state.waiting_for_clarification = True

            st.rerun()

    elif st.session_state.showing_event_suggestions:
        # Show event approval interface
        st.subheader("🎯 Suggested Events to Add to Calendar")
        st.markdown("Select events you'd like to add to your Google Calendar:")

        suggested_events = st.session_state.state.get("suggested_events", [])

        if not suggested_events:
            st.info("No event suggestions available.")
            st.session_state.showing_event_suggestions = False
            st.rerun()
        else:
            # Create checkboxes for each suggested event
            selected_event_ids = []

            for idx, event in enumerate(suggested_events):
                event_id = event.get("id", f"event_{idx}")

                with st.expander(
                    f"📅 {event['title']} - {event['start_time']}", expanded=True
                ):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(
                            f"**Time:** {event['start_time']} - {event['end_time']}"
                        )
                        st.markdown(
                            f"**Duration:** {event['duration_minutes']} minutes"
                        )
                        st.markdown(f"**Priority:** {event.get('priority', 'N/A')}")
                        if event.get("source_task"):
                            st.markdown(f"**Source Task:** {event['source_task']}")
                        st.markdown(f"**Rationale:** {event.get('rationale', '')}")

                    with col2:
                        if st.checkbox(
                            "Add this event", key=f"select_{event_id}", value=False
                        ):
                            selected_event_ids.append(event_id)

            # Action buttons
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.button("✅ Add Selected Events", type="primary"):
                    if selected_event_ids:
                        # Update state with approved events
                        st.session_state.state["approved_event_ids"] = (
                            selected_event_ids
                        )

                        # Use status container for real-time observability
                        with st.status(
                            "📤 Adding events to calendar...", expanded=True
                        ) as status:
                            approved_count = len(selected_event_ids)
                            st.write(f"🔄 Processing {approved_count} event(s)...")

                            # Call add_approved_events node directly
                            result = add_approved_events(st.session_state.state)
                            st.session_state.state = result

                            # Show results
                            success_msg = [
                                msg
                                for msg in result.get("messages", [])
                                if isinstance(msg, AIMessage)
                            ]
                            if success_msg:
                                st.write(success_msg[-1].content)

                            st.write("🔄 Refreshing calendar context...")
                            st.write("✅ Calendar updated!")

                            status.update(
                                label="✅ Events added successfully!", state="complete"
                            )

                        st.session_state.showing_event_suggestions = False
                        st.rerun()
                    else:
                        st.warning("Please select at least one event to add.")

            with col2:
                if st.button("⏭️ Skip All"):
                    st.session_state.showing_event_suggestions = False
                    st.session_state.state["suggested_events"] = []
                    st.session_state.state["pending_calendar_additions"] = False
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
                "schedule_json": [],
                "debug_info": "",
                "raw_strategist_response": "",
                "suggested_events": [],
                "approved_event_ids": [],
                "pending_calendar_additions": False,
            }
            st.session_state.conversation_started = False
            st.session_state.waiting_for_clarification = False
            st.session_state.showing_event_suggestions = False
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()


if __name__ == "__main__":
    run_app()
