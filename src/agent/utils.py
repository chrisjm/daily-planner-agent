"""Utility functions for the agent."""

from datetime import datetime


def convert_schedule_to_events(schedule_json):
    """Convert schedule JSON directly to event suggestions.

    Args:
        schedule_json: List of schedule time blocks from planner

    Returns:
        List of event suggestions ready for calendar addition
    """
    if not schedule_json:
        return []

    suggested_events = []

    for idx, time_block in enumerate(schedule_json):
        # Skip breaks - we don't want to add these to the calendar
        if time_block.get("type") == "break":
            continue

        # Calculate duration in minutes
        try:
            start = datetime.strptime(time_block["start_time"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(time_block["end_time"], "%Y-%m-%d %H:%M")
            duration_minutes = int((end - start).total_seconds() / 60)
        except (ValueError, KeyError):
            duration_minutes = 60  # Default to 60 minutes if parsing fails

        # Create event suggestion with all metadata from schedule
        event = {
            "id": f"evt_{idx + 1}",
            "title": time_block.get("title", "Untitled Task"),
            "start_time": time_block.get("start_time", ""),
            "end_time": time_block.get("end_time", ""),
            "duration_minutes": duration_minutes,
            "priority": time_block.get("priority", "P3"),
            "type": time_block.get("type", "work"),
            "energy_level": time_block.get("energy_level", "medium"),
            "cognitive_load": time_block.get("cognitive_load", "medium"),
            "rationale": time_block.get("rationale", "From your optimized schedule"),
            "tags": time_block.get("tags", []),
            "source_task": "Planned schedule",
        }

        suggested_events.append(event)

    return suggested_events
