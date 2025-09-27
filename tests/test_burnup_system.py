"""Unit tests for the burn-up chart system."""

import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from src.burnup_manager import BurnUpManager
from src.burnup_system import BurnUpSystem
from src.chart_generator import ChartGenerator
from src.data_loader import DataLoader
from src.database_model import DatabaseModel, ProgressRecord
from src.progress_calculator import ProgressCalculator


class TestDataLoader(unittest.TestCase):
    """Test cases for DataLoader class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.data_loader = DataLoader()

    def test_validate_project_data_valid(self) -> None:
        """Test validation with valid DataFrame."""
        df = pd.DataFrame(
            {
                "Project Name": ["Test Project"],
                "Task Name": ["Test Task"],
                "Start Date": [date.today()],
                "End Date": [date.today() + timedelta(days=30)],
                "Actual": [0.5],
                "Assign": ["Test User"],
                "Status": ["In Progress"],
            }
        )

        self.assertTrue(self.data_loader.validate_project_data(df))

    def test_validate_project_data_missing_columns(self) -> None:
        """Test validation with missing columns."""
        df = pd.DataFrame(
            {"Project Name": ["Test Project"], "Task Name": ["Test Task"]}
        )

        self.assertFalse(self.data_loader.validate_project_data(df))

    def test_load_project_data_adds_adjusted_columns(self) -> None:
        """Optional adjusted columns should exist and be converted to dates."""

        df = pd.DataFrame(
            {
                "Project Name": ["Project"],
                "Task Name": ["Task"],
                "Start Date": ["2025-01-01"],
                "End Date": ["2025-01-31"],
                "Actual": [0.5],
                "Assign": ["User"],
                "Status": ["Planned"],
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp:
            df.to_csv(temp.name, index=False)
            temp_path = temp.name

        try:
            loaded = self.data_loader.load_project_data(temp_path)
        finally:
            os.unlink(temp_path)

        self.assertIn("Adjusted Start Date", loaded.columns)
        self.assertIn("Adjusted End Date", loaded.columns)
        self.assertIsNone(loaded.loc[0, "Adjusted Start Date"])
        self.assertIsNone(loaded.loc[0, "Adjusted End Date"])

    def test_load_project_data_fallback_between_excel_and_csv(self) -> None:
        """Loader should fall back to alternate extension when available."""

        df = pd.DataFrame(
            {
                "Project Name": ["Project"],
                "Task Name": ["Task"],
                "Start Date": ["2025-01-01"],
                "End Date": ["2025-01-31"],
                "Actual": [0.5],
                "Assign": ["User"],
                "Status": ["Planned"],
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "plan.csv"
            df.to_csv(csv_path, index=False)

            # Request the same stem but with .xlsx extension to trigger fallback.
            requested_path = csv_path.with_suffix(".xlsx")

            loaded = self.data_loader.load_project_data(str(requested_path))

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded.loc[0, "Project Name"], "Project")

    @patch("os.path.exists")
    def test_load_project_data_file_not_found(self, mock_exists: Mock) -> None:
        """Test loading data when file doesn't exist."""
        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError):
            self.data_loader.load_project_data("nonexistent.xlsx")

    def test_load_project_data_unsupported_format(self) -> None:
        """Test loading data with unsupported file format."""
        with patch("pathlib.Path.exists", return_value=True):
            with self.assertRaises(ValueError):
                self.data_loader.load_project_data("test.txt")


