"""Parsing utilities for event titles and task content."""

import re


def parse_event_title(title: str) -> tuple[str, str]:
    """
    Parse event title to extract category and event description.

    Supports multiple formats (backward compatible):
    - "CATEGORY: Event description" -> ("CATEGORY", "Event description")
    - "category: Event description" -> ("category", "Event description")
    - "Event description [category]" -> ("category", "Event description")
    - "Event description category: tag" -> ("tag", "Event description")
    - "Event description" -> ("", "Event description")

    Args:
        title: Event title string

    Returns:
        Tuple of (category, description)
    """
    if not title:
        return ("", "No title")

    # Format 1: "CATEGORY: Description" (primary format)
    match = re.match(r"^([A-Za-z0-9_-]+):\s*(.+)$", title)
    if match:
        return (match.group(1), match.group(2).strip())

    # Format 2: "Description category: tag" (backward compatible)
    match = re.search(r"\bcategory:\s*(\S+)", title, re.IGNORECASE)
    if match:
        category = match.group(1)
        description = re.sub(
            r"\s*\bcategory:\s*\S+", "", title, flags=re.IGNORECASE
        ).strip()
        return (category, description)

    # Format 3: "Description [category]" (backward compatible)
    match = re.search(r"\[([^\]]+)\]", title)
    if match:
        category = match.group(1)
        description = re.sub(r"\s*\[[^\]]+\]", "", title).strip()
        return (category, description)

    # No category found
    return ("", title)
