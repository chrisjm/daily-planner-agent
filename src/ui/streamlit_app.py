"""Streamlit UI for Executive Function Agent."""

import streamlit as st
import markdown
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

from ..agent import create_graph
from ..agent.nodes import add_approved_events


def render_schedule_from_json(schedule_json, metadata):
    """Render a user-friendly schedule display from JSON data."""
    if not schedule_json:
        return "No schedule generated."

    # Priority emoji mapping
    priority_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🔵", "P4": "⚪"}

    # Type emoji mapping
    type_emoji = {
        "work": "💼",
        "break": "☕",
        "meeting": "👥",
        "focus": "🎯",
        "admin": "📋",
        "personal": "🏠",
    }

    # Energy level emoji
    energy_emoji = {"high": "⚡", "medium": "🔋", "low": "🪫"}

    output = []

    # Add metadata summary
    if metadata:
        output.append("## 📊 Schedule Overview\n")
        if metadata.get("scheduling_strategy"):
            output.append(f"**Strategy:** {metadata['scheduling_strategy']}\n")
        if metadata.get("peak_energy_utilization"):
            output.append(
                f"**Energy Management:** {metadata['peak_energy_utilization']}\n"
            )

        stats = []
        if metadata.get("total_scheduled_minutes"):
            hours = metadata["total_scheduled_minutes"] / 60
            stats.append(f"⏱️ {hours:.1f} hours scheduled")
        if metadata.get("high_priority_count"):
            stats.append(f"🔴 {metadata['high_priority_count']} high-priority tasks")
        if metadata.get("break_count"):
            stats.append(f"☕ {metadata['break_count']} breaks")

        if stats:
            output.append(" • ".join(stats) + "\n")

        if metadata.get("flexibility_notes"):
            output.append(f"\n💡 **Flexibility:** {metadata['flexibility_notes']}\n")

        output.append("\n---\n")

    # Add schedule items
    output.append("## 📅 Your Schedule\n")

    for item in schedule_json:
        # Parse times for display
        try:
            start = datetime.strptime(item["start_time"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(item["end_time"], "%Y-%m-%d %H:%M")
            time_str = f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
        except (ValueError, KeyError):
            time_str = f"{item['start_time']} - {item['end_time']}"

        # Build the item display
        priority = priority_emoji.get(item.get("priority", ""), "")
        type_icon = type_emoji.get(item.get("type", ""), "")
        energy = energy_emoji.get(item.get("energy_level", ""), "")

        output.append(f"### {type_icon} {time_str}\n")
        output.append(f"**{priority} {item['title']}** {energy}\n")

        if item.get("description"):
            output.append(f"\n{item['description']}\n")

        # Add metadata in a compact format
        meta_items = []
        if item.get("priority"):
            meta_items.append(f"Priority: {item['priority']}")
        if item.get("cognitive_load"):
            meta_items.append(f"Cognitive Load: {item['cognitive_load']}")
        if item.get("tags"):
            tags_str = ", ".join(item["tags"])
            meta_items.append(f"Tags: {tags_str}")

        if meta_items:
            output.append(f"\n*{' • '.join(meta_items)}*\n")

        if item.get("rationale"):
            output.append(f"\n💭 *{item['rationale']}*\n")

        output.append("\n")

    return "\n".join(output)


def generate_final_report(schedule_json, metadata, added_events):
    """Generate a final schedule report including which events were added to calendar."""
    if not schedule_json:
        return "No schedule generated."

    output = []

    # Add header
    output.append("# 📋 Final Schedule Report\n")

    # Add metadata summary
    if metadata:
        if metadata.get("scheduling_strategy"):
            output.append(f"**Strategy:** {metadata['scheduling_strategy']}\n")

        stats = []
        if metadata.get("total_scheduled_minutes"):
            hours = metadata["total_scheduled_minutes"] / 60
            stats.append(f"⏱️ {hours:.1f} hours")
        if metadata.get("high_priority_count"):
            stats.append(f"🔴 {metadata['high_priority_count']} P1 tasks")
        if metadata.get("break_count"):
            stats.append(f"☕ {metadata['break_count']} breaks")

        if stats:
            output.append(" • ".join(stats) + "\n")

        output.append("\n")

    # Add calendar integration status
    if added_events:
        output.append(f"## ✅ Added to Calendar ({len(added_events)} events)\n")
        for event in added_events:
            try:
                start = datetime.strptime(event["start_time"], "%Y-%m-%d %H:%M")
                time_str = start.strftime("%I:%M %p")
            except (ValueError, KeyError):
                time_str = event.get("start_time", "")

            output.append(f"- **{time_str}** - {event.get('title', 'Untitled')}\n")
        output.append("\n")

    # Add condensed schedule view
    output.append("## 📅 Complete Schedule\n")

    for item in schedule_json:
        try:
            start = datetime.strptime(item["start_time"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(item["end_time"], "%Y-%m-%d %H:%M")
            time_str = f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
        except (ValueError, KeyError):
            time_str = f"{item['start_time']} - {item['end_time']}"

        # Check if this was added to calendar
        in_calendar = any(
            e.get("title") == item.get("title")
            and e.get("start_time") == item.get("start_time")
            for e in added_events
        )
        calendar_marker = "📅 " if in_calendar else ""

        priority_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🔵", "P4": "⚪"}
        priority = priority_emoji.get(item.get("priority", ""), "")

        output.append(f"**{time_str}** {calendar_marker}{priority} {item['title']}\n")

    return "\n".join(output)


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

        # If we have a schedule, render it from JSON
        if st.session_state.state.get("schedule_json"):
            with st.chat_message("assistant"):
                schedule_display = render_schedule_from_json(
                    st.session_state.state["schedule_json"],
                    st.session_state.state.get("schedule_metadata", {}),
                )
                st.markdown(schedule_display)

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
            print(
                f"🔍 DEBUG: Final result has {len(final_result.get('messages', []))} messages"
            )
            st.session_state.state = final_result
            print(
                f"🔍 DEBUG: Session state now has {len(st.session_state.state.get('messages', []))} messages"
            )

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

                # Build expander title with type emoji
                type_emoji_map = {
                    "work": "💼",
                    "meeting": "👥",
                    "focus": "🎯",
                    "admin": "📋",
                    "personal": "🏠",
                }
                type_icon = type_emoji_map.get(event.get("type", ""), "📅")

                with st.expander(
                    f"{type_icon} {event['title']} - {event['start_time']}",
                    expanded=True,
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

                        # Show new metadata fields
                        if event.get("energy_level"):
                            energy_emoji = {"high": "⚡", "medium": "🔋", "low": "🪫"}
                            energy_icon = energy_emoji.get(event["energy_level"], "")
                            st.markdown(
                                f"**Energy Level:** {energy_icon} {event['energy_level'].title()}"
                            )

                        if event.get("cognitive_load"):
                            st.markdown(
                                f"**Cognitive Load:** {event['cognitive_load'].title()}"
                            )

                        if event.get("tags"):
                            tags_str = ", ".join(event["tags"])
                            st.markdown(f"**Tags:** {tags_str}")

                        if event.get("rationale"):
                            st.markdown(f"**Rationale:** {event['rationale']}")

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

                            # Track which events are being added
                            events_to_add = [
                                e
                                for e in suggested_events
                                if e.get("id") in selected_event_ids
                            ]
                            st.session_state.added_events = events_to_add

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
                        st.session_state.show_final_report = True
                        st.rerun()
                    else:
                        st.warning("Please select at least one event to add.")

            with col2:
                if st.button("⏭️ Skip All"):
                    st.session_state.showing_event_suggestions = False
                    st.session_state.state["suggested_events"] = []
                    st.session_state.state["pending_calendar_additions"] = False
                    st.session_state.show_final_report = True
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
            st.rerun()


if __name__ == "__main__":
    run_app()
