"""Sidebar component for context and analysis display."""

import streamlit as st
import markdown


def render_sidebar(state):
    """Render the sidebar with context and thought processes.

    Args:
        state: Current agent state
    """
    st.sidebar.header("📊 Context & Thought Process")

    with st.sidebar:
        if state.get("calendar_context"):
            with st.expander("📅 Calendar Context", expanded=False):
                html_content = markdown.markdown(
                    state["calendar_context"],
                    extensions=["extra", "nl2br"],
                )
                st.markdown(html_content, unsafe_allow_html=True)

        if state.get("todo_context"):
            with st.expander("✅ Todo Context", expanded=False):
                html_content = markdown.markdown(
                    state["todo_context"],
                    extensions=["extra", "nl2br"],
                )
                st.markdown(html_content, unsafe_allow_html=True)

        if state.get("analysis"):
            with st.expander("🧠 Strategic Analysis", expanded=True):
                st.markdown("**Strategist Reasoning:**")
                html_content = markdown.markdown(
                    state["analysis"], extensions=["extra", "nl2br"]
                )
                st.markdown(html_content, unsafe_allow_html=True)

                confidence = state.get("confidence", 0.0)
                st.metric("Confidence Score", f"{confidence:.2%}")

                if confidence < 0.75:
                    st.warning("⚠️ Below threshold (0.75) - requesting clarification")
                else:
                    st.success("✅ Above threshold - proceeding to planning")

                if state.get("missing_info"):
                    st.markdown("**Missing Information:**")
                    st.info(state["missing_info"])

        if state.get("raw_strategist_response"):
            with st.expander("🔍 Debug: Raw Strategist Response", expanded=False):
                st.markdown("**Raw LLM Output:**")
                st.code(state["raw_strategist_response"], language="json")

                st.markdown("**Response Analysis:**")
                raw_resp = state["raw_strategist_response"]
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
