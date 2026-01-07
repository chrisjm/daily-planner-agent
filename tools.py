import os
from datetime import datetime, timedelta
from typing import Dict
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from todoist_api_python.api import TodoistAPI
import pickle

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_google_calendar_service():
    """Authenticate and return Google Calendar service."""
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not credentials_path:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)


def get_calendar_events(lookback: int = 3, lookahead: int = 7) -> str:
    """
    Fetch calendar events from lookback days ago to lookahead days in the future.

    Args:
        lookback: Number of days to look back (default: 3)
        lookahead: Number of days to look ahead (default: 7)

    Returns:
        Formatted text summary of calendar events
    """
    try:
        service = get_google_calendar_service()

        now = datetime.utcnow()
        time_min = (now - timedelta(days=lookback)).isoformat() + "Z"
        time_max = (now + timedelta(days=lookahead)).isoformat() + "Z"

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            return "No calendar events found."

        past_events = []
        future_events = []

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            event_time = datetime.fromisoformat(start.replace("Z", "+00:00"))

            summary = event.get("summary", "No title")
            category = extract_category(summary)

            event_str = f"- {event_time.strftime('%Y-%m-%d %H:%M')}: {summary}"
            if category:
                event_str += f" [category: {category}]"

            if event_time < now:
                past_events.append(event_str)
            else:
                future_events.append(event_str)

        result = []
        if past_events:
            result.append(f"**Past Events (Momentum - Last {lookback} days):**")
            result.extend(past_events)

        if future_events:
            result.append(f"\n**Future Events (Constraints - Next {lookahead} days):**")
            result.extend(future_events)

        return "\n".join(result)

    except Exception as e:
        return f"Error fetching calendar events: {str(e)}"


def extract_category(title: str) -> str:
    """Extract category tag from event title (e.g., 'Meeting category: work' -> 'work')."""
    import re

    match = re.search(r"category:\s*(\S+)", title, re.IGNORECASE)
    return match.group(1) if match else ""


def get_todoist_tasks() -> str:
    """
    Fetch Todoist tasks and categorize them as Urgent or Backlog.

    Returns:
        Formatted text summary of tasks
    """
    try:
        api_key = os.getenv("TODOIST_API_KEY")
        if not api_key:
            raise ValueError("TODOIST_API_KEY not set in .env")

        api = TodoistAPI(api_key)
        tasks = api.get_tasks()

        if not tasks:
            return "No Todoist tasks found."

        today = datetime.now().date()
        urgent_tasks = []
        backlog_tasks = []

        for task in tasks:
            task_str = f"- {task.content}"
            if task.description:
                task_str += f" (Note: {task.description})"

            if task.due:
                due_date = datetime.fromisoformat(task.due.date).date()
                task_str += f" [Due: {task.due.date}]"

                if due_date <= today:
                    urgent_tasks.append(task_str)
                else:
                    backlog_tasks.append(task_str)
            else:
                backlog_tasks.append(task_str)

        result = []
        if urgent_tasks:
            result.append("**Urgent Tasks (Due Today or Overdue):**")
            result.extend(urgent_tasks)

        if backlog_tasks:
            result.append("\n**Backlog Tasks (No Due Date or Future):**")
            result.extend(backlog_tasks)

        return "\n".join(result)

    except Exception as e:
        return f"Error fetching Todoist tasks: {str(e)}"


def gather_all_context(lookback: int = 3, lookahead: int = 7) -> Dict[str, str]:
    """
    Gather all context from Calendar and Todoist in parallel.

    Args:
        lookback: Number of days to look back for calendar
        lookahead: Number of days to look ahead for calendar

    Returns:
        Dictionary with calendar_context and todo_context
    """
    calendar_context = get_calendar_events(lookback, lookahead)
    todo_context = get_todoist_tasks()

    return {"calendar_context": calendar_context, "todo_context": todo_context}
