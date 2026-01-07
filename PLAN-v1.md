### **Project: The Executive Function Agent (Coding Agent Spec)**

**Goal:** Build a local "Consultant" agent that autonomously gathers schedule/task context, strategizes based on user intent, and delivers a daily plan. It loops for clarification only if confidence is low.

**Tech Stack:**

- **Manager:** `uv` (Python 3.10+)
- **Orchestration:** `LangGraph`
- **LLMs:**
- **Reasoning (Strategist/Planner):** `gemini-1.5-pro`
- **Speed (Router/Parsing):** `gemini-2.0-flash`

- **Env:** `.env` (Keys: `GOOGLE_API_KEY`, `TODOIST_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`)
- **UI:** `Streamlit`

---

### **1. Architecture: The Consultant State Machine**

The graph operates as a loop: **Gather -> Strategize -> Check Confidence -> (Loop or Finalize)**.

1. **`gather_context`**: Parallel tool calls to Calendar (Past/Future) & Todoist.
2. **`strategist`**: (`gemini-1.5-pro`) Analyzes "Momentum" (Past) vs. "Constraints" (Future) vs. "Intent" (User Query). Outputs JSON `confidence` score.
3. **`check_confidence`**:

- **< 0.95**: Route to `ask_clarification`.
- **>= 0.95**: Route to `planner`.

4. **`ask_clarification`**: (`gemini-2.0-flash`) Generates single specific question -> Updates State -> Loops back to `strategist`.
5. **`planner`**: (`gemini-1.5-pro`) Generates final Markdown schedule.

---

### **2. Data Strategy (Inputs)**

- **Google Calendar**:
- _Function:_ `get_calendar_events(lookback=3, lookahead=7)`
- _Parsing:_ Extract `category: [tag]` from event titles.
- _Purpose:_ Lookback establishes energy "momentum" (e.g., "Too much coding yesterday"); Lookahead establishes hard constraints.

- **Todoist**:
- _Function:_ `get_todoist_tasks()`
- _Parsing:_
- **Urgent:** Due Date <= Today.
- **Backlog:** No Due Date (Source for matching "Intent").

---

### **3. Implementation Specs**

#### **A. Dependencies (`pyproject.toml`)**

THIS IS ALREADY COMPLETE

```bash
uv init
uv add langchain-google-genai langgraph streamlit google-api-python-client todoist-api-python python-dotenv

```

#### **B. State Definition (`graph.py`)**

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    calendar_context: str  # Parsed text summary of past/future
    todo_context: str      # Parsed text of Urgent/Backlog
    user_intent: str       # Initial user query
    analysis: str          # LLM internal reasoning
    confidence: float      # 0.0 to 1.0
    missing_info: str      # What prevents 100% confidence?
    final_schedule: str    # Markdown output

```

#### **C. LLM Strategy**

- **Strategist Node Prompt (`gemini-1.5-pro`):**

  > "You are an Executive Strategist. Analyze the `user_intent` against `calendar_context` (hard constraints) and `todo_context`. Identify if the user's request conflicts with reality. Return JSON: `{'confidence': float, 'analysis': str, 'missing_info': str}`."

- **Clarification Node Prompt (`gemini-2.0-flash`):**
  > "Based on the `missing_info`, ask one concise question to resolve the ambiguity."

---

### **4. Execution Steps**

1. **Auth:** Acquire GCP `credentials.json` (OAuth Desktop App) and Todoist API Token.
2. **Sensors:** Implement `tools.py` to fetch and clean raw data.
3. **Brain:** Build `graph.py` with `StateGraph`. Mock LLM calls initially to verify routing logic.
4. **Interface:** Implement `app.py` with Streamlit to handle the chat loop and render the Markdown plan.
