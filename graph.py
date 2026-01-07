import os
import json
import operator
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from tools import gather_all_context

load_dotenv()


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


def gather_context(state: AgentState) -> AgentState:
    """Node: Gather context from Calendar and Todoist."""
    print("📊 Gathering context from Calendar and Todoist...")

    context = gather_all_context(lookback=3, lookahead=7)

    return {
        **state,
        "calendar_context": context["calendar_context"],
        "todo_context": context["todo_context"],
    }


def strategist(state: AgentState) -> AgentState:
    """Node: Analyze context and user intent, output confidence score."""
    print("🧠 Strategist analyzing context...")

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro", api_key=os.getenv("GOOGLE_API_KEY")
    )

    prompt = f"""You are an Executive Strategist. Analyze the user's intent against their calendar and task context.

**User Intent:**
{state["user_intent"]}

**Calendar Context (Past/Future Events):**
{state["calendar_context"]}

**Todo Context (Urgent/Backlog Tasks):**
{state["todo_context"]}

**Previous Clarifications (if any):**
{chr(10).join([m.content for m in state["messages"] if isinstance(m, HumanMessage)])}

Analyze:
1. Does the user's request conflict with hard calendar constraints?
2. Are there enough details to create a concrete plan?
3. What information is missing to achieve 100% confidence?

Return ONLY a valid JSON object with this exact structure:
{{
    "confidence": <float between 0.0 and 1.0>,
    "analysis": "<your internal reasoning about momentum, constraints, and intent>",
    "missing_info": "<what prevents 100% confidence, or empty string if confident>"
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])

    try:
        result = json.loads(response.content)
        confidence = float(result.get("confidence", 0.0))
        analysis = result.get("analysis", "")
        missing_info = result.get("missing_info", "")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️  Error parsing strategist response: {e}")
        confidence = 0.5
        analysis = response.content
        missing_info = "Unable to parse strategist output"

    print(f"   Confidence: {confidence:.2f}")

    return {
        **state,
        "confidence": confidence,
        "analysis": analysis,
        "missing_info": missing_info,
    }


def check_confidence(state: AgentState) -> str:
    """Router: Check if confidence is high enough to proceed to planning."""
    confidence = state.get("confidence", 0.0)

    if confidence >= 0.95:
        print("✅ Confidence high enough, proceeding to planner")
        return "planner"
    else:
        print(f"❓ Confidence too low ({confidence:.2f}), asking for clarification")
        return "ask_clarification"


def ask_clarification(state: AgentState) -> AgentState:
    """Node: Generate a clarification question based on missing_info."""
    print("💬 Generating clarification question...")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp", api_key=os.getenv("GOOGLE_API_KEY")
    )

    prompt = f"""Based on the following missing information, ask ONE concise, specific question to resolve the ambiguity:

**Missing Information:**
{state["missing_info"]}

**User's Original Intent:**
{state["user_intent"]}

Generate a single, clear question that will help clarify the user's needs."""

    response = llm.invoke([HumanMessage(content=prompt)])
    question = response.content

    print(f"   Question: {question}")

    return {**state, "messages": [AIMessage(content=question)]}


def planner(state: AgentState) -> AgentState:
    """Node: Generate final Markdown schedule."""
    print("📅 Generating final schedule...")

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro", api_key=os.getenv("GOOGLE_API_KEY")
    )

    conversation_history = "\n".join(
        [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in state["messages"]
        ]
    )

    prompt = f"""You are an Executive Planner. Create a detailed, actionable daily schedule in Markdown format.

**User Intent:**
{state["user_intent"]}

**Calendar Context:**
{state["calendar_context"]}

**Todo Context:**
{state["todo_context"]}

**Strategic Analysis:**
{state["analysis"]}

**Conversation History:**
{conversation_history}

Create a schedule that:
1. Respects hard calendar constraints
2. Addresses urgent tasks
3. Balances energy based on past momentum
4. Aligns with user intent
5. Is realistic and achievable

Format as clean Markdown with time blocks, tasks, and brief rationale."""

    response = llm.invoke([HumanMessage(content=prompt)])
    schedule = response.content

    print("✅ Schedule generated")

    return {
        **state,
        "final_schedule": schedule,
        "messages": [AIMessage(content=schedule)],
    }


def create_graph():
    """Build the LangGraph state machine."""
    workflow = StateGraph(AgentState)

    workflow.add_node("gather_context", gather_context)
    workflow.add_node("strategist", strategist)
    workflow.add_node("ask_clarification", ask_clarification)
    workflow.add_node("planner", planner)

    workflow.set_entry_point("gather_context")

    workflow.add_edge("gather_context", "strategist")

    workflow.add_conditional_edges(
        "strategist",
        check_confidence,
        {"ask_clarification": "ask_clarification", "planner": "planner"},
    )

    workflow.add_edge("ask_clarification", END)
    workflow.add_edge("planner", END)

    return workflow.compile()


if __name__ == "__main__":
    graph = create_graph()

    initial_state = {
        "messages": [],
        "calendar_context": "",
        "todo_context": "",
        "user_intent": "Help me plan tomorrow focusing on deep work",
        "analysis": "",
        "confidence": 0.0,
        "missing_info": "",
        "final_schedule": "",
    }

    result = graph.invoke(initial_state)
    print("\n" + "=" * 60)
    print("FINAL RESULT:")
    print("=" * 60)
    print(result.get("final_schedule", "No schedule generated"))
