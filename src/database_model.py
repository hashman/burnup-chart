"""Database model for burn-up chart system."""

from datetime import date, datetime
from typing import List, Optional, Tuple

import pandas as pd
import sqlite3


class DatabaseModel:
    """Handle all database operations for the burn-up system."""

    def __init__(self, db_path: str = "burnup_history.db") -> None:
        """Initialize database model.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.initialize_database()

    def initialize_database(self) -> None:
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TEXT NOT NULL,
                project_name TEXT NOT NULL,
                task_name TEXT NOT NULL,
                assignee TEXT,
                start_date TEXT,
                end_date TEXT,
                actual_progress REAL NOT NULL,
                status TEXT,
                show_label TEXT,
                is_backfilled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(record_date, project_name, task_name)
            )
        """
        )

        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")

    def has_historical_data(self, project_name: Optional[str] = None) -> bool:
        """Check if historical data exists.

        Args:
            project_name: Optional project name to filter by

        Returns:
            True if historical data exists, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if project_name:
            cursor.execute(
                "SELECT COUNT(*) FROM daily_progress WHERE project_name = ?",
                (project_name,),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM daily_progress")

        count = cursor.fetchone()[0]
        conn.close()
        return bool(count > 0)

    def insert_progress_record(
        self,
        record_date: date,
        project_name: str,
        task_name: str,
        assignee: str,
        start_date: date,
        end_date: date,
        actual_progress: float,
        status: str,
        show_label: str,
        is_backfilled: bool = False,
    ) -> None:
        """Insert or replace a progress record.

        Args:
            record_date: Date of the record
            project_name: Name of the project
            task_name: Name of the task
            assignee: Person assigned to the task
            start_date: Task start date
            end_date: Task end date
            actual_progress: Actual progress percentage
            status: Task status
            show_label: Show label flag
            is_backfilled: Whether this is backfilled data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO daily_progress (
                record_date, project_name, task_name, assignee,
                start_date, end_date, actual_progress, status, show_label,
                is_backfilled, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (
                record_date.isoformat(),
                project_name,
                task_name,
                assignee,
                start_date.isoformat(),
                end_date.isoformat(),
                actual_progress,
                status,
                show_label,
                is_backfilled,
            ),
        )

        conn.commit()
        conn.close()

    def get_existing_record(
        self, record_date: date, project_name: str, task_name: str
    ) -> Optional[float]:
        """Get existing progress record for a specific date and task.

        Args:
            record_date: Date to check
            project_name: Project name
            task_name: Task name

        Returns:
            Actual progress if record exists, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT actual_progress FROM daily_progress
            WHERE record_date = ? AND project_name = ? AND task_name = ?
        """,
            (record_date.isoformat(), project_name, task_name),
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def get_historical_actual_data(
        self, project_name: str
    ) -> Tuple[List[date], List[float]]:
        """Get historical actual progress data for a project.

        Args:
            project_name: Name of the project

        Returns:
            Tuple of (dates, progress_values)
        """
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT record_date, AVG(actual_progress) as avg_progress
            FROM daily_progress
            WHERE project_name = ? AND record_date <= ?
            GROUP BY record_date
            ORDER BY record_date
        """

        today = datetime.now().date()
        df = pd.read_sql_query(query, conn, params=[project_name, today.isoformat()])

        conn.close()

        if df.empty:
            return [], []

        dates = [
            datetime.strptime(date_str, "%Y-%m-%d").date()
            for date_str in df["record_date"]
        ]
        progress_values = [progress * 100 for progress in df["avg_progress"]]

        return dates, progress_values

    def get_task_annotations(self, project_name: str) -> List[dict]:
        """Get task annotations for due dates.

        Args:
            project_name: Name of the project

        Returns:
            List of task annotation dictionaries
        """
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT DISTINCT project_name, task_name, end_date, show_label
            FROM daily_progress
            WHERE project_name = ? AND show_label = 'v'
            ORDER BY end_date
        """

        df = pd.read_sql_query(query, conn, params=[project_name])
        conn.close()

        if df.empty:
            return []

        annotations = []
        for _, row in df.iterrows():
            end_date = datetime.strptime(row["end_date"], "%Y-%m-%d").date()
            annotations.append(
                {
                    "project_name": row["project_name"],
                    "task_name": row["task_name"],
                    "end_date": end_date,
                    "label": f"{row['project_name']} - {row['task_name']}",
                }
            )

        return annotations

    def get_protection_status(self, project_name: str) -> pd.DataFrame:
        """Get historical protection status for a project.

        Args:
            project_name: Name of the project

        Returns:
            DataFrame with protection status information
        """
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT
                record_date,
                COUNT(*) as task_count,
                SUM(CASE WHEN is_backfilled = TRUE THEN 1 ELSE 0 END) as backfilled_count,
                SUM(CASE WHEN is_backfilled = FALSE THEN 1 ELSE 0 END) as actual_count,
                SUM(CASE WHEN show_label = 'v' THEN 1 ELSE 0 END) as labeled_count
            FROM daily_progress
            WHERE project_name = ?
            GROUP BY record_date
            ORDER BY record_date
        """

        df = pd.read_sql_query(query, conn, params=[project_name])
        conn.close()

        return df
