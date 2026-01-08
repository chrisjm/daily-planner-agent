"""Schedule display and report generation components."""

from datetime import datetime


def render_schedule_from_json(schedule_json, metadata):
    """Render a user-friendly schedule display from JSON data."""
    if not schedule_json:
        return "No schedule generated."

    # Priority emoji mapping
    priority_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🔵", "P4": "⚪"}

    # Type emoji mapping
    type_emoji = {
        "work": "💼",
        "break": "☕",
        "meeting": "👥",
        "focus": "🎯",
        "admin": "📋",
        "personal": "🏠",
    }

    # Energy level emoji
    energy_emoji = {"high": "⚡", "medium": "🔋", "low": "🪫"}

    output = []

    # Add metadata summary
    if metadata:
        output.append("## 📊 Schedule Overview\n")
        if metadata.get("scheduling_strategy"):
            output.append(f"**Strategy:** {metadata['scheduling_strategy']}\n")
        if metadata.get("peak_energy_utilization"):
            output.append(
                f"**Energy Management:** {metadata['peak_energy_utilization']}\n"
            )

        stats = []
        if metadata.get("total_scheduled_minutes"):
            hours = metadata["total_scheduled_minutes"] / 60
            stats.append(f"⏱️ {hours:.1f} hours scheduled")
        if metadata.get("high_priority_count"):
            stats.append(f"🔴 {metadata['high_priority_count']} high-priority tasks")
        if metadata.get("break_count"):
            stats.append(f"☕ {metadata['break_count']} breaks")

        if stats:
            output.append(" • ".join(stats) + "\n")

        if metadata.get("flexibility_notes"):
            output.append(f"\n💡 **Flexibility:** {metadata['flexibility_notes']}\n")

        output.append("\n---\n")

    # Add schedule items
    output.append("## 📅 Your Schedule\n")

    for item in schedule_json:
        # Parse times for display
        try:
            start = datetime.strptime(item["start_time"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(item["end_time"], "%Y-%m-%d %H:%M")
            time_str = f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
        except (ValueError, KeyError):
            time_str = f"{item['start_time']} - {item['end_time']}"

        # Build the item display
        priority = priority_emoji.get(item.get("priority", ""), "")
        type_icon = type_emoji.get(item.get("type", ""), "")
        energy = energy_emoji.get(item.get("energy_level", ""), "")

        output.append(f"### {type_icon} {time_str}\n")
        output.append(f"**{priority} {item['title']}** {energy}\n")

        if item.get("description"):
            output.append(f"\n{item['description']}\n")

        # Add metadata in a compact format
        meta_items = []
        if item.get("priority"):
            meta_items.append(f"Priority: {item['priority']}")
        if item.get("cognitive_load"):
            meta_items.append(f"Cognitive Load: {item['cognitive_load']}")
        if item.get("tags"):
            tags_str = ", ".join(item["tags"])
            meta_items.append(f"Tags: {tags_str}")

        if meta_items:
            output.append(f"\n*{' • '.join(meta_items)}*\n")

        if item.get("rationale"):
            output.append(f"\n💭 *{item['rationale']}*\n")

        output.append("\n")

    return "\n".join(output)


def generate_final_report(schedule_json, metadata, added_events):
    """Generate a final schedule report including which events were added to calendar."""
    if not schedule_json:
        return "No schedule generated."

    output = []

    # Add header
    output.append("# 📋 Final Schedule Report\n")

    # Add metadata summary
    if metadata:
        if metadata.get("scheduling_strategy"):
            output.append(f"**Strategy:** {metadata['scheduling_strategy']}\n")

        stats = []
        if metadata.get("total_scheduled_minutes"):
            hours = metadata["total_scheduled_minutes"] / 60
            stats.append(f"⏱️ {hours:.1f} hours")
        if metadata.get("high_priority_count"):
            stats.append(f"🔴 {metadata['high_priority_count']} P1 tasks")
        if metadata.get("break_count"):
            stats.append(f"☕ {metadata['break_count']} breaks")

        if stats:
            output.append(" • ".join(stats) + "\n")

        output.append("\n")

    # Add calendar integration status
    if added_events:
        output.append(f"## ✅ Added to Calendar ({len(added_events)} events)\n")
        for event in added_events:
            try:
                start = datetime.strptime(event["start_time"], "%Y-%m-%d %H:%M")
                time_str = start.strftime("%I:%M %p")
            except (ValueError, KeyError):
                time_str = event.get("start_time", "")

            output.append(f"- **{time_str}** - {event.get('title', 'Untitled')}\n")
        output.append("\n")

    # Add condensed schedule view
    output.append("## 📅 Complete Schedule\n")

    for item in schedule_json:
        try:
            start = datetime.strptime(item["start_time"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(item["end_time"], "%Y-%m-%d %H:%M")
            time_str = f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
        except (ValueError, KeyError):
            time_str = f"{item['start_time']} - {item['end_time']}"

        # Check if this was added to calendar
        in_calendar = any(
            e.get("title") == item.get("title")
            and e.get("start_time") == item.get("start_time")
            for e in added_events
        )
        calendar_marker = "📅 " if in_calendar else ""

        priority_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🔵", "P4": "⚪"}
        priority = priority_emoji.get(item.get("priority", ""), "")

        output.append(f"**{time_str}** {calendar_marker}{priority} {item['title']}\n")

    return "\n".join(output)
