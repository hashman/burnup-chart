"""Enhanced database model with date filtering support for queries."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple

import sqlite3

import pandas as pd


@dataclass
class ProgressRecord:
    """Represent a progress record to be stored in the database."""

    record_date: date
    project_name: str
    task_name: str
    assignee: str
    start_date: date
    end_date: date
    actual_progress: float
    status: str
    show_label: str
    is_backfilled: bool = False


class DatabaseModel:
    """Handle all database operations for the burn-up system with date filtering support."""

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

    def insert_progress_record(self, record: ProgressRecord) -> None:
        """Insert or replace a progress record.

        Args:
            record: Progress record to persist
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
                record.record_date.isoformat(),
                record.project_name,
                record.task_name,
                record.assignee,
                record.start_date.isoformat(),
                record.end_date.isoformat(),
                record.actual_progress,
                record.status,
                record.show_label,
                record.is_backfilled,
            ),
        )

        conn.commit()
        conn.close()

    def update_task_dates(
        self,
        project_name: str,
        task_name: str,
        new_start_date: date,
        new_end_date: date,
    ) -> int:
        """Overwrite start and end dates for a specific task.

        Args:
            project_name: Project name that owns the task
            task_name: Name of the task to update
            new_start_date: Updated start date
            new_end_date: Updated end date

        Returns:
            Number of records affected by the update.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE daily_progress
            SET start_date = ?, end_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE project_name = ? AND task_name = ?
            """,
            (
                new_start_date.isoformat(),
                new_end_date.isoformat(),
                project_name,
                task_name,
            ),
        )

        affected_rows = cursor.rowcount

        conn.commit()
        conn.close()

        return affected_rows if affected_rows is not None else 0

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
        self,
        project_name: str,
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[date], List[float]]:
        """Get historical actual progress data for a project with optional date filtering.

        Args:
            project_name: Name of the project
            target_year: Optional year to filter tasks
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Tuple of (dates, progress_values)
        """
        conn = sqlite3.connect(self.db_path)

        # Build the WHERE clause based on filters
        where_conditions = ["project_name = ?"]
        params = [project_name]

        # Add date filtering conditions for tasks
        if target_year:
            year_start = date(target_year, 1, 1).isoformat()
            year_end = date(target_year, 12, 31).isoformat()
            where_conditions.append(
                """
                (start_date >= ? OR end_date >= ?) AND
                (start_date <= ? OR end_date <= ?)
            """
            )
            params.extend([year_start, year_start, year_end, year_end])
        elif start_date or end_date:
            if start_date:
                where_conditions.append("(start_date >= ? OR end_date >= ?)")
                params.extend([start_date.isoformat(), start_date.isoformat()])
            if end_date:
                where_conditions.append("(start_date <= ? OR end_date <= ?)")
                params.extend([end_date.isoformat(), end_date.isoformat()])

        # Add record date filter (always include)
        today = datetime.now().date()
        where_conditions.append("record_date <= ?")
        params.append(today.isoformat())

        where_clause = " AND ".join(where_conditions)

        query = f"""
            SELECT record_date, AVG(actual_progress) as avg_progress
            FROM daily_progress
            WHERE {where_clause}
            GROUP BY record_date
            ORDER BY record_date
        """

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            return [], []

        dates = [
            datetime.strptime(date_str, "%Y-%m-%d").date()
            for date_str in df["record_date"]
        ]
        progress_values = [progress * 100 for progress in df["avg_progress"]]

        return dates, progress_values

    def get_task_annotations(
        self,
        project_name: str,
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[dict]:
        """Get task annotations for due dates with optional date filtering.

        Args:
            project_name: Name of the project
            target_year: Optional year to filter tasks
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of task annotation dictionaries
        """
        conn = sqlite3.connect(self.db_path)

        # Build the WHERE clause based on filters
        where_conditions = ["project_name = ?", "show_label = 'v'"]
        params = [project_name]

        # Add date filtering conditions
        if target_year:
            year_start = date(target_year, 1, 1).isoformat()
            year_end = date(target_year, 12, 31).isoformat()
            where_conditions.append(
                """
                (start_date >= ? OR end_date >= ?) AND
                (start_date <= ? OR end_date <= ?)
            """
            )
            params.extend([year_start, year_start, year_end, year_end])
        elif start_date or end_date:
            if start_date:
                where_conditions.append("start_date >= ?")
                params.extend([start_date.isoformat()])
            if end_date:
                where_conditions.append("end_date <= ?")
                params.extend([end_date.isoformat()])

        where_clause = " AND ".join(where_conditions)

        query = f"""
            SELECT DISTINCT project_name, task_name, end_date, show_label
            FROM daily_progress
            WHERE {where_clause}
            ORDER BY end_date
        """

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            return []

        annotations = []
        for _, row in df.iterrows():
            end_date_obj = datetime.strptime(row["end_date"], "%Y-%m-%d").date()
            annotations.append(
                {
                    "project_name": row["project_name"],
                    "task_name": row["task_name"],
                    "end_date": end_date_obj,
                    "label": f"{row['project_name']} - {row['task_name']}",
                }
            )

        return annotations

    def get_filtered_tasks_from_db(
        self,
        project_name: str,
        target_year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[str]:
        """Get list of task names that match the filtering criteria.

        This is useful for ensuring consistency between Excel filtering and DB filtering.

        Args:
            project_name: Name of the project
            target_year: Optional year to filter tasks
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of task names that match the criteria
        """
        conn = sqlite3.connect(self.db_path)

        # Build the WHERE clause based on filters
        where_conditions = ["project_name = ?"]
        params = [project_name]

        # Add date filtering conditions
        if target_year:
            year_start = date(target_year, 1, 1).isoformat()
            year_end = date(target_year, 12, 31).isoformat()
            where_conditions.append(
                """
                (start_date >= ? OR end_date >= ?) AND
                (start_date <= ? OR end_date <= ?)
            """
            )
            params.extend([year_start, year_start, year_end, year_end])
        elif start_date or end_date:
            if start_date:
                where_conditions.append("(start_date >= ? OR end_date >= ?)")
                params.extend([start_date.isoformat(), start_date.isoformat()])
            if end_date:
                where_conditions.append("(start_date <= ? OR end_date <= ?)")
                params.extend([end_date.isoformat(), end_date.isoformat()])

        where_clause = " AND ".join(where_conditions)

        query = f"""
            SELECT DISTINCT task_name
            FROM daily_progress
            WHERE {where_clause}
            ORDER BY task_name
        """

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df["task_name"].astype(str).tolist() if not df.empty else []

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
