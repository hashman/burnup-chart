"""Unit tests for the burn-up chart system."""

import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pandas as pd
import sqlite3

from src.burnup_manager import BurnUpManager
from src.burnup_system import BurnUpSystem
from src.chart_generator import ChartGenerator
from src.data_loader import DataLoader
from src.database_model import DatabaseModel
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

    @patch("os.path.exists")
    def test_load_project_data_file_not_found(self, mock_exists: Mock) -> None:
        """Test loading data when file doesn't exist."""
        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError):
            self.data_loader.load_project_data("nonexistent.xlsx")

    def test_load_project_data_unsupported_format(self) -> None:
        """Test loading data with unsupported file format."""
        with patch("os.path.exists", return_value=True):
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
        import os

        os.unlink(self.temp_db.name)

    def test_initialize_database(self) -> None:
        """Test database initialization."""
        # Check if table was created
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_progress'"
        )
        result = cursor.fetchone()
        conn.close()

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

        # Retrieve the record
        result = self.db_model.get_existing_record(
            test_date, "Test Project", "Test Task"
        )

        self.assertEqual(result, 0.5)

    def test_has_historical_data_with_data(self) -> None:
        """Test has_historical_data with existing data."""
        # Insert a record first
        self.db_model.insert_progress_record(
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

        result = self.db_model.has_historical_data()
        self.assertTrue(result)

    def test_get_task_annotations(self) -> None:
        """Test getting task annotations."""
        # Insert a record with show_label='v'
        self.db_model.insert_progress_record(
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

        annotations = self.db_model.get_task_annotations("Test Project")

        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0]["task_name"], "Test Task")
        self.assertEqual(annotations[0]["end_date"], date(2023, 1, 31))


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
        import os

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
        import os

        os.unlink(self.temp_db.name)

    def test_check_status(self) -> None:
        """Test status checking functionality."""
        # This should run without raising exceptions
        self.manager.check_status()


if __name__ == "__main__":
    unittest.main()
