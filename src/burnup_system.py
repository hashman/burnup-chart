"""Final fixed burn-up system with proper plan progress filtering."""

from datetime import date, datetime
from typing import Optional

import plotly.graph_objects as go

from src.chart_generator import ChartGenerator
from src.data_filter import DataFilter
from src.data_loader import DataLoader
from src.database_model import DatabaseModel
from src.progress_calculator import ProgressCalculator


class BurnUpSystem:
    """Main burn-up chart system with complete date filtering including plan progress."""

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
        self.data_filter = DataFilter()

    def initialize_project(
        self,
        file_path: str,
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> bool:
        """Initialize project with historical data generation and optional date filtering.

        This method should only be called once per project to generate
        smooth historical progress data.

        Args:
            file_path: Path to project data file
            target_year: Optional year to filter tasks (e.g., 2025)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            True if initialization successful, False otherwise
        """
        print("🚀 Project initialization...")

        if target_year:
            print(f"📅 Filtering tasks for year: {target_year}")
        elif start_date or end_date:
            print(f"📅 Filtering tasks for date range: {start_date} to {end_date}")

        try:
            # Load and validate data
            df = self.data_loader.load_project_data(file_path)
            if not self.data_loader.validate_project_data(df):
                return False

            # Apply date filtering if specified
            original_count = len(df)
            if target_year:
                # Validate year filter first
                is_valid, message = self.data_filter.validate_year_filter(
                    target_year, df
                )
                if not is_valid:
                    print(f"❌ Year filter validation failed: {message}")
                    return False
                print(f"✅ Year filter validation: {message}")

                # Apply year filter
                df = self.data_filter.filter_tasks_within_year(df, target_year)
            elif start_date or end_date:
                df = self.data_filter.filter_by_date_range(
                    df, start_date=start_date, end_date=end_date
                )

            filtered_count = len(df)
            if filtered_count < original_count:
                print(f"📊 Filtered from {original_count} to {filtered_count} tasks")

            if filtered_count == 0:
                print("❌ No tasks remaining after filtering")
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

                # Generate smooth progress sequence for this project (using filtered data)
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

    def daily_update_safe(
        self,
        file_path: str,
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> bool:
        """Perform safe daily update with optional date filtering.

        Only updates today's records without modifying historical data.

        Args:
            file_path: Path to project data file
            target_year: Optional year to filter tasks
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            True if update successful, False otherwise
        """
        print(f"📅 Safe daily update - {self.today}")

        if target_year:
            print(f"📅 Filtering tasks for year: {target_year}")
        elif start_date or end_date:
            print(f"📅 Filtering tasks for date range: {start_date} to {end_date}")

        try:
            # Load and validate data
            df = self.data_loader.load_project_data(file_path)
            if not self.data_loader.validate_project_data(df):
                return False

            # Apply date filtering if specified
            original_count = len(df)
            if target_year:
                # Validate year filter first
                is_valid, message = self.data_filter.validate_year_filter(
                    target_year, df
                )
                if not is_valid:
                    print(f"❌ Year filter validation failed: {message}")
                    return False
                print(f"✅ Year filter validation: {message}")

                # Apply year filter
                df = self.data_filter.filter_tasks_within_year(df, target_year)
            elif start_date or end_date:
                df = self.data_filter.filter_by_date_range(
                    df, start_date=start_date, end_date=end_date
                )

            filtered_count = len(df)
            if filtered_count < original_count:
                print(f"📊 Filtered from {original_count} to {filtered_count} tasks")

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
        self,
        project_name: str,
        file_path: str = "plan.xlsx",
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[go.Figure]:
        """Create improved burn-up chart with complete date filtering including plan progress.

        Args:
            project_name: Name of the project to chart
            file_path: Path to current project data file
            target_year: Optional year to filter tasks
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Plotly Figure object or None if failed
        """
        print(f"📊 Generating improved burn-up chart: {project_name}")

        if target_year:
            print(
                f"📅 Filtering ALL data (Excel + Database + Plan) for year: {target_year}"
            )
        elif start_date or end_date:
            print(
                f"📅 Filtering ALL data (Excel + Database + Plan) for date range: {start_date} to {end_date}"
            )

        try:
            # Load current data
            df = self.data_loader.load_project_data(file_path)

            # Apply date filtering if specified
            original_count = len(df)
            if target_year:
                # Validate year filter first
                is_valid, message = self.data_filter.validate_year_filter(
                    target_year, df
                )
                if not is_valid:
                    print(f"❌ Year filter validation failed: {message}")
                    return None
                print(f"✅ Year filter validation: {message}")

                # Apply year filter
                df = self.data_filter.filter_tasks_within_year(df, target_year)
            elif start_date or end_date:
                df = self.data_filter.filter_by_date_range(
                    df, start_date=start_date, end_date=end_date
                )

            filtered_count = len(df)
            if filtered_count < original_count:
                print(
                    f"📊 Filtered Excel data from {original_count} to {filtered_count} tasks"
                )

            project_data = df[df["Project Name"] == project_name]

            if project_data.empty:
                print("❌ No data found for the specified project after filtering")
                return None

            # FIXED: Calculate optimal chart date range based on FILTERED tasks
            print("📊 Calculating optimal chart date range for filtered tasks...")
            chart_start, chart_end = (
                self.progress_calc.calculate_optimal_chart_date_range(
                    project_data, buffer_days=5, min_range_days=30
                )
            )
            print(f"📊 Chart date range: {chart_start} to {chart_end}")

            # FIXED: Generate plan progress sequence for the filtered date range
            print("📊 Generating plan progress for filtered date range...")
            dates, plan_progress = self.progress_calc.generate_plan_progress_sequence(
                project_data, chart_start, chart_end
            )
            print(f"📊 Generated plan progress: {len(dates)} data points")

            # Get filtered historical actual data from database
            print("📊 Getting filtered historical data from database...")
            actual_dates, actual_progress = self.db_model.get_historical_actual_data(
                project_name,
                target_year=target_year,
                start_date=start_date,
                end_date=end_date,
            )
            print(f"📊 Retrieved {len(actual_dates)} filtered historical data points")

            # Get filtered task annotations from database
            print("📊 Getting filtered annotations from database...")
            task_annotations = self.db_model.get_task_annotations(
                project_name,
                target_year=target_year,
                start_date=start_date,
                end_date=end_date,
            )
            print(f"📊 Retrieved {len(task_annotations)} filtered annotations")

            # Get filter context for chart title
            filter_context = self.progress_calc.get_filtered_date_context(
                project_data, target_year, start_date, end_date
            )

            # Create chart title with filter info
            title_suffix = ""
            if filter_context["filter_type"] != "none":
                title_suffix = f" ({filter_context['filter_description']})"

            # Create chart
            chart = self.chart_gen.create_burnup_chart(
                project_name=f"{project_name}{title_suffix}",
                dates=dates,
                plan_progress=plan_progress,
                actual_dates=actual_dates,
                actual_progress=actual_progress,
                task_annotations=task_annotations,
                today=datetime.now(),
            )

            print("✅ Chart generated with COMPLETELY filtered data:")
            print(f"  - Plan date range: {chart_start} to {chart_end}")
            print(f"  - Plan data points: {len(dates)} (filtered)")
            print(f"  - Actual data points: {len(actual_dates)} (filtered)")
            print(f"  - Annotations: {len(task_annotations)} (filtered)")
            print(f"  - Filter context: {filter_context['filter_description']}")

            return chart

        except Exception as e:
            print(f"❌ Chart generation failed: {e}")
            return None

    def show_data_summary(self, file_path: str) -> None:
        """Show summary of data including date ranges and years covered.

        Args:
            file_path: Path to project data file
        """
        try:
            df = self.data_loader.load_project_data(file_path)

            print("\n📊 Data Summary:")
            print("=" * 50)

            # Overall summary
            overall_summary = self.data_filter.get_date_range_summary(df)
            print(f"Total tasks: {overall_summary['total_tasks']}")
            print(f"Date range: {overall_summary['date_range']}")
            print(
                f"Years covered: {', '.join(map(str, overall_summary['years_covered']))}"
            )

            # Project-wise summary
            print("\n📋 Project Breakdown:")
            for project_name in df["Project Name"].unique():
                project_data = df[df["Project Name"] == project_name]
                project_summary = self.data_filter.get_date_range_summary(project_data)
                print(
                    f"  {project_name}: {project_summary['total_tasks']} tasks, "
                    f"{project_summary['date_range']}"
                )

            # Year-wise summary
            print("\n📅 Year Breakdown:")
            for year in overall_summary["years_covered"]:
                year_data = self.data_filter.filter_tasks_within_year(df, year)
                print(f"  {year}: {len(year_data)} tasks")

        except Exception as e:
            print(f"❌ Failed to show data summary: {e}")

    def show_protection_status(self, project_name: str) -> None:
        """Display historical protection status for a project.

        Args:
            project_name: Name of the project
        """
        df = self.db_model.get_protection_status(project_name)

        if df.empty:
            print(f"❌ No data found for {project_name}")
            return

        print(f"\n🔒 {project_name} Historical Protection Status:")
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
