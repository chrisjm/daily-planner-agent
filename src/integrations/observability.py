"""Observability and debugging infrastructure for integrations.

Provides structured logging, diagnostics, and validation tools for all integrations."""

import json
import logging
import time
import traceback
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, asdict, field


# Configure structured logging
class IntegrationLogger:
    """Structured logger for integration operations."""

    def __init__(self, integration_name: str, log_dir: Optional[Path] = None):
        self.integration_name = integration_name
        self.log_dir = log_dir or Path.home() / ".daily-planner-agent" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # JSON structured log file for machine parsing (set this first, always)
        self.json_log_file = (
            self.log_dir
            / f"{integration_name}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        # Create logger
        self.logger = logging.getLogger(f"integration.{integration_name}")
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Console handler (INFO and above)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            # File handler (DEBUG and above) - daily rotation
            log_file = (
                self.log_dir
                / f"{integration_name}_{datetime.now().strftime('%Y%m%d')}.log"
            )
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def _write_json_log(self, level: str, message: str, **kwargs):
        """Write structured JSON log entry."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "integration": self.integration_name,
            "level": level,
            "message": message,
            **kwargs,
        }
        with open(self.json_log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def debug(self, message: str, **kwargs):
        self.logger.debug(message)
        self._write_json_log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(message)
        self._write_json_log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message)
        self._write_json_log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(message)
        self._write_json_log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        self.logger.critical(message)
        self._write_json_log("CRITICAL", message, **kwargs)


@dataclass
class IntegrationMetrics:
    """Metrics for integration function calls."""

    integration: str
    function: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    result_summary: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

    def complete(
        self, success: bool, error: Optional[Exception] = None, result: Any = None
    ):
        """Mark metrics as complete."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success

        if error:
            self.error = str(error)
            self.error_type = type(error).__name__
            self.traceback = traceback.format_exc()

        if result is not None:
            self.result_summary = self._summarize_result(result)

    def _summarize_result(self, result: Any) -> dict:
        """Create a summary of the result for logging."""
        summary = {"type": type(result).__name__}

        if isinstance(result, str):
            summary["length"] = len(result)
            summary["preview"] = result[:200] if len(result) > 200 else result
            summary["line_count"] = result.count("\n")
        elif isinstance(result, (list, tuple)):
            summary["count"] = len(result)
            summary["item_types"] = list(set(type(item).__name__ for item in result))
        elif isinstance(result, dict):
            summary["keys"] = list(result.keys())
            summary["size"] = len(result)

        return summary

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def observe_integration(integration_name: str):
    """Decorator to add observability to integration functions.

    Args:
        integration_name: Name of the integration (e.g., 'calendar', 'todoist')

    Usage:
        @observe_integration('calendar')
        def get_calendar_events():
            ...
    """
    logger = IntegrationLogger(integration_name)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics = IntegrationMetrics(
                integration=integration_name,
                function=func.__name__,
                start_time=time.time(),
                metadata={"args_count": len(args), "kwargs_keys": list(kwargs.keys())},
            )

            logger.info(
                f"Starting {func.__name__}",
                function=func.__name__,
                args_count=len(args),
                kwargs=list(kwargs.keys()),
            )

            try:
                result = func(*args, **kwargs)
                metrics.complete(success=True, result=result)

                logger.info(
                    "Completed " + func.__name__,
                    function=func.__name__,
                    duration_ms=metrics.duration_ms,
                    result_summary=metrics.result_summary,
                )

                # Write metrics to JSON log
                logger._write_json_log(
                    "METRICS", func.__name__ + " completed", **metrics.to_dict()
                )

                return result

            except Exception as e:
                metrics.complete(success=False, error=e)

                logger.error(
                    "Failed " + func.__name__ + ": " + str(e),
                    function=func.__name__,
                    error_type=type(e).__name__,
                    error=str(e),
                    traceback=traceback.format_exc(),
                )

                # Write metrics to JSON log
                logger._write_json_log(
                    "METRICS", func.__name__ + " failed", **metrics.to_dict()
                )

                raise

        return wrapper

    return decorator


@dataclass
class ValidationResult:
    """Result of data validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_error(self, error: str):
        self.valid = False
        self.errors.append(error)

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def to_dict(self) -> dict:
        return asdict(self)


class IntegrationValidator:
    """Validator for integration data."""

    def __init__(self, integration_name: str):
        self.integration_name = integration_name
        self.logger = IntegrationLogger(integration_name)

    def validate_api_response(
        self, response: Any, expected_type: type = None
    ) -> ValidationResult:
        """Validate API response structure."""
        result = ValidationResult(valid=True)

        if response is None:
            result.add_error("Response is None")
            return result

        if expected_type and not isinstance(response, expected_type):
            result.add_error(
                f"Expected type {expected_type.__name__}, got {type(response).__name__}"
            )

        # Type-specific validation
        if isinstance(response, str):
            if not response.strip():
                result.add_warning("Response string is empty or whitespace")
            result.metadata["length"] = len(response)
            result.metadata["line_count"] = response.count("\n")

        elif isinstance(response, (list, tuple)):
            result.metadata["count"] = len(response)
            if len(response) == 0:
                result.add_warning("Response list is empty")

        elif isinstance(response, dict):
            result.metadata["keys"] = list(response.keys())
            if not response:
                result.add_warning("Response dict is empty")

        self.logger.debug("Validated API response", validation_result=result.to_dict())
        return result

    def validate_datetime_parsing(self, date_str: str) -> ValidationResult:
        """Validate datetime string parsing."""
        result = ValidationResult(valid=True)

        if not date_str:
            result.add_error("Date string is empty")
            return result

        try:
            # Try common formats
            parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            result.metadata["parsed_datetime"] = parsed.isoformat()
        except Exception as e:
            result.add_error(f"Failed to parse datetime: {str(e)}")

        return result


def get_integration_diagnostics(integration_name: str, days: int = 1) -> dict:
    """Get diagnostic information for an integration.

    Args:
        integration_name: Name of the integration
        days: Number of days of logs to analyze

    Returns:
        Dictionary with diagnostic information
    """
    logger = IntegrationLogger(integration_name)
    log_dir = logger.log_dir

    diagnostics = {
        "integration": integration_name,
        "timestamp": datetime.utcnow().isoformat(),
        "log_files": [],
        "recent_errors": [],
        "metrics_summary": {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "avg_duration_ms": 0,
        },
    }

    # Find relevant log files
    for i in range(days):
        date_str = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        json_log = log_dir / f"{integration_name}_{date_str}.jsonl"

        if json_log.exists():
            diagnostics["log_files"].append(str(json_log))

            # Parse JSON logs for metrics
            durations = []
            with open(json_log, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)

                        if entry.get("level") == "METRICS":
                            diagnostics["metrics_summary"]["total_calls"] += 1
                            if entry.get("success"):
                                diagnostics["metrics_summary"]["successful_calls"] += 1
                            else:
                                diagnostics["metrics_summary"]["failed_calls"] += 1

                            if entry.get("duration_ms"):
                                durations.append(entry["duration_ms"])

                        elif entry.get("level") == "ERROR":
                            diagnostics["recent_errors"].append(
                                {
                                    "timestamp": entry.get("timestamp"),
                                    "message": entry.get("message"),
                                    "error_type": entry.get("error_type"),
                                    "function": entry.get("function"),
                                }
                            )
                    except json.JSONDecodeError:
                        continue

            if durations:
                diagnostics["metrics_summary"]["avg_duration_ms"] = sum(
                    durations
                ) / len(durations)

    # Limit recent errors to last 10
    diagnostics["recent_errors"] = diagnostics["recent_errors"][-10:]

    return diagnostics
