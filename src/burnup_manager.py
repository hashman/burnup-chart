"""Final manager with complete plan progress filtering."""

from datetime import date
from typing import Optional

import plotly.graph_objects as go

from src.burnup_system import BurnUpSystem, DateFilterOptions


class BurnUpManager:
    """High-level manager with COMPLETE date filtering (including plan progress)."""

    def __init__(self, db_path: str = "burnup_history.db") -> None:
        """Initialize burn-up manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.system = BurnUpSystem(db_path)

    def initialize_project(
        self,
        file_path: str = "plan.xlsx",
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> bool:
        """Initialize project (only use once per project) with optional date filtering.

        Args:
            file_path: Path to project data file
            target_year: Optional year to filter tasks (e.g., 2025)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            True if initialization successful, False otherwise
        """
        print("🚀 Project initialization (only use once)...")
        result = self.system.initialize_project(
            file_path, target_year=target_year, start_date=start_date, end_date=end_date
        )
        if result:
            print("✅ Project initialization completed")
        return result

    def daily_update(
        self,
        file_path: str = "plan.xlsx",
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> bool:
        """Execute daily update in safe mode with optional date filtering.

        Important: Only updates today's records, doesn't modify historical data.

        Args:
            file_path: Path to project data file
            target_year: Optional year to filter tasks
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            True if update successful, False otherwise
        """
        print("📅 Executing daily update (history protection mode)...")
        result = self.system.daily_update_safe(
            file_path, target_year=target_year, start_date=start_date, end_date=end_date
        )
        if result:
            print("✅ Daily update completed (historical data unaffected)")
        return result

    def show_improved_chart(
        self,
        project_name: str,
        file_path: str = "plan.xlsx",
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[go.Figure]:
        """Generate and display improved chart with COMPLETE date filtering.

        FINAL FIX: Now properly filters Excel data + Database data + Plan progress.

        Args:
            project_name: Name of the project
            file_path: Path to project data file
            target_year: Optional year to filter tasks (e.g., 2025)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Plotly Figure object or None if failed
        """
        filter_options = DateFilterOptions(
            target_year=target_year, start_date=start_date, end_date=end_date
        )
        chart = self.system.create_burnup_chart(
            project_name,
            file_path,
            filter_options=filter_options,
        )
        if chart:
            chart.show()
        return chart

    def show_data_summary(self, file_path: str = "plan.xlsx") -> None:
        """Display data summary including available years and date ranges.

        Args:
            file_path: Path to project data file
        """
        self.system.show_data_summary(file_path)

    def show_protection_status(self, project_name: str) -> None:
        """Display historical protection status.

        Args:
            project_name: Name of the project
        """
        self.system.show_protection_status(project_name)

    def check_status(self) -> None:
        """Check system status and provide recommendations."""
        has_data = self.system.has_historical_data()
        print("📊 System Status:")
        print(f"  Has historical data: {'Yes' if has_data else 'No'}")
        if not has_data:
            print("  Recommendation: Run initialize_project() first")
        else:
            print("  Can safely execute daily_update()")

    def overwrite_task_dates(
        self,
        project_name: str,
        task_name: str,
        new_start_date: date,
        new_end_date: date,
    ) -> bool:
        """Overwrite start and end dates for a specific task."""

        print(
            f"✏️ Overwriting dates for task '{task_name}' in project '{project_name}' "
            f"→ {new_start_date} to {new_end_date}"
        )
        return self.system.overwrite_task_dates(
            project_name, task_name, new_start_date, new_end_date
        )

    # Convenience methods for year-specific operations
    def initialize_project_for_year(self, file_path: str, year: int) -> bool:
        """Initialize project for a specific year.

        Args:
            file_path: Path to project data file
            year: Target year (e.g., 2025)

        Returns:
            True if initialization successful, False otherwise
        """
        return self.initialize_project(file_path, target_year=year)

    def daily_update_for_year(self, file_path: str, year: int) -> bool:
        """Execute daily update for a specific year.

        Args:
            file_path: Path to project data file
            year: Target year (e.g., 2025)

        Returns:
            True if update successful, False otherwise
        """
        return self.daily_update(file_path, target_year=year)

    def show_chart_for_year(
        self, project_name: str, file_path: str, year: int
    ) -> Optional[go.Figure]:
        """Generate chart for a specific year.

        FINAL FIX: Now completely filters all data including plan progress.

        Args:
            project_name: Name of the project
            file_path: Path to project data file
            year: Target year (e.g., 2025)

        Returns:
            Plotly Figure object or None if failed
        """
        return self.show_improved_chart(project_name, file_path, target_year=year)
