"""Enhanced progress calculation utilities with improved date range handling."""

import datetime as dt
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, cast

import pandas as pd


class ProgressCalculator:
    """Handle all progress calculation operations with enhanced date range support."""

    @staticmethod
    def _is_valid_date(value: object) -> bool:
        """Return True when the provided value represents a valid date."""

        return value is not None and not pd.isna(value)

    @classmethod
    def _resolve_task_dates(
        cls, task: pd.Series, use_adjusted: bool
    ) -> Tuple[Optional[date], Optional[date]]:
        """Return the appropriate start/end dates for a task.

        When ``use_adjusted`` is True and adjusted dates are present, those values
        take precedence; otherwise the original plan dates are used.
        """

        start_date: Optional[date] = task.get("Start Date")
        end_date: Optional[date] = task.get("End Date")

        if use_adjusted:
            adjusted_start = task.get("Adjusted Start Date")
            adjusted_end = task.get("Adjusted End Date")
            if cls._is_valid_date(adjusted_start):
                start_date = adjusted_start
            if cls._is_valid_date(adjusted_end):
                end_date = adjusted_end

        if not cls._is_valid_date(start_date) or not cls._is_valid_date(end_date):
            return None, None

        start_date_typed = cast(date, start_date)
        end_date_typed = cast(date, end_date)

        if start_date_typed > end_date_typed:
            # Swap to avoid invalid ranges while still reflecting user data.
            return end_date_typed, start_date_typed

        return start_date_typed, end_date_typed

    @staticmethod
    def calculate_plan_percentage(
        start_date: date, end_date: date, current_date: date
    ) -> float:
        """Calculate individual task plan percentage.

        Args:
            start_date: Task start date
            end_date: Task end date
            current_date: Current evaluation date

        Returns:
            Progress percentage as float between 0.0 and 1.0
        """

        if current_date < start_date:
            return 0.0
        if current_date >= end_date:
            return 1.0

        total_days = (end_date - start_date).days
        elapsed_days = (current_date - start_date).days

        if total_days == 0:
            return 1.0

        return min(elapsed_days / total_days, 1.0)

    @classmethod
    def calculate_plan_progress(
        cls,
        project_data: pd.DataFrame,
        target_date: date,
        *,
        use_adjusted: bool = False,
    ) -> float:
        """Calculate plan progress for the requested plan version.

        Args:
            project_data: DataFrame containing project tasks
            target_date: Date to calculate progress for
            use_adjusted: Whether to prioritise adjusted plan dates

        Returns:
            Overall plan progress percentage
        """

        total_plan = 0.0
        counted_tasks = 0

        for _, task in project_data.iterrows():
            start_date, end_date = cls._resolve_task_dates(task, use_adjusted)
            if start_date is None or end_date is None:
                continue
            task_plan = cls.calculate_plan_percentage(start_date, end_date, target_date)
            total_plan += task_plan
            counted_tasks += 1

        return total_plan / counted_tasks * 100 if counted_tasks > 0 else 0.0

    @classmethod
    def calculate_plan_progress_original(
        cls, project_data: pd.DataFrame, target_date: date
    ) -> float:
        """Backward-compatible helper for legacy callers."""

        return cls.calculate_plan_progress(
            project_data, target_date, use_adjusted=False
        )

    @classmethod
    def calculate_optimal_chart_date_range(
        cls, project_data: pd.DataFrame, buffer_days: int = 5, min_range_days: int = 30
    ) -> Tuple[date, date]:
        """Calculate optimal date range for chart display based on filtered tasks.

        Args:
            project_data: Filtered DataFrame containing project tasks
            buffer_days: Days to add before start and after end
            min_range_days: Minimum range to ensure chart readability

        Returns:
            Tuple of (chart_start_date, chart_end_date)
        """
        if project_data.empty:
            today = datetime.now().date()
            return today - dt.timedelta(days=30), today + dt.timedelta(days=30)

        # Get the actual date range of filtered tasks
        project_start = project_data["Start Date"].min()
        project_end = project_data["End Date"].max()

        # Add buffer
        chart_start = project_start - dt.timedelta(days=buffer_days)
        chart_end = project_end + dt.timedelta(days=buffer_days)

        # Ensure minimum range for readability
        current_range = (chart_end - chart_start).days
        if current_range < min_range_days:
            extra_days = (min_range_days - current_range) // 2
            chart_start -= dt.timedelta(days=extra_days)
            chart_end += dt.timedelta(days=extra_days)

        return chart_start, chart_end

    @classmethod
    def generate_plan_progress_sequence(
        cls, project_data: pd.DataFrame, chart_start_date: date, chart_end_date: date
    ) -> Tuple[List[date], List[float], List[float]]:
        """Generate plan progress sequences for initial and current plan lines.

        Args:
            project_data: Filtered DataFrame containing project tasks
            chart_start_date: Start date for chart
            chart_end_date: End date for chart

        Returns:
            Tuple of (dates, initial_plan_progress, current_plan_progress)
        """
        # Create date range
        dates = []
        current_date = chart_start_date
        while current_date <= chart_end_date:
            dates.append(current_date)
            current_date += dt.timedelta(days=1)

        # Calculate plan progress for each date
        initial_plan_progress = [
            cls.calculate_plan_progress(project_data, date_val, use_adjusted=False)
            for date_val in dates
        ]
        current_plan_progress = [
            cls.calculate_plan_progress(project_data, date_val, use_adjusted=True)
            for date_val in dates
        ]

        return dates, initial_plan_progress, current_plan_progress

    @classmethod
    def get_filtered_date_context(
        cls,
        project_data: pd.DataFrame,
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get context information about the filtered date range.

        Args:
            project_data: Filtered DataFrame containing project tasks
            target_year: Optional year filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with context information
        """
        if project_data.empty:
            return {
                "has_data": False,
                "task_count": 0,
                "date_range": "No data",
                "filter_type": "none",
            }

        task_start = project_data["Start Date"].min()
        task_end = project_data["End Date"].max()
        task_count = len(project_data)

        # Determine filter type and effective range
        if target_year:
            filter_type = "year"
            filter_description = f"Year {target_year}"
            effective_start = max(task_start, date(target_year, 1, 1))
            effective_end = min(task_end, date(target_year, 12, 31))
        elif start_date or end_date:
            filter_type = "date_range"
            filter_description = f"{start_date or 'start'} to {end_date or 'end'}"
            effective_start = max(task_start, start_date) if start_date else task_start
            effective_end = min(task_end, end_date) if end_date else task_end
        else:
            filter_type = "none"
            filter_description = "No filter"
            effective_start = task_start
            effective_end = task_end

        return {
            "has_data": True,
            "task_count": task_count,
            "task_date_range": f"{task_start} to {task_end}",
            "effective_date_range": f"{effective_start} to {effective_end}",
            "filter_type": filter_type,
            "filter_description": filter_description,
            "task_start": task_start,
            "task_end": task_end,
            "effective_start": effective_start,
            "effective_end": effective_end,
        }

    @staticmethod
    def generate_smooth_actual_progress(
        project_data: pd.DataFrame, today: date
    ) -> List[Dict[str, Any]]:
        """Generate smooth actual progress sequence.

        Args:
            project_data: DataFrame containing project tasks (can be filtered)
            today: Current date

        Returns:
            List of progress data dictionaries
        """
        print("🔄 Generating smooth actual progress sequence...")

        # Get overall project start date from filtered data
        project_start = project_data["Start Date"].min()

        # Calculate current overall actual progress (average of filtered tasks)
        current_overall_actual = project_data["Actual"].mean()

        print(f"Project start date (filtered): {project_start}")
        print(
            f"Current overall actual progress (filtered): {current_overall_actual:.1%}"
        )

        # Generate date range from project start to today
        date_range = []
        current_date = project_start
        while current_date <= today:
            date_range.append(current_date)
            current_date += dt.timedelta(days=1)

        # Calculate daily progress (smooth rise)
        total_days = len(date_range)
        progress_per_day = current_overall_actual / total_days if total_days > 0 else 0

        actual_progress_sequence = []
        for i, date_val in enumerate(date_range):
            # Linear rise to current progress
            daily_progress = progress_per_day * (i + 1)
            # Ensure doesn't exceed current actual progress
            daily_progress = min(daily_progress, current_overall_actual)

            actual_progress_sequence.append(
                {"date": date_val, "progress": daily_progress}
            )

        print(
            f"Generated {len(actual_progress_sequence)} actual data points (filtered)"
        )
        return actual_progress_sequence
