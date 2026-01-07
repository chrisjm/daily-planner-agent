# Integration Observability & Debugging Guide

This document describes the comprehensive observability system for debugging integration issues in the daily planner agent.

## Overview

The observability system provides:

- **Structured logging** with multiple output formats (console, file, JSON)
- **Automatic metrics collection** for all integration calls
- **Data validation** to catch parsing and API response issues
- **Diagnostic CLI tools** for testing and debugging
- **Scalable architecture** that works across all integrations

## Architecture

### Components

1. **`observability.py`** - Core observability infrastructure

   - `IntegrationLogger`: Structured logging with console, file, and JSON outputs
   - `observe_integration`: Decorator for automatic metrics and error tracking
   - `IntegrationValidator`: Data validation for API responses and datetime parsing
   - `get_integration_diagnostics`: Retrieve diagnostic information from logs

2. **`diagnostics.py`** - CLI tool for testing and debugging

   - Test integrations individually or all at once
   - View diagnostic summaries with metrics
   - Export diagnostics to JSON for analysis
   - View recent logs with filtering

3. **Instrumented integrations**
   - `calendar.py` - Full observability for Google Calendar
   - `todoist.py` - Full observability for Todoist

## Log Files

Logs are stored in `~/.daily-planner-agent/logs/`:

```
~/.daily-planner-agent/logs/
├── calendar_20260106.log       # Human-readable logs
├── calendar_20260106.jsonl     # Machine-readable structured logs
├── todoist_20260106.log
└── todoist_20260106.jsonl
```

### Log Levels

- **DEBUG**: Detailed information for diagnosing problems (file only)
- **INFO**: General informational messages (console + file)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures

### JSON Log Format

Each line in `.jsonl` files is a JSON object:

```json
{
  "timestamp": "2026-01-06T23:07:00.123456",
  "integration": "calendar",
  "level": "INFO",
  "message": "Retrieved 15 calendar events",
  "function": "get_calendar_events",
  "event_count": 15
}
```

Metrics entries include additional fields:

```json
{
  "timestamp": "2026-01-06T23:07:01.234567",
  "integration": "calendar",
  "level": "METRICS",
  "message": "get_calendar_events completed",
  "function": "get_calendar_events",
  "start_time": 1704585420.123,
  "end_time": 1704585421.234,
  "duration_ms": 1111.0,
  "success": true,
  "result_summary": {
    "type": "str",
    "length": 1234,
    "line_count": 25
  }
}
```

## Using the Diagnostic CLI

### Test Integrations

Test calendar integration:

```bash
python -m src.integrations.diagnostics test calendar
```

Test all integrations:

```bash
python -m src.integrations.diagnostics test all
```

Verbose output (shows preview of results):

```bash
python -m src.integrations.diagnostics test calendar -v
```

### View Diagnostics

Show diagnostic summary for calendar (last 24 hours):

```bash
python -m src.integrations.diagnostics diag calendar
```

Analyze last 7 days:

```bash
python -m src.integrations.diagnostics diag calendar --days 7
```

Example output:

```
============================================================
Diagnostics for CALENDAR
============================================================

Timestamp: 2026-01-06T23:07:00.123456

Log Files (2 found):
  - /Users/chris/.daily-planner-agent/logs/calendar_20260106.log
  - /Users/chris/.daily-planner-agent/logs/calendar_20260106.jsonl

Metrics Summary:
  Total Calls: 45
  Successful: 42
  Failed: 3
  Success Rate: 93.3%
  Avg Duration: 856.23ms

Recent Errors (3):
  1. 2026-01-06T22:45:12.123456
     Function: get_calendar_events
     Type: KeyError
     Message: Missing required field in event
```

### View Logs

Show last 50 lines of logs:

```bash
python -m src.integrations.diagnostics logs calendar
```

Show last 100 lines:

```bash
python -m src.integrations.diagnostics logs calendar --lines 100
```

Filter by log level:

```bash
python -m src.integrations.diagnostics logs calendar --level ERROR
```

### Export Diagnostics

Export diagnostics to JSON file:

```bash
python -m src.integrations.diagnostics export --output diagnostics.json
```

Export last 7 days:

```bash
python -m src.integrations.diagnostics export --output diagnostics.json --days 7
```

## Adding Observability to New Integrations

### Step 1: Import observability tools

```python
from .observability import (
    observe_integration,
    IntegrationLogger,
    IntegrationValidator,
)
```

### Step 2: Initialize logger and validator

```python
# Initialize logger and validator for your integration
_logger = IntegrationLogger("your_integration_name")
_validator = IntegrationValidator("your_integration_name")
```

### Step 3: Add decorator to main functions

```python
@observe_integration("your_integration_name")
def get_your_data() -> str:
    """Fetch data from your integration."""
    try:
        # Your code here
        pass
    except Exception as e:
        _logger.error(
            "Fatal error in get_your_data",
            error_type=type(e).__name__,
            error=str(e)
        )
        return f"Error fetching data: {str(e)}"
```

