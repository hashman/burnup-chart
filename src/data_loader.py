"""Data loading utilities for burn-up chart system."""

from pathlib import Path

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
        path = Path(file_path)
        file_extension = path.suffix.lower()

        if not path.exists():
            fallback_extension = None
            if file_extension == ".xlsx":
                fallback_extension = ".csv"
            elif file_extension == ".csv":
                fallback_extension = ".xlsx"

            if fallback_extension:
                fallback_path = path.with_suffix(fallback_extension)
                if fallback_path.exists():
                    print(
                        "ℹ️ Provided data file not found, using fallback: "
                        f"{fallback_path.name}"
                    )
                    path = fallback_path
                    file_extension = fallback_extension
                else:
                    raise FileNotFoundError(f"File not found: {file_path}")
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        if file_extension == ".xlsx":
            df = pd.read_excel(path)
        elif file_extension == ".csv":
            df = pd.read_csv(path)
        else:
            raise ValueError(
                f"Unsupported file format: {file_extension}. "
                "Please use .xlsx or .csv files"
            )

        # Convert date columns to date objects
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce").dt.date
        df["End Date"] = pd.to_datetime(df["End Date"], errors="coerce").dt.date

        # Optional adjusted plan dates
        optional_date_columns = ["Adjusted Start Date", "Adjusted End Date"]
        for column in optional_date_columns:
            if column in df.columns:
                df[column] = pd.to_datetime(df[column], errors="coerce").dt.date
            else:
                # Ensure downstream logic can safely reference these columns
                df[column] = pd.Series([None] * len(df), dtype="object")

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
