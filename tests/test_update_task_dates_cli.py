"""Tests for the standalone task date overwrite CLI."""

import os
import sqlite3
import tempfile
from datetime import date
from unittest import TestCase

from update_task_dates import main as cli_main
from src.database_model import DatabaseModel


class UpdateTaskDatesCLITest(TestCase):
    """Ensure the CLI updates records as expected."""

    def setUp(self) -> None:
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.db_model = DatabaseModel(self.temp_db.name)

        # Seed with a sample record to update during tests
        self.db_model.insert_progress_record(
            record_date=date(2024, 1, 15),
            project_name="Demo Project",
            task_name="Implement Feature",
            assignee="Alice",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            actual_progress=0.5,
            status="In Progress",
            show_label="v",
            is_backfilled=False,
        )

    def tearDown(self) -> None:
        os.unlink(self.temp_db.name)

    def test_successful_update(self) -> None:
        """CLI should return zero and update dates when task exists."""

        exit_code = cli_main(
            [
                "--db",
                self.temp_db.name,
                "--project",
                "Demo Project",
                "--task",
                "Implement Feature",
                "--start-date",
                "2024-02-01",
                "--end-date",
                "2024-02-20",
            ]
        )

        self.assertEqual(exit_code, 0)

        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT start_date, end_date FROM daily_progress WHERE task_name = ?",
            ("Implement Feature",),
        )
        start_value, end_value = cursor.fetchone()
        conn.close()

        self.assertEqual(start_value, "2024-02-01")
        self.assertEqual(end_value, "2024-02-20")

    def test_missing_task_returns_non_zero(self) -> None:
        """Missing tasks should return a dedicated exit code."""

        exit_code = cli_main(
            [
                "--db",
                self.temp_db.name,
                "--project",
                "Demo Project",
                "--task",
                "Missing Task",
                "--start-date",
                "2024-02-01",
                "--end-date",
                "2024-02-20",
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_invalid_date_range(self) -> None:
        """Start date after end date should yield error exit code."""

        exit_code = cli_main(
            [
                "--db",
                self.temp_db.name,
                "--project",
                "Demo Project",
                "--task",
                "Implement Feature",
                "--start-date",
                "2024-03-10",
                "--end-date",
                "2024-03-01",
            ]
        )

        self.assertEqual(exit_code, 1)
