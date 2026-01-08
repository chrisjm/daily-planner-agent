# Architecture Documentation

## Overview

The Executive Function Agent is built with a modular Python architecture that separates concerns into logical packages.

## Module Structure

### `src/agent/` - Core Agent Logic

**state.py**

- Defines `AgentState` TypedDict with all state fields
- Used by LangGraph for state management

**prompts.py**

- Contains all LLM prompts as string constants
- `STRATEGIST_PROMPT`: Analyzes context and outputs confidence
- `CLARIFICATION_PROMPT`: Generates clarification questions
- `PLANNER_PROMPT`: Creates final schedule

**nodes.py**

- Implements all node functions for the state machine
- `gather_context()`: Fetches Calendar + Todoist data
- `strategist()`: Analyzes with confidence scoring
- `check_confidence()`: Router function (threshold: 0.95)
- `ask_clarification()`: Generates questions
- `planner()`: Creates structured JSON schedule with event suggestions
- `add_approved_events()`: Adds user-selected events to Google Calendar

**utils.py**

- `convert_schedule_to_events()`: Converts schedule JSON to calendar event suggestions
- Filters out breaks and enriches events with metadata

**graph.py**

- Constructs the LangGraph state machine
- `create_graph()`: Returns compiled graph
- Defines edges and conditional routing

### `src/integrations/` - External Services

**calendar.py**

- Google Calendar OAuth authentication with read/write scopes
- `get_google_calendar_service()`: Returns authenticated service
- `get_calendar_events()`: Fetches and formats events with rich context
- `add_calendar_event()`: Adds a single event to Google Calendar with metadata
- `get_calendar_timezone()`: Retrieves calendar timezone for proper event creation

**todoist.py**

- Todoist API integration
- `get_todoist_tasks()`: Fetches tasks with priority, labels, descriptions

**parsers.py**

- `parse_event_title()`: Extracts category and clean description
- Supports multiple formats: "CATEGORY: Event", "[category]", "category: tag"

### `src/config/` - Configuration

**settings.py**

- All configuration constants in one place
- Calendar settings (lookback/lookahead days)
- Confidence threshold
- LLM model names
- API keys (loaded from environment)
- Text truncation limits

### `src/ui/` - User Interface

**streamlit_app.py**

- Streamlit application logic
- `run_app()`: Main application function
- Handles conversation state and graph invocation
- Renders chat interface and schedule output

## Data Flow

```
User Input
    ↓
gather_context → [Calendar API + Todoist API]
    ↓
strategist → [Gemini 2.5 Pro analyzes context]
    ↓
check_confidence
    ├─ < 0.95 → ask_clarification → [Gemini 2.0 Flash] → END (user responds)
    └─ ≥ 0.95 → planner → [Gemini 2.5 Pro] → JSON Schedule + Event Suggestions → END
                                                    ↓
                                            User Selects Events
                                                    ↓
                                            add_approved_events → [Calendar API] → END
```

## State Management

The `AgentState` flows through all nodes:

- **messages**: Conversation history
- **calendar_context**: Formatted calendar events
- **todo_context**: Formatted tasks
- **user_intent**: Original user query
- **analysis**: LLM reasoning
- **confidence**: 0.0-1.0 score
- **missing_info**: What's needed for 100% confidence
- **schedule_json**: Structured schedule as list of time blocks
- **schedule_metadata**: Metadata about scheduling strategy
- **suggested_events**: Calendar event suggestions generated from schedule
- **approved_event_ids**: IDs of events user wants to add to calendar
- **pending_calendar_additions**: Boolean flag for pending calendar operations
- **cycle_count**: Number of graph execution cycles
- **clarification_count**: Number of clarification attempts

## Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Configuration Centralization**: All settings in `config/settings.py`
3. **Prompt Externalization**: Prompts separate from logic
4. **Rich Context**: Extract all unstructured data from sources
5. **Structured Output**: JSON-based schedule format for programmatic processing
6. **User Control**: Explicit approval required before calendar modifications
7. **Testability**: Each module can be tested independently
8. **Extensibility**: Easy to add new integrations or nodes

## Adding New Features

### New Integration

1. Create new file in `src/integrations/`
2. Add to `__init__.py` exports
3. Call from `gather_context()` node

### New Node

1. Add function to `src/agent/nodes.py`
2. Register in `src/agent/graph.py`
3. Add edges and routing logic

### New Configuration

1. Add constant to `src/config/settings.py`
2. Export in `__init__.py`
3. Import where needed

## Schedule Structure

The planner generates a structured JSON schedule with the following format:

```json
{
  "schedule": [
    {
      "start_time": "YYYY-MM-DD HH:MM",
      "end_time": "YYYY-MM-DD HH:MM",
      "title": "Task title",
      "priority": "P1|P2|P3|P4",
      "type": "work|meeting|break|personal",
      "energy_level": "high|medium|low",
      "cognitive_load": "high|medium|low",
      "tags": ["tag1", "tag2"],
      "rationale": "Why this task is scheduled at this time"
    }
  ],
  "metadata": {
    "scheduling_strategy": "Overall approach and considerations"
  }
}
```

## Calendar Event Addition

1. **Schedule Generation**: Planner creates JSON schedule
2. **Event Conversion**: `convert_schedule_to_events()` transforms schedule blocks into event suggestions (excludes breaks)
3. **User Selection**: UI presents events for user approval
4. **Calendar Addition**: `add_approved_events()` adds selected events with rich metadata
5. **Context Refresh**: Calendar context updated to include new events

## Testing Strategy

- **Unit Tests**: Test individual functions (parsers, formatters, event converters)
- **Integration Tests**: Test API connections with mocks
- **End-to-End Tests**: Test full graph execution including calendar additions
- **Prompt Tests**: Validate LLM outputs against expected JSON formats
