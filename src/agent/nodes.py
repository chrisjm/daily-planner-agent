"""Agent node functions for LangGraph state machine."""

import json
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import AgentState
from .prompts import (
    STRATEGIST_PROMPT,
    CLARIFICATION_PROMPT,
    PLANNER_PROMPT,
    SUGGEST_EVENTS_PROMPT,
)
from ..config.settings import (
    GOOGLE_API_KEY,
    STRATEGIST_MODEL,
    CLARIFICATION_MODEL,
    PLANNER_MODEL,
    CONFIDENCE_THRESHOLD,
    LOOKBACK_DAYS,
    LOOKAHEAD_DAYS,
)
from ..integrations.calendar import get_calendar_events, add_calendar_event
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
    full_response = response.content

    print(f"✅ Schedule generated ({len(full_response)} chars)")

    # Extract JSON schedule if present
    schedule_json = []
    markdown_schedule = full_response

    try:
        # Look for JSON code block
        if "```json" in full_response:
            json_start = full_response.find("```json") + 7
            json_end = full_response.find("```", json_start)
            json_str = full_response[json_start:json_end].strip()
            schedule_json = json.loads(json_str)

            # Extract markdown (everything after the JSON block)
            markdown_start = full_response.find("```", json_end) + 3
            markdown_schedule = full_response[markdown_start:].strip()

            print(f"   Extracted {len(schedule_json)} time blocks from schedule")
        else:
            print("   No JSON schedule found in response")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️  Could not parse schedule JSON: {e}")
        schedule_json = []

    return {
        **state,
        "final_schedule": markdown_schedule,
        "schedule_json": schedule_json,
        "messages": state["messages"] + [AIMessage(content=markdown_schedule)],
    }


def suggest_events(state: AgentState) -> AgentState:
    """Node: Generate event suggestions from scheduled time blocks."""
    print("💡 Generating event suggestions from schedule...")

    schedule_json = state.get("schedule_json", [])

    # If no schedule JSON, return empty suggestions
    if not schedule_json:
        print("   No schedule JSON available, skipping suggestions")
        return {
            **state,
            "suggested_events": [],
            "pending_calendar_additions": False,
        }

    llm = ChatGoogleGenerativeAI(model=PLANNER_MODEL, api_key=GOOGLE_API_KEY)

    # Convert schedule_json to string for prompt
    import json as json_module

    schedule_json_str = json_module.dumps(schedule_json, indent=2)

    prompt = SUGGEST_EVENTS_PROMPT.format(
        schedule_json=schedule_json_str,
        calendar_context=state["calendar_context"],
        user_intent=state["user_intent"],
    )

    response = llm.invoke([HumanMessage(content=prompt)])

    print("📝 Raw suggest_events response (first 500 chars):")
    print(f"   {response.content[:500]}")

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

        suggested_events = json.loads(content)

        if not isinstance(suggested_events, list):
            print("⚠️  Response is not a list, wrapping in array")
            suggested_events = []

        print(f"✅ Successfully parsed {len(suggested_events)} event suggestions")

    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️  Error parsing suggest_events response: {e}")
        print("   Full response content:")
        print(f"   {response.content}")
        suggested_events = []

    return {
        **state,
        "suggested_events": suggested_events,
        "pending_calendar_additions": len(suggested_events) > 0,
    }


def add_approved_events(state: AgentState) -> AgentState:
    """Node: Add user-approved events to Google Calendar."""
    print("📤 Adding approved events to calendar...")

    approved_ids = state.get("approved_event_ids", [])
    suggested_events = state.get("suggested_events", [])

    if not approved_ids:
        print("   No events approved by user")
        return {
            **state,
            "pending_calendar_additions": False,
            "messages": state["messages"]
            + [AIMessage(content="No events were selected to add to your calendar.")],
        }

    # Filter to only approved events
    events_to_add = [e for e in suggested_events if e.get("id") in approved_ids]

    print(f"   Adding {len(events_to_add)} approved events...")

    results = []
    success_count = 0
    failed_events = []

    for event in events_to_add:
        print(f"   Adding: {event['title']} at {event['start_time']}")

        # Prepare event data for calendar API
        event_data = {
            "title": event["title"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "description": f"Priority: {event.get('priority', 'N/A')}\nSource: {event.get('source_task', 'Suggested')}\n\nRationale: {event.get('rationale', '')}",
        }

        result = add_calendar_event(event_data)
        results.append(result)

        if result["success"]:
            success_count += 1
            print(f"   ✅ Added: {event['title']}")
        else:
            failed_events.append(event["title"])
            print(f"   ❌ Failed: {event['title']} - {result['error']}")

    # Build response message
    if success_count == len(events_to_add):
        message = f"✅ Successfully added {success_count} event(s) to your calendar!"
    elif success_count > 0:
        message = f"⚠️ Added {success_count} of {len(events_to_add)} events. Failed to add: {', '.join(failed_events)}"
    else:
        message = f"❌ Failed to add any events. Errors: {', '.join(failed_events)}"

    print(
        f"✅ Calendar additions complete: {success_count}/{len(events_to_add)} successful"
    )

    # Refresh calendar context to include new events
    print("🔄 Refreshing calendar context...")
    updated_calendar_context = get_calendar_events(
        lookback=LOOKBACK_DAYS, lookahead=LOOKAHEAD_DAYS
    )

    return {
        **state,
        "calendar_context": updated_calendar_context,
        "pending_calendar_additions": False,
        "suggested_events": [],
        "approved_event_ids": [],
        "messages": state["messages"] + [AIMessage(content=message)],
    }
