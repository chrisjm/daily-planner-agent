"""Todoist integration."""

from datetime import datetime
from todoist_api_python.api import TodoistAPI

from ..config.settings import TODOIST_API_KEY, TASK_DESCRIPTION_MAX_LENGTH


def get_todoist_tasks() -> str:
    """
    Fetch Todoist tasks with rich context including labels, priority, and project info.
    Categorizes as Urgent (due today/overdue) or Backlog (future/no due date).

    Returns:
        Formatted text summary of tasks with all available metadata
    """
    try:
        if not TODOIST_API_KEY:
            raise ValueError("TODOIST_API_KEY not set in .env")

        api = TodoistAPI(TODOIST_API_KEY)
        tasks = api.get_tasks()

        if not tasks:
            return "No Todoist tasks found."

        today = datetime.now().date()
        urgent_tasks = []
        backlog_tasks = []

        for task in tasks:
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
            if task.due:
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
            else:
                task_str += " [No due date]"
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
