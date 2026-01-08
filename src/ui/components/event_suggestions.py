"""Event suggestion UI component."""

import streamlit as st
from langchain_core.messages import AIMessage

from ...agent.nodes import add_approved_events


def render_event_suggestions(state, session_state):
    """Render the event suggestion and selection interface.

    Args:
        state: Current agent state
        session_state: Streamlit session state

    Returns:
        bool: True if should rerun, False otherwise
    """
    st.subheader("🎯 Suggested Events to Add to Calendar")
    st.markdown("Select events you'd like to add to your Google Calendar:")

    suggested_events = state.get("suggested_events", [])

    if not suggested_events:
        st.info("No event suggestions available.")
        session_state.showing_event_suggestions = False
        return True

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
                st.markdown(f"**Time:** {event['start_time']} - {event['end_time']}")
                st.markdown(f"**Duration:** {event['duration_minutes']} minutes")
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
                if st.checkbox("Add this event", key=f"select_{event_id}", value=False):
                    selected_event_ids.append(event_id)

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("✅ Add Selected Events", type="primary"):
            if selected_event_ids:
                # Update state with approved events
                state["approved_event_ids"] = selected_event_ids

                # Use status container for real-time observability
                with st.status(
                    "📤 Adding events to calendar...", expanded=True
                ) as status:
                    approved_count = len(selected_event_ids)
                    st.write(f"🔄 Processing {approved_count} event(s)...")

                    # Track which events are being added
                    events_to_add = [
                        e for e in suggested_events if e.get("id") in selected_event_ids
                    ]
                    session_state.added_events = events_to_add

                    # Call add_approved_events node directly
                    result = add_approved_events(state)
                    session_state.state = result

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

                session_state.showing_event_suggestions = False
                session_state.show_final_report = True
                return True
            else:
                st.warning("Please select at least one event to add.")
                return False

    with col2:
        if st.button("⏭️ Skip All"):
            session_state.showing_event_suggestions = False
            session_state.state["suggested_events"] = []
            session_state.state["pending_calendar_additions"] = False
            session_state.show_final_report = True
            return True

    return False
