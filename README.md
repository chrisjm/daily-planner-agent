# Executive Function Agent 🧠

An AI-powered daily planning consultant that autonomously gathers your schedule and task context, strategizes based on your intent, and delivers a personalized daily plan.

## Features

- **Smart Context Gathering**: Automatically fetches events from Google Calendar and tasks from Todoist
- **Strategic Analysis**: Uses Gemini 2.5 Pro to analyze momentum (past events) vs constraints (future events) vs intent (your goals)
- **Confidence-Based Clarification**: Only asks questions when confidence is below 95%
- **Interactive Planning**: Streamlit UI for conversational planning experience
- **Calendar Integration**: Add approved schedule items directly to Google Calendar with rich metadata
- **Structured Scheduling**: JSON-based schedule output with time blocks, priorities, and energy levels
- **LangGraph State Machine**: Robust workflow orchestration with conditional routing

## Architecture

The agent operates as a state machine with the following flow:

```
Gather Context → Strategist → Check Confidence → [Ask Clarification OR Planner]
                                    ↓                        ↓
                                  < 0.95                  >= 0.95
                                    ↓                        ↓
                              Loop Back              Generate Schedule
                                                            ↓
                                                    User Approves Events
                                                            ↓
                                                    Add to Calendar
```

### Nodes

1. **gather_context**: Parallel fetch from Google Calendar (past 3 days + future 7 days) and Todoist
2. **strategist**: Analyzes context with Gemini 2.5 Pro, outputs confidence score
3. **check_confidence**: Routes based on 0.95 threshold
4. **ask_clarification**: Generates specific question using Gemini 2.0 Flash
5. **planner**: Creates structured JSON schedule with Gemini 2.5 Pro, including time blocks with priorities, energy levels, and rationale
6. **add_approved_events**: Adds user-selected events to Google Calendar with rich metadata

## Setup

### Prerequisites

- Python 3.12+
- Google Cloud Project with Calendar API enabled (read/write access)
- Todoist API access
- Google Gemini API key

### Installation

1. **Clone and install dependencies**:

   ```bash
   cd daily-planner-agent
   uv sync
   ```

2. **Set up Google Calendar OAuth**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials (Desktop App or Web App)
   - Download `credentials.json` to project root
   - **Important**: Ensure the OAuth scope includes calendar write permissions

3. **Get Todoist API Token**:

   - Go to [Todoist Settings → Integrations](https://todoist.com/prefs/integrations)
   - Copy your API token

4. **Get Google Gemini API Key**:

   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create API key

5. **Configure environment**:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```bash
   GOOGLE_API_KEY=your_gemini_api_key_here
   TODOIST_API_KEY=your_todoist_token_here
   GOOGLE_APPLICATION_CREDENTIALS=credentials.json
   ```

### First Run Authentication

On first run, the app will open a browser window for Google Calendar OAuth:

```bash
uv run streamlit run app.py
```

1. Browser will open automatically
2. Sign in to your Google account
3. Grant calendar read permissions
4. Token will be saved to `token.pickle` for future use

## Usage

### Streamlit UI

```bash
uv run streamlit run app.py
```

Navigate to `http://localhost:8501` and start planning:

**Example queries:**

- "Help me plan tomorrow focusing on deep work"
- "I need to prepare for my presentation next week"
- "Balance my workload for the next 3 days"

**Workflow:**

1. Enter your planning request
2. Agent gathers context and analyzes your schedule
3. Review the generated schedule with time blocks
4. Select which events to add to your calendar
5. Events are added with full metadata (priority, energy level, rationale)

### Command Line Testing

Test the graph directly:

```bash
uv run python graph.py
```

## Project Structure

```
daily-planner-agent/
├── src/
│   ├── agent/
│   │   ├── state.py       # AgentState TypedDict
│   │   ├── prompts.py     # LLM prompts
│   │   ├── nodes.py       # Node functions
│   │   └── graph.py       # LangGraph construction
│   ├── integrations/
│   │   ├── calendar.py    # Google Calendar API
│   │   ├── todoist.py     # Todoist API
│   │   └── parsers.py     # Event/task parsing
│   ├── config/
│   │   └── settings.py    # Configuration constants
│   └── ui/
│       └── streamlit_app.py  # Streamlit interface
├── app.py                 # Entry point
├── .env                   # Environment variables (gitignored)
├── .env.example           # Template for environment setup
├── credentials.json       # Google OAuth credentials (gitignored)
├── token.pickle           # OAuth token cache (gitignored)
├── pyproject.toml         # Dependencies
└── README.md              # This file
```

## How It Works

### Data Strategy

**Google Calendar**:

- Lookback (3 days): Establishes energy "momentum" (e.g., "Too much coding yesterday")
- Lookahead (7 days): Establishes hard constraints
- Extracts `category: ` tags from event titles

**Todoist**:

- **Urgent**: Due date ≤ today
- **Backlog**: No due date (source for matching user intent)

### LLM Strategy

**Strategist** (Gemini 2.5 Pro):

- Analyzes momentum vs constraints vs intent
- Returns JSON with confidence score (0.0-1.0)
- Identifies missing information

**Clarification** (Gemini 2.0 Flash):

- Generates single specific question
- Fast routing and parsing

**Planner** (Gemini 2.5 Pro):

- Creates structured JSON schedule with time blocks
- Each block includes: title, time range, priority, type, energy level, cognitive load, tags, and rationale
- Balances energy, respects constraints, aligns with user intent
- Automatically generates event suggestions from schedule

**Calendar Integration**:

- Converts schedule blocks to calendar event suggestions
- User selects which events to add
- Events added with rich metadata in description
- Calendar context refreshed after additions

## Customization

### Adjust Configuration

Edit `src/config/settings.py`:

```python
# Calendar settings
LOOKBACK_DAYS = 3  # Change lookback window
LOOKAHEAD_DAYS = 7  # Change lookahead window

# Agent confidence threshold
CONFIDENCE_THRESHOLD = 0.95  # Adjust threshold

# LLM model names
STRATEGIST_MODEL = "gemini-2.5-pro"
CLARIFICATION_MODEL = "gemini-2.0-flash-exp"
PLANNER_MODEL = "gemini-2.5-pro"
```

### Modify Prompts

Edit `src/agent/prompts.py` to customize LLM prompts for strategist, clarification, and planner nodes.

## Troubleshooting

### "GOOGLE_APPLICATION_CREDENTIALS not set"

Ensure `credentials.json` exists and `.env` points to it correctly.

### "Error fetching calendar events"

Run OAuth flow again by deleting `token.pickle` and restarting the app.

### "Error fetching Todoist tasks"

Verify your `TODOIST_API_KEY` in `.env` is correct.

### Import errors

Ensure all dependencies are installed:

```bash
uv sync
```

## Tech Stack

- **Package Manager**: `uv`
- **Orchestration**: `LangGraph`
- **LLMs**: Google Gemini (2.5 Pro + 2.0 Flash)
- **UI**: Streamlit
- **APIs**: Google Calendar API, Todoist API

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

---

Built with ❤️ using LangGraph and Gemini
