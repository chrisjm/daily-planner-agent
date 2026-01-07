"""LangGraph state machine construction."""

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    gather_context,
    strategist,
    check_confidence,
    ask_clarification,
    planner,
)


def create_graph():
    """Build the LangGraph state machine for the Executive Function Agent."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("gather_context", gather_context)
    workflow.add_node("strategist", strategist)
    workflow.add_node("ask_clarification", ask_clarification)
    workflow.add_node("planner", planner)

    # Set entry point
    workflow.set_entry_point("gather_context")

    # Add edges
    workflow.add_edge("gather_context", "strategist")

    # Conditional routing based on confidence
    workflow.add_conditional_edges(
        "strategist",
        check_confidence,
        {"ask_clarification": "ask_clarification", "planner": "planner"},
    )

    # Terminal edges
    workflow.add_edge("ask_clarification", END)
    workflow.add_edge("planner", END)

    return workflow.compile()
