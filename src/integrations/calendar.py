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
    LOOKBACK_DAYS,
    LOOKAHEAD_DAYS,
    OAUTH_REDIRECT_PORT,
)
from .parsers import parse_event_title
from .observability import (
    observe_integration,
    IntegrationLogger,
    IntegrationValidator,
)


# Initialize logger and validator for calendar integration
_logger = IntegrationLogger("calendar")
_validator = IntegrationValidator("calendar")


def get_calendar_timezone():
    """Get the timezone of the primary Google Calendar."""
    try:
        service = get_google_calendar_service()
        calendar = service.calendars().get(calendarId="primary").execute()
        timezone = calendar.get("timeZone", "UTC")
        _logger.debug(f"Calendar timezone: {timezone}")
        return timezone
    except Exception as e:
        _logger.warning(f"Could not get calendar timezone, defaulting to UTC: {e}")
        return "UTC"


def get_google_calendar_service():
    """Authenticate and return Google Calendar service."""
    _logger.info("Initializing Google Calendar service")
    creds = None

    if os.path.exists(TOKEN_PICKLE_PATH):
        _logger.debug(f"Loading credentials from {TOKEN_PICKLE_PATH}")
        with open(TOKEN_PICKLE_PATH, "rb") as token:
            creds = pickle.load(token)
        _logger.debug("Credentials loaded successfully")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            _logger.info("Refreshing expired credentials")
            creds.refresh(Request())
            _logger.info("Credentials refreshed successfully")
        else:
            if not GOOGLE_APPLICATION_CREDENTIALS:
                _logger.error("GOOGLE_APPLICATION_CREDENTIALS not set in .env")
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env")

            _logger.info(
                f"Starting OAuth flow with credentials from {GOOGLE_APPLICATION_CREDENTIALS}"
            )

            # Check if using Web or Desktop credentials
            try:
                with open(GOOGLE_APPLICATION_CREDENTIALS, "r") as f:
                    cred_data = json.load(f)
                _logger.debug(
                    f"Credential type: {'web' if 'web' in cred_data else 'desktop'}"
                )
            except FileNotFoundError:
                _logger.error(
                    f"Credentials file not found: {GOOGLE_APPLICATION_CREDENTIALS}"
                )
                raise
            except json.JSONDecodeError as e:
                _logger.error(f"Invalid JSON in credentials file: {str(e)}")
                raise

            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_APPLICATION_CREDENTIALS, CALENDAR_SCOPES
            )

            # Use appropriate OAuth flow based on credential type
            if "web" in cred_data:
                # Web application: use fixed port with open_browser=True
                _logger.info(f"Starting web OAuth flow on port {OAUTH_REDIRECT_PORT}")
                creds = flow.run_local_server(
                    port=OAUTH_REDIRECT_PORT,
                    open_browser=True,
                    authorization_prompt_message="Please visit this URL: {url}",
                    success_message="Authentication successful! You can close this window.",
                )
            else:
                # Desktop application: use dynamic port
                _logger.info("Starting desktop OAuth flow")
                creds = flow.run_local_server(port=0)

            _logger.info("OAuth flow completed successfully")

        _logger.debug(f"Saving credentials to {TOKEN_PICKLE_PATH}")
        with open(TOKEN_PICKLE_PATH, "wb") as token:
            pickle.dump(creds, token)
        _logger.debug("Credentials saved successfully")

    service = build("calendar", "v3", credentials=creds)
    _logger.info("Google Calendar service initialized successfully")
    return service


