"""Unit tests focused on DataFilter helper functions."""

from __future__ import annotations

from datetime import date
from unittest import TestCase

import pandas as pd

from src.data_filter import DataFilter


class DataFilterTests(TestCase):
    """Exercise the filtering utilities with representative data."""

    def setUp(self) -> None:  # noqa: D401 - standard unittest hook
        self.df = pd.DataFrame(
            {
                "Project Name": ["Alpha", "Alpha", "Beta"],
                "Task Name": ["A1", "A2", "B1"],
                "Start Date": [
                    date(2024, 12, 20),
                    date(2025, 1, 10),
                    date(2025, 11, 20),
                ],
                "End Date": [
                    date(2025, 1, 15),
                    date(2025, 3, 1),
                    date(2026, 1, 15),
                ],
            }
        )

    def test_filter_by_date_range_combined(self) -> None:
        """Year and explicit date filtering should cooperate correctly."""

        filtered = DataFilter.filter_by_date_range(
            self.df,
            start_year=2025,
            end_year=2025,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        self.assertListEqual(filtered["Task Name"].tolist(), ["A2"])

    def test_filter_tasks_within_year(self) -> None:
        """Tasks that overlap the target year must be included."""

        filtered = DataFilter.filter_tasks_within_year(self.df, 2025)
        self.assertCountEqual(filtered["Task Name"], ["A1", "A2", "B1"])

    def test_get_date_range_summary(self) -> None:
        """Summaries should report the full span of the data set."""

        summary = DataFilter.get_date_range_summary(self.df)
        self.assertEqual(summary["total_tasks"], 3)
        self.assertEqual(summary["start_date"], date(2024, 12, 20))
        self.assertEqual(summary["end_date"], date(2026, 1, 15))
        self.assertIn(2025, summary["years_covered"])

    def test_validate_year_filter_fail_and_pass(self) -> None:
        """Validate success and failure paths of year filtering."""

        valid, message = DataFilter.validate_year_filter(2023, self.df)
        self.assertFalse(valid)
        self.assertIn("Year 2023", message)

        valid, message = DataFilter.validate_year_filter(2025, self.df)
        self.assertTrue(valid)
        self.assertIn("Found", message)
