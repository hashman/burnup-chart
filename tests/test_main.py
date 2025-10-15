"""Tests for the top-level main module."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pandas as pd

import main as main_module


class MainModuleTests(TestCase):
    """Validate the behaviour of the CLI entry-point helpers."""

    def test_resolve_plan_path_prefers_explicit(self) -> None:
        """Explicit paths should be honoured when they exist."""

        with patch("main.Path.exists", return_value=True) as mock_exists:
            result = main_module._resolve_plan_path("custom.csv")

        self.assertEqual(result, "custom.csv")
        mock_exists.assert_called()  # ensure existence was checked

    def test_resolve_plan_path_fallback(self) -> None:
        """Fallback should search for default plan files when not provided."""

        exists_sequence = [False, True]  # plan.xlsx missing, plan.csv present
        with patch("main.Path.exists", side_effect=exists_sequence):
            result = main_module._resolve_plan_path(None)

        self.assertEqual(result, "plan.csv")

    def test_main_runs_for_each_project(self) -> None:
        """main() should drive the workflow for every detected project."""

        projects = pd.DataFrame(
            {
                "Project Name": ["Alpha", "Beta"],
                "Task Name": ["Task A", "Task B"],
                "Start Date": pd.to_datetime(["2025-07-01", "2025-07-10"]).date,
                "End Date": pd.to_datetime(["2025-08-01", "2025-08-10"]).date,
                "Actual": [0.1, 0.2],
                "Assign": ["Alice", "Bob"],
                "Status": ["In Progress", "Planned"],
            }
        )

        args = SimpleNamespace(plan_path=None)

        with patch.object(main_module, "parse_args", return_value=args), patch.object(
            main_module, "_resolve_plan_path", return_value="plan.csv"
        ), patch.object(main_module, "DataLoader") as mock_loader, patch.object(
            main_module, "BurnUpManager"
        ) as mock_manager:

            mock_loader.return_value.load_project_data.return_value = projects

            manager_instance = mock_manager.return_value
            manager_instance.system.has_historical_data.return_value = True
            manager_instance.show_improved_chart.return_value = MagicMock()

            main_module.main()

        self.assertEqual(
            manager_instance.show_improved_chart.call_count,
            len(projects["Project Name"].unique()),
        )
        self.assertEqual(
            manager_instance.show_protection_status.call_count,
            len(projects["Project Name"].unique()),
        )

    def test_main_handles_missing_plan(self) -> None:
        """When no plan files exist the program should exit gracefully."""

        args = SimpleNamespace(plan_path=None)
        with patch.object(main_module, "parse_args", return_value=args), patch.object(
            main_module, "_resolve_plan_path", side_effect=FileNotFoundError("missing")
        ):
            main_module.main()  # Should not raise
