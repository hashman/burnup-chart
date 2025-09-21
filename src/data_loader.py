"""Data loading utilities for burn-up chart system."""

import os

import pandas as pd


class DataLoader:
    """Handle data loading operations from various file formats."""

    @staticmethod
    def load_project_data(file_path: str) -> pd.DataFrame:
        """Load project data from Excel or CSV file.

        Args:
            file_path: Path to the data file

        Returns:
            DataFrame with project data

        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == ".xlsx":
            df = pd.read_excel(file_path)
        elif file_extension == ".csv":
            df = pd.read_csv(file_path)
        else:
            raise ValueError(
                f"Unsupported file format: {file_extension}. "
                "Please use .xlsx or .csv files"
            )

        # Convert date columns to date objects
        df["Start Date"] = pd.to_datetime(df["Start Date"]).dt.date
        df["End Date"] = pd.to_datetime(df["End Date"]).dt.date

        return df

    @staticmethod
    def validate_project_data(df: pd.DataFrame) -> bool:
        """Validate that the DataFrame has required columns.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        required_columns = [
            "Project Name",
            "Task Name",
            "Start Date",
            "End Date",
            "Actual",
            "Assign",
            "Status",
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False

        print("✅ Data validation passed")
        return True
