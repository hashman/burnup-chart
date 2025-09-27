"""Integration-style tests covering BurnUpSystem workflows."""

from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path
from unittest import TestCase

from src.burnup_system import BurnUpSystem, DateFilterOptions
from src.data_loader import DataLoader


class BurnUpSystemIntegrationTests(TestCase):
    """Exercise BurnUpSystem using the sample plan file."""

    def setUp(self) -> None:
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()
        self.db_path = temp_db.name
        self.system = BurnUpSystem(self.db_path)
        self.plan_path = Path("tests/data/sample_plan.csv")
        self.loader = DataLoader()

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_full_progress_flow(self) -> None:
        """Initialize history, perform updates, and generate charts per project."""

        dataframe = self.loader.load_project_data(str(self.plan_path))
        project_names = dataframe["Project Name"].unique().tolist()
        self.assertTrue(project_names)

        # Initialize historical records and confirm safe update works afterwards.
        self.assertTrue(self.system.initialize_project(str(self.plan_path)))
        self.assertTrue(self.system.daily_update_safe(str(self.plan_path)))

        # Generate charts for each project across the configured window.
        filters = DateFilterOptions(
            start_date=date(2025, 7, 1), end_date=date(2025, 12, 31)
        )
        for project in project_names:
            figure = self.system.create_burnup_chart(
                project, str(self.plan_path), filter_options=filters
            )
            self.assertIsNotNone(figure)
            # Cover status/reporting helpers.
            self.system.show_protection_status(project)

        # Demonstrate handling of missing projects and invalid filters.
        self.assertIsNone(
            self.system.create_burnup_chart("Nonexistent", str(self.plan_path))
        )

        invalid_filters = DateFilterOptions(target_year=2023)
        self.assertIsNone(
            self.system.create_burnup_chart(
                project_names[0], str(self.plan_path), filter_options=invalid_filters
            )
        )

        # Summary output should succeed without raising.
        self.system.show_data_summary(str(self.plan_path))
