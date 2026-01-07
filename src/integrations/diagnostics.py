"""Diagnostic CLI tool for testing and debugging integrations.

Usage:
    python -m src.integrations.diagnostics calendar
    python -m src.integrations.diagnostics todoist
    python -m src.integrations.diagnostics all
    python -m src.integrations.diagnostics logs calendar --days 7
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from .observability import get_integration_diagnostics, IntegrationLogger


def test_calendar_integration(verbose: bool = False) -> dict:
    """Test calendar integration and return results."""
    from .calendar import get_calendar_events

    logger = IntegrationLogger("calendar")
    result = {
        "integration": "calendar",
        "timestamp": datetime.utcnow().isoformat(),
        "success": False,
        "output": None,
        "error": None,
    }

    print("\n" + "=" * 60)
    print("Testing Calendar Integration")
    print("=" * 60)

    try:
        print("\nFetching calendar events...")
        output = get_calendar_events()
        result["success"] = not output.startswith("Error")
        result["output"] = output

        if result["success"]:
            print("\n✅ Calendar integration successful!")
            if verbose:
                print("\nOutput preview:")
                print("-" * 60)
                print(output[:500] + "..." if len(output) > 500 else output)
        else:
            print("\n❌ Calendar integration failed!")
            print(f"Error: {output}")
            result["error"] = output

    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ Calendar integration crashed: {str(e)}")
        logger.error("Calendar test crashed", error=str(e))

    return result


def test_todoist_integration(verbose: bool = False) -> dict:
    """Test Todoist integration and return results."""
    from .todoist import get_todoist_tasks

    logger = IntegrationLogger("todoist")
    result = {
        "integration": "todoist",
        "timestamp": datetime.utcnow().isoformat(),
        "success": False,
        "output": None,
        "error": None,
    }

    print("\n" + "=" * 60)
    print("Testing Todoist Integration")
    print("=" * 60)

    try:
        print("\nFetching Todoist tasks...")
        output = get_todoist_tasks()
        result["success"] = not output.startswith("Error")
        result["output"] = output

        if result["success"]:
            print("\n✅ Todoist integration successful!")
            if verbose:
                print("\nOutput preview:")
                print("-" * 60)
                print(output[:500] + "..." if len(output) > 500 else output)
        else:
            print("\n❌ Todoist integration failed!")
            print(f"Error: {output}")
            result["error"] = output

    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ Todoist integration crashed: {str(e)}")
        logger.error("Todoist test crashed", error=str(e))

    return result


def show_diagnostics(integration: str, days: int = 1):
    """Show diagnostic information for an integration."""
    print("\n" + "=" * 60)
    print(f"Diagnostics for {integration.upper()}")
    print("=" * 60)

    diag = get_integration_diagnostics(integration, days=days)

    print(f"\nTimestamp: {diag['timestamp']}")
    print(f"\nLog Files ({len(diag['log_files'])} found):")
    for log_file in diag["log_files"]:
        print(f"  - {log_file}")

    print("\nMetrics Summary:")
    metrics = diag["metrics_summary"]
    print(f"  Total Calls: {metrics['total_calls']}")
    print(f"  Successful: {metrics['successful_calls']}")
    print(f"  Failed: {metrics['failed_calls']}")
    if metrics["total_calls"] > 0:
        success_rate = (metrics["successful_calls"] / metrics["total_calls"]) * 100
        print(f"  Success Rate: {success_rate:.1f}%")
    if metrics["avg_duration_ms"] > 0:
        print(f"  Avg Duration: {metrics['avg_duration_ms']:.2f}ms")

    if diag["recent_errors"]:
        print(f"\nRecent Errors ({len(diag['recent_errors'])}):")
        for idx, error in enumerate(diag["recent_errors"], 1):
            print(f"\n  {idx}. {error['timestamp']}")
            print(f"     Function: {error.get('function', 'unknown')}")
            print(f"     Type: {error.get('error_type', 'unknown')}")
            print(f"     Message: {error['message']}")
    else:
        print("\n✅ No recent errors found!")


def show_logs(integration: str, lines: int = 50, level: Optional[str] = None):
    """Show recent log entries for an integration."""
    logger = IntegrationLogger(integration)
    log_dir = logger.log_dir

    # Find today's log file
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"{integration}_{date_str}.log"

    if not log_file.exists():
        print(f"\n❌ No log file found for {integration} today: {log_file}")
        return

    print("\n" + "=" * 60)
    print(f"Recent Logs for {integration.upper()} (last {lines} lines)")
    print("=" * 60 + "\n")

    with open(log_file, "r") as f:
        all_lines = f.readlines()
        recent_lines = all_lines[-lines:]

        for line in recent_lines:
            if level:
                if f" - {level.upper()} - " in line:
                    print(line.rstrip())
            else:
                print(line.rstrip())


def export_diagnostics(output_file: str, integrations: list[str], days: int = 1):
    """Export diagnostics to a JSON file."""
    diagnostics = {}

    for integration in integrations:
        print(f"Collecting diagnostics for {integration}...")
        diagnostics[integration] = get_integration_diagnostics(integration, days=days)

    output_path = Path(output_file)
    with open(output_path, "w") as f:
        json.dump(diagnostics, f, indent=2)

    print(f"\n✅ Diagnostics exported to: {output_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Diagnostic tool for integration debugging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test calendar integration
  python -m src.integrations.diagnostics test calendar

  # Test all integrations
  python -m src.integrations.diagnostics test all

  # Show diagnostics for calendar (last 7 days)
  python -m src.integrations.diagnostics diag calendar --days 7

  # Show recent logs
  python -m src.integrations.diagnostics logs todoist --lines 100

  # Export diagnostics to JSON
  python -m src.integrations.diagnostics export --output diag.json --days 7
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test integrations")
    test_parser.add_argument(
        "integration",
        choices=["calendar", "todoist", "all"],
        help="Integration to test",
    )
    test_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show verbose output"
    )

    # Diagnostics command
    diag_parser = subparsers.add_parser("diag", help="Show diagnostics")
    diag_parser.add_argument(
        "integration", choices=["calendar", "todoist"], help="Integration to diagnose"
    )
    diag_parser.add_argument(
        "--days", type=int, default=1, help="Number of days to analyze (default: 1)"
    )

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show recent logs")
    logs_parser.add_argument(
        "integration",
        choices=["calendar", "todoist"],
        help="Integration to show logs for",
    )
    logs_parser.add_argument(
        "--lines", type=int, default=50, help="Number of lines to show (default: 50)"
    )
    logs_parser.add_argument(
        "--level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Filter by log level",
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export diagnostics to JSON")
    export_parser.add_argument(
        "--output",
        default="integration_diagnostics.json",
        help="Output file path (default: integration_diagnostics.json)",
    )
    export_parser.add_argument(
        "--days", type=int, default=1, help="Number of days to analyze (default: 1)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "test":
        results = []

        if args.integration in ["calendar", "all"]:
            results.append(test_calendar_integration(verbose=args.verbose))

        if args.integration in ["todoist", "all"]:
            results.append(test_todoist_integration(verbose=args.verbose))

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{result['integration'].upper()}: {status}")

        # Exit with error code if any test failed
        if not all(r["success"] for r in results):
            sys.exit(1)

    elif args.command == "diag":
        show_diagnostics(args.integration, days=args.days)

    elif args.command == "logs":
        show_logs(args.integration, lines=args.lines, level=args.level)

    elif args.command == "export":
        export_diagnostics(
            args.output, integrations=["calendar", "todoist"], days=args.days
        )


if __name__ == "__main__":
    main()