@observe_integration("calendar")
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

        # Use timezone-aware datetime to match Google Calendar API responses
        from datetime import timezone

        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=lookback)).isoformat()
        time_max = (now + timedelta(days=lookahead)).isoformat()

        _logger.info(
            "Fetching calendar events",
            lookback_days=lookback,
            lookahead_days=lookahead,
            time_min=time_min,
            time_max=time_max,
        )

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

        _logger.debug(f"Raw API response keys: {list(events_result.keys())}")

        events = events_result.get("items", [])
        _logger.info(f"Retrieved {len(events)} calendar events")

        # Validate API response
        validation = _validator.validate_api_response(events, expected_type=list)
        if not validation.valid:
            _logger.warning(f"API response validation failed: {validation.errors}")
        if validation.warnings:
            _logger.warning(f"API response warnings: {validation.warnings}")

        if not events:
            _logger.info("No calendar events found in the specified time range")
            return "No calendar events found."

        past_events = []
        future_events = []

        for idx, event in enumerate(events):
            try:
                start = event["start"].get("dateTime", event["start"].get("date"))

                # Validate datetime parsing
                datetime_validation = _validator.validate_datetime_parsing(start)
                if not datetime_validation.valid:
                    _logger.error(
                        "Failed to parse event datetime",
                        event_index=idx,
                        event_id=event.get("id"),
                        start_value=start,
                        errors=datetime_validation.errors,
                    )
                    continue

                # Parse datetime and ensure it's timezone-aware
                from datetime import timezone

                event_time = datetime.fromisoformat(start.replace("Z", "+00:00"))

                # If event is all-day (no timezone info), make it timezone-aware
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                    _logger.debug(
                        "Converted all-day event to timezone-aware",
                        event_index=idx,
                        event_id=event.get("id"),
                        original_start=start,
                    )

                summary = event.get("summary", "No title")
                location = event.get("location", "")

                # Get end time for duration calculation
                end = event["end"].get("dateTime", event["end"].get("date"))
                end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)

                _logger.debug(
                    f"Processing event {idx + 1}/{len(events)}",
                    event_id=event.get("id"),
                    summary=summary,
                    event_time_str=event_time.isoformat(),
                    event_time_tzinfo=str(event_time.tzinfo),
                    now_tzinfo=str(now.tzinfo),
                    has_location=bool(location),
                )

                category, clean_title = parse_event_title(summary)
            except KeyError as e:
                _logger.error(
                    "Missing required field in event",
                    event_index=idx,
                    event_id=event.get("id"),
                    missing_field=str(e),
                    event_keys=list(event.keys()),
                )
                continue
            except Exception as e:
                _logger.error(
                    "Error processing event",
                    event_index=idx,
                    event_id=event.get("id"),
                    error=str(e),
                )
                continue

            # Build rich event string with time range and location
            duration = end_time - event_time
            duration_mins = int(duration.total_seconds() / 60)

            event_str = f"- {event_time.strftime('%Y-%m-%d %H:%M')}-{end_time.strftime('%H:%M')} ({duration_mins}min): "
            if category:
                event_str += f"[{category}] "
            event_str += clean_title

            # Add location if present
            if location:
                event_str += f" @ {location}"

            # Categorize as past or future with detailed logging on comparison
            try:
                is_past = event_time < now
                if is_past:
                    past_events.append(event_str)
                else:
                    future_events.append(event_str)
            except TypeError as e:
                _logger.error(
                    "Datetime comparison failed",
                    event_index=idx,
                    event_id=event.get("id"),
                    event_time=event_time.isoformat(),
                    event_tzinfo=str(event_time.tzinfo),
                    now_time=now.isoformat(),
                    now_tzinfo=str(now.tzinfo),
                    error=str(e),
                )
                # Default to future if comparison fails
                future_events.append(event_str)

        result = []
        if past_events:
            result.append(f"**Past Events (Momentum - Last {lookback} days):**")
            result.extend(past_events)

        if future_events:
            result.append(f"\n**Future Events (Constraints - Next {lookahead} days):**")
            result.extend(future_events)

        final_result = "\n".join(result)
        _logger.info(
            "Calendar events formatted successfully",
            past_events_count=len(past_events),
            future_events_count=len(future_events),
            total_length=len(final_result),
        )

        return final_result

    except Exception as e:
        _logger.error(
            "Fatal error in get_calendar_events",
            error_type=type(e).__name__,
            error=str(e),
        )
        return f"Error fetching calendar events: {str(e)}"


@observe_integration("calendar")
def add_calendar_event(event_data: dict) -> dict:
    """
    Add a single event to Google Calendar.

    Args:
        event_data: Dictionary with keys:
            - title: Event title
            - start_time: Start time in "YYYY-MM-DD HH:MM" format
            - end_time: End time in "YYYY-MM-DD HH:MM" format
            - description: Optional event description

    Returns:
        Dictionary with:
            - success: Boolean indicating if event was added
            - event_id: Google Calendar event ID if successful
            - error: Error message if failed
    """
    try:
        service = get_google_calendar_service()

        # Get the calendar's timezone
        calendar_tz = get_calendar_timezone()

        # Parse datetime strings and make timezone-aware
        from datetime import datetime
        import pytz

        start_dt = datetime.strptime(event_data["start_time"], "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(event_data["end_time"], "%Y-%m-%d %H:%M")

        # Localize to calendar timezone
        tz = pytz.timezone(calendar_tz)
        start_dt = tz.localize(start_dt)
        end_dt = tz.localize(end_dt)

        # Build event object for Google Calendar API
        event = {
            "summary": event_data["title"],
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": calendar_tz,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": calendar_tz,
            },
        }

        # Add description if provided
        if event_data.get("description"):
            event["description"] = event_data["description"]

        _logger.info(
            "Adding event to calendar",
            title=event_data["title"],
            start_time=event_data["start_time"],
            end_time=event_data["end_time"],
        )

        # Insert event into calendar
        created_event = (
            service.events().insert(calendarId="primary", body=event).execute()
        )

        event_id = created_event.get("id")
        _logger.info(
            "Event added successfully",
            event_id=event_id,
            title=event_data["title"],
        )

        return {
            "success": True,
            "event_id": event_id,
            "error": None,
        }

    except Exception as e:
        _logger.error(
            "Error adding calendar event",
            error_type=type(e).__name__,
            error=str(e),
            event_data=event_data,
        )
        return {
            "success": False,
            "event_id": None,
            "error": str(e),
        }
