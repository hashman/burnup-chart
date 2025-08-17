"""Main burn-up system implementation."""

import datetime as dt
from datetime import date, datetime
from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go

from src.chart_generator import ChartGenerator
from src.data_loader import DataLoader
from src.database_model import DatabaseModel
from src.progress_calculator import ProgressCalculator


class BurnUpSystem:
    """Main burn-up chart system with history protection."""

    def __init__(self, db_path: str = "burnup_history.db") -> None:
        """Initialize burn-up system.

        Args:
            db_path: Path to SQLite database file
        """
        self.today = datetime.now().date()
        self.db_model = DatabaseModel(db_path)
        self.data_loader = DataLoader()
        self.progress_calc = ProgressCalculator()
        self.chart_gen = ChartGenerator()

    def initialize_project(self, file_path: str) -> bool:
        """Initialize project with historical data generation.

        This method should only be called once per project to generate
        smooth historical progress data.

        Args:
            file_path: Path to project data file

        Returns:
            True if initialization successful, False otherwise
        """
        print("🚀 Project initialization...")

        try:
            # Load and validate data
            df = self.data_loader.load_project_data(file_path)
            if not self.data_loader.validate_project_data(df):
                return False

            # Process each project
            project_groups = df.groupby("Project Name")

            for project_name, project_data in project_groups:
                # Check if project already has historical data
                if self.db_model.has_historical_data(project_name):
                    print(
                        f"⚠️ Project {project_name} already has historical data, "
                        "skipping initialization"
                    )
                    continue

                print(f"🔄 Initializing project: {project_name}")

                # Generate smooth progress sequence for this project
                progress_sequence = self.progress_calc.generate_smooth_actual_progress(
                    project_data, self.today
                )

                # Allocate progress to each task proportionally
                for _, task in project_data.iterrows():
                    # Calculate task weight
                    task_weight = (
                        task["Actual"] / project_data["Actual"].mean()
                        if project_data["Actual"].mean() > 0
                        else 1.0
                    )

                    for progress_data in progress_sequence:
                        # Calculate task progress for this date
                        task_progress = progress_data["progress"] * task_weight
                        task_progress = min(
                            task_progress, task["Actual"]
                        )  # Don't exceed current actual progress

                        # Insert historical record
                        self.db_model.insert_progress_record(
                            record_date=progress_data["date"],
                            project_name=project_name,
                            task_name=task["Task Name"],
                            assignee=task["Assign"],
                            start_date=task["Start Date"],
                            end_date=task["End Date"],
                            actual_progress=task_progress,
                            status=task["Status"],
                            show_label=task.get("Show Label", "v"),
                            is_backfilled=progress_data["date"] < self.today,
                        )

                print(f"✅ Project {project_name} initialization completed")

            return True

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False

    def daily_update_safe(self, file_path: str) -> bool:
        """Perform safe daily update.

        Only updates today's records without modifying historical data.

        Args:
            file_path: Path to project data file

        Returns:
            True if update successful, False otherwise
        """
        print(f"📅 Safe daily update - {self.today}")

        try:
            # Load and validate data
            df = self.data_loader.load_project_data(file_path)
            if not self.data_loader.validate_project_data(df):
                return False

            # Check if initialization is needed first
            if not self.db_model.has_historical_data():
                print(
                    "⚠️ No historical data found, please run initialize_project() first"
                )
                return False

            updates = 0

            for _, row in df.iterrows():
                project_name = row["Project Name"]
                task_name = row["Task Name"]
                actual_progress = row["Actual"]
                show_label = row.get("Show Label", "v")

                # Check if today already has a record
                existing_progress = self.db_model.get_existing_record(
                    self.today, project_name, task_name
                )

                if existing_progress is not None:
                    if (
                        abs(existing_progress - actual_progress) > 0.001
                    ):  # Only update if changed
                        print(
                            f"  Updating {task_name}: {existing_progress:.1%} → "
                            f"{actual_progress:.1%}"
                        )
                    else:
                        print(
                            f"  Skipping {task_name}: no progress change "
                            f"({actual_progress:.1%})"
                        )
                        continue
                else:
                    print(f"  Adding {task_name}: {actual_progress:.1%}")

                # Only update or insert today's record
                self.db_model.insert_progress_record(
                    record_date=self.today,
                    project_name=project_name,
                    task_name=task_name,
                    assignee=row["Assign"],
                    start_date=row["Start Date"],
                    end_date=row["End Date"],
                    actual_progress=actual_progress,
                    status=row["Status"],
                    show_label=show_label,
                    is_backfilled=False,
                )

                updates += 1

            print(f"✅ Safe update completed, affected {updates} today's records")
            print("🔒 Historical records completely unaffected")
            return True

        except Exception as e:
            print(f"❌ Daily update failed: {e}")
            return False

    def create_burnup_chart(
        self, project_name: str, file_path: str = "plan.xlsx"
    ) -> Optional[go.Figure]:
        """Create improved burn-up chart with smart annotation positioning.

        Args:
            project_name: Name of the project to chart
            file_path: Path to current project data file

        Returns:
            Plotly Figure object or None if failed
        """
        print(f"📊 Generating improved burn-up chart: {project_name}")

        try:
            # Load current data
            df = self.data_loader.load_project_data(file_path)
            project_data = df[df["Project Name"] == project_name]

            if project_data.empty:
                print("❌ No data found for the specified project")
                return None

            # Get date range
            project_start = project_data["Start Date"].min()
            project_end = project_data["End Date"].max()

            # Create date range with buffer
            dates = []
            current_date = project_start - dt.timedelta(days=5)
            while current_date <= project_end + dt.timedelta(days=5):
                dates.append(current_date)
                current_date += dt.timedelta(days=1)

            # Calculate plan progress
            plan_progress = [
                self.progress_calc.calculate_plan_progress_original(
                    project_data, date_val
                )
                for date_val in dates
            ]

            # Get historical actual data
            actual_dates, actual_progress = self.db_model.get_historical_actual_data(
                project_name
            )

            # Get task annotations
            task_annotations = self.db_model.get_task_annotations(project_name)

            # Create chart
            chart = self.chart_gen.create_burnup_chart(
                project_name=project_name,
                dates=dates,
                plan_progress=plan_progress,
                actual_dates=actual_dates,
                actual_progress=actual_progress,
                task_annotations=task_annotations,
                today=datetime.now(),
            )

            return chart

        except Exception as e:
            print(f"❌ Chart generation failed: {e}")
            return None

    def show_protection_status(self, project_name: str) -> None:
        """Display historical protection status for a project.

        Args:
            project_name: Name of the project
        """
        df = self.db_model.get_protection_status(project_name)

        if df.empty:
            print(f"❌ No data found for {project_name}")
            return

        print(f"\\n🔒 {project_name} Historical Protection Status:")
        print(
            f"  Record date range: {df['record_date'].min()} ~ {df['record_date'].max()}"
        )
        print(f"  Total record days: {len(df)}")
        print(
            f"  Today has records: "
            f"{'Yes' if self.today.isoformat() in df['record_date'].values else 'No'}"
        )

        # Show recent records
        print("\n📊 Recent 5 days' records:")
        recent = df.tail(5)
        for _, row in recent.iterrows():
            date_str = row["record_date"]
            is_today = date_str == self.today.isoformat()
            status = "📅 Today" if is_today else "🔒 History"
            print(
                f"  {date_str}: {row['task_count']} tasks, "
                f"{row['labeled_count']} with labels ({status})"
            )

    def has_historical_data(self, project_name: Optional[str] = None) -> bool:
        """Check if historical data exists.

        Args:
            project_name: Optional project name to filter by

        Returns:
            True if historical data exists, False otherwise
        """
        return self.db_model.has_historical_data(project_name)