class TestProgressCalculator(unittest.TestCase):
    """Test cases for ProgressCalculator class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.progress_calc = ProgressCalculator()

    def test_calculate_plan_percentage_before_start(self) -> None:
        """Test plan percentage calculation before start date."""
        start_date = date(2023, 1, 10)
        end_date = date(2023, 1, 20)
        current_date = date(2023, 1, 5)

        result = self.progress_calc.calculate_plan_percentage(
            start_date, end_date, current_date
        )
        self.assertEqual(result, 0.0)

    def test_calculate_plan_percentage_after_end(self) -> None:
        """Test plan percentage calculation after end date."""
        start_date = date(2023, 1, 10)
        end_date = date(2023, 1, 20)
        current_date = date(2023, 1, 25)

        result = self.progress_calc.calculate_plan_percentage(
            start_date, end_date, current_date
        )
        self.assertEqual(result, 1.0)

    def test_calculate_plan_percentage_midway(self) -> None:
        """Test plan percentage calculation at midpoint."""
        start_date = date(2023, 1, 10)
        end_date = date(2023, 1, 20)
        current_date = date(2023, 1, 15)

        result = self.progress_calc.calculate_plan_percentage(
            start_date, end_date, current_date
        )
        self.assertEqual(result, 0.5)

    def test_calculate_plan_percentage_same_start_end(self) -> None:
        """Test plan percentage with same start and end date."""
        start_date = date(2023, 1, 10)
        end_date = date(2023, 1, 10)
        current_date = date(2023, 1, 10)

        result = self.progress_calc.calculate_plan_percentage(
            start_date, end_date, current_date
        )
        self.assertEqual(result, 1.0)

    def test_generate_plan_progress_sequence_with_adjusted_dates(self) -> None:
        """Adjusted dates should drive the current plan line."""

        project_data = pd.DataFrame(
            {
                "Start Date": [date(2025, 1, 1), date(2025, 1, 10)],
                "End Date": [date(2025, 1, 31), date(2025, 2, 10)],
                "Adjusted Start Date": [date(2025, 1, 5), None],
                "Adjusted End Date": [date(2025, 2, 5), date(2025, 2, 20)],
                "Actual": [0.2, 0.4],
            }
        )

        dates, initial_plan, current_plan = (
            self.progress_calc.generate_plan_progress_sequence(
                project_data, date(2025, 1, 1), date(2025, 1, 5)
            )
        )

        self.assertEqual(len(dates), len(initial_plan))
        self.assertEqual(len(dates), len(current_plan))
        # Current plan should differ when adjusted dates exist
        self.assertNotEqual(initial_plan, current_plan)

    def test_resolve_task_dates_prefers_adjusted(self) -> None:
        """Adjusted dates should override original planning windows."""

        row = pd.Series(
            {
                "Start Date": date(2025, 1, 1),
                "End Date": date(2025, 2, 1),
                "Adjusted Start Date": date(2025, 1, 10),
                "Adjusted End Date": date(2025, 2, 10),
            }
        )
        start_date, end_date = (
            self.progress_calc._resolve_task_dates(  # pylint: disable=protected-access
                row, use_adjusted=True
            )
        )
        self.assertEqual(start_date, date(2025, 1, 10))
        self.assertEqual(end_date, date(2025, 2, 10))

    def test_get_filtered_date_context_variants(self) -> None:
        """Cover context calculation for different filter types."""

        project_data = pd.DataFrame(
            {
                "Start Date": [date(2025, 1, 1)],
                "End Date": [date(2025, 2, 1)],
            }
        )

        year_context = self.progress_calc.get_filtered_date_context(
            project_data, target_year=2025
        )
        self.assertEqual(year_context["filter_type"], "year")

        range_context = self.progress_calc.get_filtered_date_context(
            project_data, start_date=date(2025, 1, 15), end_date=date(2025, 1, 31)
        )
        self.assertEqual(range_context["filter_type"], "date_range")

        no_filter_context = self.progress_calc.get_filtered_date_context(project_data)
        self.assertEqual(no_filter_context["filter_type"], "none")

    def test_generate_smooth_actual_progress(self) -> None:
        """Test smooth actual progress generation."""
        project_data = pd.DataFrame(
            {
                "Start Date": [date(2023, 1, 1), date(2023, 1, 5)],
                "End Date": [date(2023, 1, 31), date(2023, 1, 25)],
                "Actual": [0.4, 0.6],
            }
        )
        today = date(2023, 1, 10)

        result = self.progress_calc.generate_smooth_actual_progress(project_data, today)

        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("date", result[0])
        self.assertIn("progress", result[0])


class TestDatabaseModel(unittest.TestCase):
    """Test cases for DatabaseModel class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.db_model = DatabaseModel(self.temp_db.name)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)

    def test_initialize_database(self) -> None:
        """Test database initialization."""
        # Check if table was created
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_progress'"
            )
            result = cursor.fetchone()

        self.assertIsNotNone(result)

    def test_has_historical_data_empty(self) -> None:
        """Test has_historical_data with empty database."""
        result = self.db_model.has_historical_data()
        self.assertFalse(result)

    def test_insert_and_get_existing_record(self) -> None:
        """Test inserting and retrieving records."""
        test_date = date(2023, 1, 15)

        # Insert a record
        self.db_model.insert_progress_record(
            ProgressRecord(
                record_date=test_date,
                project_name="Test Project",
                task_name="Test Task",
                assignee="Test User",
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 31),
                actual_progress=0.5,
                status="In Progress",
                show_label="v",
                is_backfilled=False,
            )
        )

        # Retrieve the record
        result = self.db_model.get_existing_record(
            test_date, "Test Project", "Test Task"
        )

        self.assertEqual(result, 0.5)

    def test_update_task_dates(self) -> None:
        """Test overwriting task start and end dates."""
        original_start = date(2023, 1, 1)
        original_end = date(2023, 1, 31)

        self.db_model.insert_progress_record(
            ProgressRecord(
                record_date=date(2023, 1, 15),
                project_name="Test Project",
                task_name="Test Task",
                assignee="Test User",
                start_date=original_start,
                end_date=original_end,
                actual_progress=0.5,
                status="In Progress",
                show_label="v",
                is_backfilled=False,
            )
        )

        updated_count = self.db_model.update_task_dates(
            "Test Project",
            "Test Task",
            new_start_date=date(2023, 2, 1),
            new_end_date=date(2023, 2, 28),
        )

        self.assertEqual(updated_count, 1)

        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT start_date, end_date FROM daily_progress
                WHERE project_name = ? AND task_name = ?
                """,
                ("Test Project", "Test Task"),
            )
            start_value, end_value = cursor.fetchone()

        self.assertEqual(start_value, "2023-02-01")
        self.assertEqual(end_value, "2023-02-28")

    def test_update_task_dates_no_match(self) -> None:
        """Updating dates should return zero when task is missing."""

        updated_count = self.db_model.update_task_dates(
            "Unknown Project",
            "Missing Task",
            new_start_date=date(2023, 2, 1),
            new_end_date=date(2023, 2, 28),
        )

        self.assertEqual(updated_count, 0)

    def test_has_historical_data_with_data(self) -> None:
        """Test has_historical_data with existing data."""
        # Insert a record first
        self.db_model.insert_progress_record(
            ProgressRecord(
                record_date=date(2023, 1, 15),
                project_name="Test Project",
                task_name="Test Task",
                assignee="Test User",
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 31),
                actual_progress=0.5,
                status="In Progress",
                show_label="v",
                is_backfilled=False,
            )
        )

        result = self.db_model.has_historical_data()
        self.assertTrue(result)

    def test_get_task_annotations(self) -> None:
        """Test getting task annotations."""
        # Insert a record with show_label='v'
        self.db_model.insert_progress_record(
            ProgressRecord(
                record_date=date(2023, 1, 15),
                project_name="Test Project",
                task_name="Test Task",
                assignee="Test User",
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 31),
                actual_progress=0.5,
                status="In Progress",
                show_label="v",
                is_backfilled=False,
            )
        )

        annotations = self.db_model.get_task_annotations("Test Project")

        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0]["task_name"], "Test Task")
        self.assertEqual(annotations[0]["end_date"], date(2023, 1, 31))

    def test_database_filters(self) -> None:
        """Database queries should honour filtering options."""

        records = [
            ProgressRecord(
                record_date=date(2025, 7, 10),
                project_name="Demo",
                task_name="Task A",
                assignee="Alice",
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 20),
                actual_progress=0.5,
                status="In Progress",
                show_label="v",
                is_backfilled=False,
            ),
            ProgressRecord(
                record_date=date(2025, 8, 5),
                project_name="Demo",
                task_name="Task B",
                assignee="Bob",
                start_date=date(2025, 8, 1),
                end_date=date(2025, 9, 1),
                actual_progress=0.7,
                status="Planned",
                show_label="v",
                is_backfilled=False,
            ),
        ]

        for record in records:
            self.db_model.insert_progress_record(record)

        dates, progress = self.db_model.get_historical_actual_data(
            "Demo", start_date=date(2025, 7, 1), end_date=date(2025, 8, 10)
        )
        self.assertEqual(len(dates), 2)
        self.assertEqual(len(progress), 2)

        tasks = self.db_model.get_filtered_tasks_from_db(
            "Demo", start_date=date(2025, 7, 1), end_date=date(2025, 7, 31)
        )
        self.assertEqual(tasks, ["Task A"])


class TestChartGenerator(unittest.TestCase):
    """Test cases for ChartGenerator class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.chart_gen = ChartGenerator()

    def test_wrap_text_short(self) -> None:
        """Test text wrapping with short text."""
        result = self.chart_gen.wrap_text("Short text", 20)
        self.assertEqual(result, "Short text")

    def test_wrap_text_long(self) -> None:
        """Test text wrapping with long text."""
        long_text = "This is a very long text that should be wrapped"
        result = self.chart_gen.wrap_text(long_text, 20)
        self.assertIn("<br>", result)

    def test_wrap_text_forces_split_on_long_word(self) -> None:
        """Extremely long tokens should be forcefully split."""
        long_word = "A" * 50
        result = self.chart_gen.wrap_text(long_word, 10)
        self.assertIn("<br>", result)

    def test_calculate_smart_annotation_positions_large_group(self) -> None:
        """Large groups should exercise the general offset/height logic."""
        annotations = [
            {
                "task_name": f"Task {idx}",
                "end_date": date(2025, 7, 1 + idx),
                "label": f"Label {idx}",
            }
            for idx in range(6)
        ]

        result = self.chart_gen.calculate_smart_annotation_positions(annotations)
        self.assertEqual(len(result), 6)

    def test_calculate_smart_annotation_positions_empty(self) -> None:
        """Test smart annotation positioning with empty list."""
        result = self.chart_gen.calculate_smart_annotation_positions([])
        self.assertEqual(result, [])

    def test_calculate_smart_annotation_positions_single(self) -> None:
        """Test smart annotation positioning with single annotation."""
        annotations = [
            {
                "task_name": "Test Task",
                "end_date": date(2023, 1, 15),
                "label": "Test Label",
            }
        ]

        result = self.chart_gen.calculate_smart_annotation_positions(annotations)

        self.assertEqual(len(result), 1)
        self.assertIn("y", result[0])
        self.assertIn("x_offset", result[0])

    def test_create_burnup_chart_with_multiple_plan_lines(self) -> None:
        """Chart should include initial, current, and actual traces."""

        dates = [date(2025, 1, 1), date(2025, 1, 10)]
        initial_plan = [0.0, 50.0]
        current_plan = [5.0, 60.0]
        actual_dates = dates
        actual_progress = [0.0, 55.0]

        figure = self.chart_gen.create_burnup_chart(
            project_name="Demo",
            dates=dates,
            initial_plan_progress=initial_plan,
            current_plan_progress=current_plan,
            actual_dates=actual_dates,
            actual_progress=actual_progress,
            task_annotations=[],
            today=datetime(2025, 1, 2),
        )

        self.assertEqual(len(figure.data), 3)
        self.assertEqual(figure.data[0].name, "Initial Plan")
        self.assertEqual(figure.data[1].name, "Current Plan")
        self.assertEqual(figure.data[2].name, "Actual Progress")


