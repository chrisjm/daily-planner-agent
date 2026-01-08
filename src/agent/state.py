"""Agent state definition."""

import operator
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State definition for the Executive Function Agent."""

    messages: Annotated[List[BaseMessage], operator.add]
    calendar_context: str
    todo_context: str
    user_intent: str
    analysis: str
    confidence: float
    missing_info: str
    final_schedule: str
    debug_info: str
    raw_strategist_response: str
    suggested_events: List[dict]
    approved_event_ids: List[str]
    pending_calendar_additions: bool
