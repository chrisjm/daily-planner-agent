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
- `planner()`: Creates final Markdown schedule

**graph.py**

- Constructs the LangGraph state machine
- `create_graph()`: Returns compiled graph
- Defines edges and conditional routing

### `src/integrations/` - External Services

**calendar.py**

- Google Calendar OAuth authentication
- `get_google_calendar_service()`: Returns authenticated service
- `get_calendar_events()`: Fetches and formats events with rich context

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
    └─ ≥ 0.95 → planner → [Gemini 2.5 Pro] → Final Schedule
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
- **final_schedule**: Markdown output

## Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Configuration Centralization**: All settings in `config/settings.py`
3. **Prompt Externalization**: Prompts separate from logic
4. **Rich Context**: Extract all unstructured data from sources
5. **Testability**: Each module can be tested independently
6. **Extensibility**: Easy to add new integrations or nodes

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

## Testing Strategy

- **Unit Tests**: Test individual functions (parsers, formatters)
- **Integration Tests**: Test API connections with mocks
- **End-to-End Tests**: Test full graph execution
- **Prompt Tests**: Validate LLM outputs against expected formats