class TestBurnUpSystem(unittest.TestCase):
    """Test cases for BurnUpSystem class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.system = BurnUpSystem(self.temp_db.name)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)

    def test_has_historical_data(self) -> None:
        """Test has_historical_data method."""
        result = self.system.has_historical_data()
        self.assertFalse(result)

    @patch("src.burnup_system.DataLoader.load_project_data")
    @patch("src.burnup_system.DataLoader.validate_project_data")
    def test_initialize_project_invalid_data(
        self, mock_validate: Mock, mock_load: Mock
    ) -> None:
        """Test project initialization with invalid data."""
        mock_load.return_value = pd.DataFrame()
        mock_validate.return_value = False

        result = self.system.initialize_project("test.xlsx")
        self.assertFalse(result)

    @patch("src.burnup_system.DataLoader.load_project_data")
    @patch("src.burnup_system.DataLoader.validate_project_data")
    def test_daily_update_safe_no_historical_data(
        self, mock_validate: Mock, mock_load: Mock
    ) -> None:
        """Test daily update when no historical data exists."""
        mock_load.return_value = pd.DataFrame()
        mock_validate.return_value = True

        result = self.system.daily_update_safe("test.xlsx")
        self.assertFalse(result)

    def test_overwrite_task_dates_success(self) -> None:
        """Task date overwrite should update all matching records."""

        self.system.db_model.insert_progress_record(
            ProgressRecord(
                record_date=date(2023, 1, 10),
                project_name="Demo",
                task_name="Implement Feature",
                assignee="Alice",
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 20),
                actual_progress=0.3,
                status="In Progress",
                show_label="v",
                is_backfilled=False,
            )
        )

        result = self.system.overwrite_task_dates(
            "Demo",
            "Implement Feature",
            new_start_date=date(2023, 1, 5),
            new_end_date=date(2023, 1, 25),
        )

        self.assertTrue(result)

        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT start_date, end_date FROM daily_progress
                WHERE project_name = ? AND task_name = ?
                """,
                ("Demo", "Implement Feature"),
            )
            start_value, end_value = cursor.fetchone()

        self.assertEqual(start_value, "2023-01-05")
        self.assertEqual(end_value, "2023-01-25")

    def test_overwrite_task_dates_invalid_range(self) -> None:
        """Invalid date ranges should raise an error."""

        with self.assertRaises(ValueError):
            self.system.overwrite_task_dates(
                "Demo",
                "Implement Feature",
                new_start_date=date(2023, 2, 1),
                new_end_date=date(2023, 1, 1),
            )

    def test_overwrite_task_dates_missing_task(self) -> None:
        """Overwriting a missing task should return False."""

        result = self.system.overwrite_task_dates(
            "Demo",
            "Unknown Task",
            new_start_date=date(2023, 2, 1),
            new_end_date=date(2023, 2, 10),
        )

        self.assertFalse(result)


class TestBurnUpManager(unittest.TestCase):
    """Test cases for BurnUpManager class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.manager = BurnUpManager(self.temp_db.name)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)

    def test_check_status(self) -> None:
        """Test status checking functionality."""
        # This should run without raising exceptions
        self.manager.check_status()


if __name__ == "__main__":
    unittest.main()
