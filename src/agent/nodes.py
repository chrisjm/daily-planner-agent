"""Agent node functions for LangGraph state machine."""

import json
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import AgentState
from .prompts import STRATEGIST_PROMPT, CLARIFICATION_PROMPT, PLANNER_PROMPT
from ..config.settings import (
    GOOGLE_API_KEY,
    STRATEGIST_MODEL,
    CLARIFICATION_MODEL,
    PLANNER_MODEL,
    CONFIDENCE_THRESHOLD,
    LOOKBACK_DAYS,
    LOOKAHEAD_DAYS,
)
from ..integrations.calendar import get_calendar_events
from ..integrations.todoist import get_todoist_tasks


def gather_context(state: AgentState) -> AgentState:
    """Node: Gather context from Calendar and Todoist."""
    print("📊 Gathering context from Calendar and Todoist...")

    calendar_context = get_calendar_events(
        lookback=LOOKBACK_DAYS, lookahead=LOOKAHEAD_DAYS
    )
    todo_context = get_todoist_tasks()

    return {
        **state,
        "calendar_context": calendar_context,
        "todo_context": todo_context,
    }


def strategist(state: AgentState) -> AgentState:
    """Node: Analyze context and user intent, output confidence score."""
    print("🧠 Strategist analyzing context...")

    llm = ChatGoogleGenerativeAI(model=STRATEGIST_MODEL, api_key=GOOGLE_API_KEY)

    conversation_history = "\n".join(
        [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in state["messages"]
        ]
    )
    if not conversation_history:
        conversation_history = "(No previous conversation)"

    prompt = STRATEGIST_PROMPT.format(
        user_intent=state["user_intent"],
        calendar_context=state["calendar_context"],
        todo_context=state["todo_context"],
        conversation_history=conversation_history,
    )

    response = llm.invoke([HumanMessage(content=prompt)])

    print("📝 Raw strategist response (first 500 chars):")
    print(f"   {response.content[:500]}")
    print(f"   Response type: {type(response.content)}")
    print(f"   Response length: {len(response.content)} chars")

    try:
        # Try to extract JSON from markdown code blocks if present
        content = response.content.strip()
        if content.startswith("```"):
            # Extract JSON from code block
            lines = content.split("\n")
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    json_lines.append(line)
            content = "\n".join(json_lines)
            print(f"   Extracted from code block: {content[:200]}")

        result = json.loads(content)
        confidence = float(result.get("confidence", 0.0))
        analysis = result.get("analysis", "")
        missing_info = result.get("missing_info", "")
        print("✅ Successfully parsed JSON")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️  Error parsing strategist response: {e}")
        print("   Full response content:")
        print(f"   {response.content}")
        confidence = 0.5
        analysis = response.content
        missing_info = (
            "Unable to parse strategist output - LLM did not return valid JSON"
        )

    print(f"   Confidence: {confidence:.2f}")

    return {
        **state,
        "confidence": confidence,
        "analysis": analysis,
        "missing_info": missing_info,
        "raw_strategist_response": response.content,
    }


def check_confidence(state: AgentState) -> str:
    """Router: Check if confidence is high enough to proceed to planning."""
    confidence = state.get("confidence", 0.0)

    if confidence >= CONFIDENCE_THRESHOLD:
        print("✅ Confidence high enough, proceeding to planner")
        return "planner"
    else:
        print(f"❓ Confidence too low ({confidence:.2f}), asking for clarification")
        return "ask_clarification"


def ask_clarification(state: AgentState) -> AgentState:
    """Node: Generate a clarification question based on missing_info."""
    print("💬 Generating clarification question...")

    llm = ChatGoogleGenerativeAI(model=CLARIFICATION_MODEL, api_key=GOOGLE_API_KEY)

    conversation_history = "\n".join(
        [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in state["messages"]
        ]
    )
    if not conversation_history:
        conversation_history = "(No previous conversation)"

    prompt = CLARIFICATION_PROMPT.format(
        missing_info=state["missing_info"],
        user_intent=state["user_intent"],
        conversation_history=conversation_history,
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    question = response.content

    print(f"   Question: {question}")

    return {**state, "messages": [AIMessage(content=question)]}


def planner(state: AgentState) -> AgentState:
    """Node: Generate final Markdown schedule."""
    print("📅 Generating final schedule...")

    llm = ChatGoogleGenerativeAI(model=PLANNER_MODEL, api_key=GOOGLE_API_KEY)

    conversation_history = "\n".join(
        [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in state["messages"]
        ]
    )

    prompt = PLANNER_PROMPT.format(
        user_intent=state["user_intent"],
        calendar_context=state["calendar_context"],
        todo_context=state["todo_context"],
        analysis=state["analysis"],
        conversation_history=conversation_history,
    )

    print(f"   Using analysis: {state['analysis'][:200]}...")
    print(f"   Confidence was: {state.get('confidence', 0.0):.2f}")

    response = llm.invoke([HumanMessage(content=prompt)])
    schedule = response.content

    print(f"✅ Schedule generated ({len(schedule)} chars)")

    return {
        **state,
        "final_schedule": schedule,
        "messages": [AIMessage(content=schedule)],
    }
