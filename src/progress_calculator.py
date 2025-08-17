"""Progress calculation utilities for burn-up chart system."""

import datetime as dt
from datetime import date
from typing import Any, Dict, List

import pandas as pd


class ProgressCalculator:
    """Handle all progress calculation operations."""

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
    def calculate_plan_progress_original(
        cls, project_data: pd.DataFrame, target_date: date
    ) -> float:
        """Calculate original plan progress (all tasks included).

        Args:
            project_data: DataFrame containing project tasks
            target_date: Date to calculate progress for

        Returns:
            Overall plan progress percentage
        """
        total_plan = 0.0
        task_count = len(project_data)

        for _, task in project_data.iterrows():
            task_plan = cls.calculate_plan_percentage(
                task["Start Date"], task["End Date"], target_date
            )
            total_plan += task_plan

        return total_plan / task_count * 100 if task_count > 0 else 0.0

    @staticmethod
    def generate_smooth_actual_progress(
        project_data: pd.DataFrame, today: date
    ) -> List[Dict[str, Any]]:
        """Generate smooth actual progress sequence.

        Args:
            project_data: DataFrame containing project tasks
            today: Current date

        Returns:
            List of progress data dictionaries
        """
        print("🔄 Generating smooth actual progress sequence...")

        # Get overall project start date
        project_start = project_data["Start Date"].min()

        # Calculate current overall actual progress (average of all tasks)
        current_overall_actual = project_data["Actual"].mean()

        print(f"Project start date: {project_start}")
        print(f"Current overall actual progress: {current_overall_actual:.1%}")

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

        print(f"Generated {len(actual_progress_sequence)} actual data points")
        return actual_progress_sequence
