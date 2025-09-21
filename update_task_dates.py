"""Command-line helper to overwrite task start and end dates in the burn-up database."""

from __future__ import annotations

import argparse
from datetime import date
from typing import Iterable, Optional

from src.burnup_manager import BurnUpManager


def _parse_iso_date(value: str) -> date:
    """Parse an ISO formatted date string (YYYY-MM-DD)."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected format YYYY-MM-DD."
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    """Create an argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Overwrite the stored start and end dates for a specific task in the "
            "burn-up chart historical database."
        )
    )
    parser.add_argument(
        "--db",
        default="burnup_history.db",
        help="Path to the SQLite database file (default: burnup_history.db).",
    )
    parser.add_argument(
        "--project", required=True, help="Project name that owns the task."
    )
    parser.add_argument("--task", required=True, help="Task name to update.")
    parser.add_argument(
        "--start-date",
        required=True,
        type=_parse_iso_date,
        help="New task start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=_parse_iso_date,
        help="New task end date in YYYY-MM-DD format.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Entry point for the CLI.

    Args:
        argv: Optional iterable of argument strings. When ``None`` the arguments
            are read from ``sys.argv``.

    Returns:
        Exit status code (0 on success).
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    manager = BurnUpManager(db_path=args.db)

    try:
        updated = manager.overwrite_task_dates(
            args.project, args.task, args.start_date, args.end_date
        )
    except ValueError as exc:
        print(f"❌ {exc}")
        return 1

    if updated:
        print(
            "✅ Successfully updated task dates: "
            f"{args.project} / {args.task} → {args.start_date} to {args.end_date}"
        )
        return 0

    print(
        "⚠️ No matching records were found in the database for the provided "
        "project and task."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
