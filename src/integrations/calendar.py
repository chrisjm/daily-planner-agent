"""Google Calendar integration."""

import os
import pickle
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config.settings import (
    CALENDAR_SCOPES,
    TOKEN_PICKLE_PATH,
    GOOGLE_APPLICATION_CREDENTIALS,
    EVENT_DESCRIPTION_MAX_LENGTH,
    LOOKBACK_DAYS,
    LOOKAHEAD_DAYS,
    OAUTH_REDIRECT_PORT,
)
from .parsers import parse_event_title


def get_google_calendar_service():
    """Authenticate and return Google Calendar service."""
    creds = None

    if os.path.exists(TOKEN_PICKLE_PATH):
        with open(TOKEN_PICKLE_PATH, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not GOOGLE_APPLICATION_CREDENTIALS:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env")

            # Check if using Web or Desktop credentials
            with open(GOOGLE_APPLICATION_CREDENTIALS, "r") as f:
                cred_data = json.load(f)

            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_APPLICATION_CREDENTIALS, CALENDAR_SCOPES
            )

            # Use appropriate OAuth flow based on credential type
            if "web" in cred_data:
                # Web application: use fixed port with open_browser=True
                creds = flow.run_local_server(
                    port=OAUTH_REDIRECT_PORT,
                    open_browser=True,
                    authorization_prompt_message="Please visit this URL: {url}",
                    success_message="Authentication successful! You can close this window.",
                )
            else:
                # Desktop application: use dynamic port
                creds = flow.run_local_server(port=0)

        with open(TOKEN_PICKLE_PATH, "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)


def get_calendar_events(
    lookback: int = LOOKBACK_DAYS, lookahead: int = LOOKAHEAD_DAYS
) -> str:
    """
    Fetch calendar events from lookback days ago to lookahead days in the future.

    Args:
        lookback: Number of days to look back (default from config)
        lookahead: Number of days to look ahead (default from config)

    Returns:
        Formatted text summary of calendar events with rich context
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
            description = event.get("description", "")
            location = event.get("location", "")

            category, clean_title = parse_event_title(summary)

            # Build rich event string with all available data
            event_str = f"- {event_time.strftime('%Y-%m-%d %H:%M')}: "
            if category:
                event_str += f"[{category}] "
            event_str += clean_title

            # Add location if present
            if location:
                event_str += f" @ {location}"

            # Add description if present (truncate if too long)
            if description:
                desc_preview = (
                    description[:EVENT_DESCRIPTION_MAX_LENGTH] + "..."
                    if len(description) > EVENT_DESCRIPTION_MAX_LENGTH
                    else description
                )
                event_str += f" | {desc_preview}"

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
