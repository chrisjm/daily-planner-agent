"""Todoist integration."""

from datetime import datetime
from todoist_api_python.api import TodoistAPI

from ..config.settings import TODOIST_API_KEY, TASK_DESCRIPTION_MAX_LENGTH
from .observability import (
    observe_integration,
    IntegrationLogger,
    IntegrationValidator,
)


# Initialize logger and validator for todoist integration
_logger = IntegrationLogger("todoist")
_validator = IntegrationValidator("todoist")


@observe_integration("todoist")
def get_todoist_tasks() -> str:
    """
    Fetch Todoist tasks with rich context including labels, priority, and project info.
    Categorizes as Urgent (due today/overdue) or Backlog (future/no due date).

    Returns:
        Formatted text summary of tasks with all available metadata
    """
    try:
        if not TODOIST_API_KEY:
            _logger.error("TODOIST_API_KEY not set in .env")
            raise ValueError("TODOIST_API_KEY not set in .env")

        _logger.info("Initializing Todoist API client")
        api = TodoistAPI(TODOIST_API_KEY)

        _logger.info("Fetching Todoist tasks")
        tasks_response = api.get_tasks()

        # Handle ResultsPaginator - convert to list
        _logger.debug(f"Tasks response type: {type(tasks_response).__name__}")
        raw_tasks = list(tasks_response)

        # Flatten if API returns nested lists (each page is a list)
        tasks = []
        for item in raw_tasks:
            if isinstance(item, list):
                tasks.extend(item)
                _logger.debug(f"Flattened nested list with {len(item)} tasks")
            else:
                tasks.append(item)

        _logger.info(f"Retrieved {len(tasks)} tasks from Todoist")

        # Debug: Log first task structure if available
        if tasks:
            _logger.debug(
                "First task structure",
                task_type=type(tasks[0]).__name__,
                has_id=hasattr(tasks[0], "id"),
                has_content=hasattr(tasks[0], "content"),
            )

        # Validate API response
        validation = _validator.validate_api_response(tasks, expected_type=list)
        if not validation.valid:
            _logger.warning(f"API response validation failed: {validation.errors}")
        if validation.warnings:
            _logger.warning(f"API response warnings: {validation.warnings}")

        if not tasks:
            _logger.info("No Todoist tasks found")
            return "No Todoist tasks found."

        today = datetime.now().date()
        urgent_tasks = []
        backlog_tasks = []

        for idx, task in enumerate(tasks):
            try:
                _logger.debug(
                    f"Processing task {idx + 1}/{len(tasks)}",
                    task_id=task.id,
                    content=task.content,
                    priority=task.priority,
                    has_due=bool(task.due),
                    labels_count=len(task.labels) if task.labels else 0,
                )
                # Start with task content
                task_str = f"- {task.content}"

                # Add priority indicator (p1=highest, p4=lowest)
                priority_map = {4: "🔴 P1", 3: "🟡 P2", 2: "🔵 P3", 1: "⚪ P4"}
                if task.priority > 1:
                    task_str += f" [{priority_map.get(task.priority, '')}]"

                # Add labels if present
                if task.labels:
                    task_str += f" #{', #'.join(task.labels)}"

                # Add description if present (truncate if too long)
                if task.description:
                    desc_preview = (
                        task.description[:TASK_DESCRIPTION_MAX_LENGTH] + "..."
                        if len(task.description) > TASK_DESCRIPTION_MAX_LENGTH
                        else task.description
                    )
                    task_str += f" | {desc_preview}"

                # Add due date info
                if task.due and task.due.date:
                    try:
                        due_date = datetime.fromisoformat(task.due.date).date()
                        days_until = (due_date - today).days

                        if days_until < 0:
                            task_str += f" [⚠️ OVERDUE by {abs(days_until)} days]"
                        elif days_until == 0:
                            task_str += " [📅 Due TODAY]"
                        else:
                            task_str += f" [Due: {task.due.date}]"

                        if due_date <= today:
                            urgent_tasks.append(task_str)
                        else:
                            backlog_tasks.append(task_str)
                    except (ValueError, AttributeError, TypeError) as e:
                        # Date parsing failed - treat as backlog task with no date
                        _logger.debug(
                            "Could not parse task due date, treating as no due date",
                            task_index=idx,
                            task_id=task.id,
                            due_date_value=getattr(task.due, "date", None),
                            error=str(e),
                        )
                        task_str += " [No due date]"
                        backlog_tasks.append(task_str)
                else:
                    # No due date or due.date is None
                    task_str += " [No due date]"
                    backlog_tasks.append(task_str)

            except AttributeError as e:
                _logger.debug(
                    "Missing required attribute in task, skipping",
                    task_index=idx,
                    task_id=getattr(task, "id", "unknown"),
                    missing_attribute=str(e),
                )
                continue
            except Exception as e:
                _logger.debug(
                    "Error processing task, skipping",
                    task_index=idx,
                    task_id=getattr(task, "id", "unknown"),
                    error=str(e),
                )
                continue

        result = []
        if urgent_tasks:
            result.append("**Urgent Tasks (Due Today or Overdue):**")
            result.extend(urgent_tasks)

        if backlog_tasks:
            result.append("\n**Backlog Tasks (No Due Date or Future):**")
            result.extend(backlog_tasks)

        final_result = "\n".join(result)
        _logger.info(
            "Todoist tasks formatted successfully",
            urgent_tasks_count=len(urgent_tasks),
            backlog_tasks_count=len(backlog_tasks),
            total_length=len(final_result),
        )

        return final_result

    except Exception as e:
        _logger.error(
            "Fatal error in get_todoist_tasks",
            error_type=type(e).__name__,
            error=str(e),
        )
        return f"Error fetching Todoist tasks: {str(e)}"
