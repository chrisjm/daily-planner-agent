"""Streamlit UI for Executive Function Agent."""

import streamlit as st
from langchain_core.messages import HumanMessage

from ..agent import create_graph
from .state_manager import initialize_session_state, reset_session_state
from .components import (
    render_sidebar,
    render_chat_messages,
    render_event_suggestions,
    generate_final_report,
)


def run_app():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Executive Function Agent", page_icon="🧠", layout="wide"
    )

    st.title("🧠 Executive Function Agent")
    st.markdown("*Your AI consultant for strategic daily planning*")

    # Initialize session state
    initialize_session_state(create_graph())

    # Sidebar with context and thought processes
    render_sidebar(st.session_state.state)

    # Main conversation area
    st.subheader("💬 Conversation")

    chat_container = st.container()
    with chat_container:
        render_chat_messages(st.session_state.state)

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

            # Use status container for real-time observability
            with st.status("🔄 Processing your request...", expanded=True) as status:
                st.write("📊 Gathering context from Calendar and Todoist...")
                print("\n🔍 DEBUG: Starting graph.stream (initial request)")

                # Stream graph execution to show progress
                # Don't pass messages here - let gather_context add the user message
                # This prevents operator.add from duplicating messages
                final_result = None
                for event in st.session_state.graph.stream(
                    st.session_state.state,
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                ):
                    # event is a dict with node name as key
                    for node_name, node_output in event.items():
                        print(
                            f"🔍 DEBUG: Node '{node_name}' output has {len(node_output.get('messages', []))} messages"
                        )
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
                            event_count = len(node_output.get("suggested_events", []))
                            st.write("✅ Schedule generated")
                            if event_count > 0:
                                st.write(
                                    f"💡 Generated {event_count} calendar event suggestion(s)"
                                )
                            else:
                                st.write("💡 No calendar events to suggest")

                        # Keep the last output as final result
                        final_result = node_output

                status.update(label="✅ Processing complete!", state="complete")

            # Update state only once after all streaming completes
            print(
                f"🔍 DEBUG: Final result has {len(final_result.get('messages', []))} messages"
            )
            st.session_state.state = final_result
            print(
                f"🔍 DEBUG: Session state now has {len(st.session_state.state.get('messages', []))} messages"
            )

            if final_result.get("schedule_json"):
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
                # Add clarification message directly to state
                # Don't pass messages separately to avoid operator.add duplication
                new_message = HumanMessage(content=clarification_input)
                current_messages = st.session_state.state.get("messages", [])
                print(
                    f"\n🔍 DEBUG: Clarification cycle - current messages: {len(current_messages)}"
                )

                # Check if this exact message is already in the list
                if not any(
                    isinstance(m, HumanMessage) and m.content == clarification_input
                    for m in current_messages
                ):
                    # Add message directly to state, not as separate parameter
                    st.session_state.state["messages"] = current_messages + [
                        new_message
                    ]
                    print(
                        f"🔍 DEBUG: Added clarification message to state, total: {len(st.session_state.state['messages'])}"
                    )
                else:
                    print("🔍 DEBUG: Clarification message already exists")

                result = st.session_state.graph.invoke(
                    st.session_state.state,
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )
                print(
                    f"🔍 DEBUG: After invoke, result has {len(result.get('messages', []))} messages"
                )
                st.session_state.state = result
                print(
                    f"🔍 DEBUG: Session state now has {len(st.session_state.state.get('messages', []))} messages"
                )

                if result.get("schedule_json"):
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
        should_rerun = render_event_suggestions(
            st.session_state.state, st.session_state
        )
        if should_rerun:
            st.rerun()

    else:
        # Show final report if available
        if st.session_state.show_final_report and st.session_state.state.get(
            "schedule_json"
        ):
            st.subheader("📋 Final Schedule Report")

            # Generate and display the final report
            final_report = generate_final_report(
                st.session_state.state["schedule_json"],
                st.session_state.state.get("schedule_metadata", {}),
                st.session_state.added_events,
            )
            st.markdown(final_report)

            # Add download button for the report
            st.download_button(
                label="📥 Download Schedule Report",
                data=final_report,
                file_name="schedule_report.md",
                mime="text/markdown",
            )
        else:
            st.success(
                "✅ Schedule generated! You can start a new conversation by refreshing the page."
            )

        if st.button("🔄 Start New Planning Session"):
            reset_session_state()
            st.rerun()


if __name__ == "__main__":
    run_app()
