"""Data filtering utilities for burn-up chart system."""

from datetime import date
from typing import Optional, Tuple

import pandas as pd


class DataFilter:
    """Handle data filtering operations for time range and other criteria."""

    @staticmethod
    def filter_by_date_range(
        df: pd.DataFrame,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Filter DataFrame by date range.

        Args:
            df: DataFrame to filter
            start_year: Optional start year filter
            end_year: Optional end year filter
            start_date: Optional specific start date
            end_date: Optional specific end date

        Returns:
            Filtered DataFrame
        """
        filtered_df = df.copy()

        # Filter by year range if specified
        if start_year is not None:
            year_start = date(start_year, 1, 1)
            filtered_df = filtered_df[
                (filtered_df["Start Date"] >= year_start)
                | (filtered_df["End Date"] >= year_start)
            ]

        if end_year is not None:
            year_end = date(end_year, 12, 31)
            filtered_df = filtered_df[
                (filtered_df["Start Date"] <= year_end)
                | (filtered_df["End Date"] <= year_end)
            ]

        # Filter by specific date range if specified
        if start_date is not None:
            # filtered_df = filtered_df[
            #     (filtered_df["Start Date"] >= start_date)
            #     | (filtered_df["End Date"] >= start_date)
            # ]
            filtered_df = filtered_df[(filtered_df["Start Date"] >= start_date)]

        if end_date is not None:
            # filtered_df = filtered_df[
            #     (filtered_df["Start Date"] <= end_date)
            #     | (filtered_df["End Date"] <= end_date)
            # ]
            filtered_df = filtered_df[(filtered_df["End Date"] <= end_date)]

        return filtered_df

    @staticmethod
    def filter_tasks_within_year(df: pd.DataFrame, target_year: int) -> pd.DataFrame:
        """Filter tasks that fall within a specific year.

        Tasks are included if:
        1. They start within the target year, OR
        2. They end within the target year, OR
        3. They span across the target year

        Args:
            df: DataFrame to filter
            target_year: Year to filter for

        Returns:
            Filtered DataFrame containing only tasks relevant to the target year
        """
        year_start = date(target_year, 1, 1)
        year_end = date(target_year, 12, 31)

        # Include tasks that:
        # 1. Start within the year
        # 2. End within the year
        # 3. Span across the year (start before, end after)
        mask = (
            (df["Start Date"] >= year_start)
            & (df["Start Date"] <= year_end)  # Start in year
            | (df["End Date"] >= year_start)
            & (df["End Date"] <= year_end)  # End in year
            | (df["Start Date"] < year_start)
            & (df["End Date"] > year_end)  # Span across year
        )

        return df[mask]

    @staticmethod
    def get_date_range_summary(df: pd.DataFrame) -> dict:
        """Get summary information about the date range in the DataFrame.

        Args:
            df: DataFrame to analyze

        Returns:
            Dictionary with date range information
        """
        if df.empty:
            return {
                "total_tasks": 0,
                "date_range": "No data",
                "start_date": None,
                "end_date": None,
                "years_covered": [],
            }

        min_start = df["Start Date"].min()
        max_end = df["End Date"].max()

        # Get all years covered
        all_dates = pd.concat(
            [pd.to_datetime(df["Start Date"]), pd.to_datetime(df["End Date"])]
        )
        years_covered = sorted(all_dates.dt.year.unique())

        return {
            "total_tasks": len(df),
            "date_range": f"{min_start} to {max_end}",
            "start_date": min_start,
            "end_date": max_end,
            "years_covered": years_covered,
        }

    @staticmethod
    def validate_year_filter(target_year: int, df: pd.DataFrame) -> Tuple[bool, str]:
        """Validate if the year filter will return meaningful results.

        Args:
            target_year: Year to validate
            df: DataFrame to check against

        Returns:
            Tuple of (is_valid, message)
        """
        if df.empty:
            return False, "No data available to filter"

        summary = DataFilter.get_date_range_summary(df)
        years_covered = summary["years_covered"]

        if target_year not in years_covered:
            return False, (
                f"Year {target_year} not found in data. "
                f"Available years: {', '.join(map(str, years_covered))}"
            )

        # Check how many tasks would be included
        filtered_df = DataFilter.filter_tasks_within_year(df, target_year)
        task_count = len(filtered_df)

        if task_count == 0:
            return False, f"No tasks found for year {target_year}"

        return True, f"Found {task_count} tasks for year {target_year}"
