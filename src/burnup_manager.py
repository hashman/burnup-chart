"""Manager class for burn-up chart system."""

from typing import Optional

import plotly.graph_objects as go

from src.burnup_system import BurnUpSystem


class BurnUpManager:
    """High-level manager for burn-up chart operations."""

    def __init__(self, db_path: str = "burnup_history.db") -> None:
        """Initialize burn-up manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.system = BurnUpSystem(db_path)

    def initialize_project(self, file_path: str = "plan.xlsx") -> bool:
        """Initialize project (only use once per project).

        Args:
            file_path: Path to project data file

        Returns:
            True if initialization successful, False otherwise
        """
        print("🚀 Project initialization (only use once)...")
        result = self.system.initialize_project(file_path)
        if result:
            print("✅ Project initialization completed")
        return result

    def daily_update(self, file_path: str = "plan.xlsx") -> bool:
        """Execute daily update in safe mode.

        Important: Only updates today's records, doesn't modify historical data.

        Args:
            file_path: Path to project data file

        Returns:
            True if update successful, False otherwise
        """
        print("📅 Executing daily update (history protection mode)...")
        result = self.system.daily_update_safe(file_path)
        if result:
            print("✅ Daily update completed (historical data unaffected)")
        return result

    def show_improved_chart(
        self, project_name: str, file_path: str = "plan.xlsx"
    ) -> Optional[go.Figure]:
        """Generate and display improved chart with collision avoidance.

        Args:
            project_name: Name of the project
            file_path: Path to project data file

        Returns:
            Plotly Figure object or None if failed
        """
        chart = self.system.create_burnup_chart(project_name, file_path)
        if chart:
            chart.show()
        return chart

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
