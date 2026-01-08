"""Agent node functions for LangGraph state machine."""

import json
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import AgentState
from .prompts import (
    STRATEGIST_PROMPT,
    CLARIFICATION_PROMPT,
    PLANNER_PROMPT,
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
    current_cycle = state.get("cycle_count", 0) + 1
    message_count = len(state.get("messages", []))
    print(f"📊 Gathering context from Calendar and Todoist... (Cycle {current_cycle})")
    print(f"   📨 Message count at entry: {message_count}")

    calendar_context = get_calendar_events(
        lookback=LOOKBACK_DAYS, lookahead=LOOKAHEAD_DAYS
    )
    todo_context = get_todoist_tasks()

    # On first cycle, add the user's initial message
    # This prevents operator.add from duplicating it when passed in the initial state
    result = {
        **state,
        "calendar_context": calendar_context,
        "todo_context": todo_context,
        "cycle_count": current_cycle,
    }

    if current_cycle == 1 and state.get("user_intent"):
        from langchain_core.messages import HumanMessage

        print("   📨 Adding initial user message on first cycle")
        result["messages"] = [HumanMessage(content=state["user_intent"])]

    return result


def strategist(state: AgentState) -> AgentState:
    """Node: Analyze context and user intent, output confidence score."""
    message_count = len(state.get("messages", []))
    print("🧠 Strategist analyzing context...")
    print(f"   📨 Message count at entry: {message_count}")

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
    clarification_count = state.get("clarification_count", 0)
    max_clarifications = 2  # Limit to 2 clarification attempts

    if confidence >= CONFIDENCE_THRESHOLD:
        print("✅ Confidence high enough, proceeding to planner")
        return "planner"
    elif clarification_count >= max_clarifications:
        print(
            f"⚠️  Max clarification attempts reached ({clarification_count}), forcing planner with confidence {confidence:.2f}"
        )
        return "planner"
    else:
        print(
            f"❓ Confidence too low ({confidence:.2f}), asking for clarification (attempt {clarification_count + 1}/{max_clarifications})"
        )
        return "ask_clarification"


def ask_clarification(state: AgentState) -> AgentState:
    """Node: Generate a clarification question based on missing_info."""
    cycle = state.get("cycle_count", 1)
    print(f"💬 Generating clarification question... (Cycle {cycle})")

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

    # Increment clarification count
    clarification_count = state.get("clarification_count", 0) + 1
    message_count_before = len(state.get("messages", []))

    # Only add message if this is the first time through this node (cycle 1)
    # On subsequent cycles, the message is already in the state
    if cycle == 1:
        print(
            f"   📨 Adding clarification message (count before: {message_count_before})"
        )
        return {
            **state,
            "messages": state.get("messages", []) + [AIMessage(content=question)],
            "clarification_count": clarification_count,
        }
    else:
        print(
            f"   ⏭️  Skipping message addition (already added in cycle 1, count: {message_count_before})"
        )
        return {**state, "clarification_count": clarification_count}


def planner(state: AgentState) -> AgentState:
    """Node: Generate final schedule as structured JSON and create event suggestions."""
    cycle = state.get("cycle_count", 1)
    print(f"📅 Generating final schedule... (Cycle {cycle})")

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

    # Parse the JSON response
    schedule_data = {}
    schedule_json = []
    metadata = {}

    try:
        # Try to extract JSON from markdown code blocks if present
        content = full_response.strip()
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

        schedule_data = json.loads(content)
        schedule_json = schedule_data.get("schedule", [])
        metadata = schedule_data.get("metadata", {})

        print(f"   Parsed {len(schedule_json)} time blocks from schedule")
        print(f"   Metadata: {metadata.get('scheduling_strategy', 'N/A')[:100]}...")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️  Could not parse schedule JSON: {e}")
        print(f"   Full response: {full_response[:500]}")
        schedule_json = []
        metadata = {}

    # Generate event suggestions directly from schedule JSON
    from .utils import convert_schedule_to_events

    suggested_events = convert_schedule_to_events(schedule_json)
    print(f"   Generated {len(suggested_events)} event suggestions from schedule")

    # Store the full structured data
    if cycle == 1:
        return {
            **state,
            "schedule_json": schedule_json,
            "schedule_metadata": metadata,
            "suggested_events": suggested_events,
            "pending_calendar_additions": len(suggested_events) > 0,
            "final_schedule": "",  # No longer using markdown
        }
    else:
        print("   ⏭️  Skipping state update (already updated in cycle 1)")
        return {
            **state,
            "schedule_json": schedule_json,
            "schedule_metadata": metadata,
            "suggested_events": suggested_events,
            "pending_calendar_additions": len(suggested_events) > 0,
            "final_schedule": "",
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

        # Prepare event data for calendar API with rich metadata
        description_parts = [
            f"Priority: {event.get('priority', 'N/A')}",
            f"Type: {event.get('type', 'N/A')}",
            f"Energy Level: {event.get('energy_level', 'N/A')}",
            f"Cognitive Load: {event.get('cognitive_load', 'N/A')}",
        ]

        if event.get("tags"):
            tags_str = ", ".join(event["tags"])
            description_parts.append(f"Tags: {tags_str}")

        description_parts.append(f"\nRationale: {event.get('rationale', '')}")
        description_parts.append(
            f"\nSource: {event.get('source_task', 'Planned schedule')}"
        )

        event_data = {
            "title": event["title"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "description": "\n".join(description_parts),
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

    cycle = state.get("cycle_count", 1)

    # Only add message if this is the first time through this node
    if cycle == 1:
        return {
            **state,
            "calendar_context": updated_calendar_context,
            "pending_calendar_additions": False,
            "suggested_events": [],
            "approved_event_ids": [],
            "messages": state.get("messages", []) + [AIMessage(content=message)],
        }
    else:
        print("   ⏭️  Skipping message addition (already added in cycle 1)")
        return {
            **state,
            "calendar_context": updated_calendar_context,
            "pending_calendar_additions": False,
            "suggested_events": [],
            "approved_event_ids": [],
        }