### Step 4: Add logging throughout your code

```python
# Info logs for major steps
_logger.info("Starting data fetch", param1=value1, param2=value2)

# Debug logs for detailed information
_logger.debug(
    f"Processing item {idx + 1}/{total}",
    item_id=item.id,
    item_name=item.name
)

# Error logs with context
_logger.error(
    "Failed to parse item",
    item_index=idx,
    item_id=item.id,
    error=str(e)
)
```

### Step 5: Add validation

```python
# Validate API responses
validation = _validator.validate_api_response(response, expected_type=list)
if not validation.valid:
    _logger.warning(f"API response validation failed: {validation.errors}")

# Validate datetime parsing
datetime_validation = _validator.validate_datetime_parsing(date_str)
if not datetime_validation.valid:
    _logger.error(
        "Failed to parse datetime",
        value=date_str,
        errors=datetime_validation.errors
    )
```

## Debugging Common Issues

### Issue: "Can't compare offset-naive and offset-aware datetimes"

**What to look for in logs:**

- Search for "Failed to parse event datetime" or "Failed to parse task due date"
- Check the `start_value` or `due_date_value` fields in error logs
- Look for datetime validation errors

**Example log entry:**

```json
{
  "level": "ERROR",
  "message": "Failed to parse event datetime",
  "event_index": 5,
  "start_value": "2026-01-07",
  "errors": ["Failed to parse datetime: ..."]
}
```

### Issue: "list object has no attribute 'content'"

**What to look for in logs:**

- Search for "Missing required attribute" errors
- Check the `task_index` and `missing_attribute` fields
- Look at the raw API response structure

**Example log entry:**

```json
{
  "level": "ERROR",
  "message": "Missing required attribute in task",
  "task_index": 3,
  "task_id": "12345",
  "missing_attribute": "'list' object has no attribute 'content'"
}
```

### Issue: Empty or unexpected API responses

**What to look for in logs:**

- Check validation warnings: "Response list is empty"
- Look at `result_summary` in METRICS entries
- Check the count of items retrieved

**Example log entry:**

```json
{
  "level": "WARNING",
  "message": "API response warnings: ['Response list is empty']",
  "validation_result": {
    "valid": true,
    "warnings": ["Response list is empty"],
    "metadata": { "count": 0 }
  }
}
```

## Performance Monitoring

### Metrics Collected

For each integration function call:

- **Duration**: Time taken in milliseconds
- **Success/Failure**: Whether the call succeeded
- **Result Summary**: Type, size, and preview of the result
- **Error Details**: Full error type, message, and traceback

### Analyzing Performance

Use the diagnostic CLI to get performance metrics:

```bash
python -m src.integrations.diagnostics diag calendar --days 7
```

Look for:

- **Success rate**: Should be >95% for stable integrations
- **Average duration**: Baseline for performance regression detection
- **Failed calls**: Patterns in errors (time of day, specific operations)

### Exporting for Analysis

Export to JSON and analyze with tools like jq:

```bash
# Export diagnostics
python -m src.integrations.diagnostics export --output diag.json --days 7

# Get average duration by integration
cat diag.json | jq '.calendar.metrics_summary.avg_duration_ms'

# Count errors by type
cat ~/.daily-planner-agent/logs/calendar_20260106.jsonl | \
  jq -r 'select(.level=="ERROR") | .error_type' | \
  sort | uniq -c
```

## Best Practices

1. **Always use the decorator** - `@observe_integration()` on main functions
2. **Log at appropriate levels** - DEBUG for details, INFO for milestones, ERROR for failures
3. **Include context** - Pass relevant variables as kwargs to logger methods
4. **Validate early** - Check API responses and datetime parsing before processing
5. **Handle errors gracefully** - Log errors with full context, then return user-friendly messages
6. **Test regularly** - Use the diagnostic CLI to test integrations after changes
7. **Monitor metrics** - Check diagnostics periodically to catch degradation

## Troubleshooting the Observability System

### Logs not appearing

Check that the log directory exists:

```bash
ls -la ~/.daily-planner-agent/logs/
```

If it doesn't exist, it will be created automatically on first use.

### JSON logs not parsing

Validate JSON structure:

```bash
cat ~/.daily-planner-agent/logs/calendar_20260106.jsonl | jq empty
```

### Diagnostic CLI not working

Ensure you're running from the project root:

```bash
cd /path/to/daily-planner-agent
python -m src.integrations.diagnostics test calendar
```

## Future Enhancements

Potential improvements to the observability system:

- [ ] Real-time log streaming dashboard
- [ ] Automatic alerting for error rate thresholds
- [ ] Integration with external monitoring services (Sentry, DataDog)
- [ ] Performance regression detection
- [ ] Automated test suite based on diagnostics
- [ ] Log aggregation across multiple days
- [ ] Correlation IDs for tracing requests across integrations
