"""SQLite and database storage backends for traces."""

from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from typing import Any, Optional
from pyrewind.core.storage import StorageBackend


class SQLiteStorageBackend(StorageBackend):
    """SQLite-based storage backend for queryable traces.

    Enables powerful queries across traces, steps, and metadata.
    Suitable for large trace collections and analysis.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def initialize(self) -> None:
        """Create database schema."""
        if self._initialized:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        # Traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                module TEXT,
                qualname TEXT,
                python_version TEXT,
                platform TEXT,
                started_at_ns INTEGER,
                ended_at_ns INTEGER,
                result_repr TEXT,
                exception_type TEXT,
                exception_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                step_id INTEGER,
                timestamp_ns INTEGER,
                filename TEXT,
                function TEXT,
                line_no INTEGER,
                locals_json TEXT,
                FOREIGN KEY (trace_id) REFERENCES traces(trace_id),
                UNIQUE(trace_id, step_id)
            )
        """)

        # Create indices for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_traces_module
            ON traces(module)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_trace_id
            ON steps(trace_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_line_no
            ON steps(line_no)
        """)

        conn.commit()
        self._initialized = True

    def store_trace_metadata(self, trace_id: str, metadata: dict[str, Any]) -> None:
        """Store trace metadata."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO traces
            (trace_id, module, qualname, python_version, platform, started_at_ns)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trace_id,
            metadata.get("module", ""),
            metadata.get("qualname", ""),
            metadata.get("python_version", ""),
            metadata.get("platform", ""),
            metadata.get("started_at_ns", 0),
        ))
        conn.commit()

    def store_step(
        self,
        trace_id: str,
        step_id: int,
        step_data: dict[str, Any],
    ) -> None:
        """Store a single trace step."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        locals_json = json.dumps(
            step_data.get("locals_snapshot", {}),
            default=str
        )

        cursor.execute("""
            INSERT OR REPLACE INTO steps
            (trace_id, step_id, timestamp_ns, filename, function, line_no, locals_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            trace_id,
            step_id,
            step_data.get("timestamp_ns", 0),
            step_data.get("filename", ""),
            step_data.get("function", ""),
            step_data.get("line_no", 0),
            locals_json,
        ))
        conn.commit()

    def store_exception(self, trace_id: str, exception_data: dict[str, Any]) -> None:
        """Store exception information."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE traces
            SET exception_type = ?, exception_message = ?
            WHERE trace_id = ?
        """, (
            exception_data.get("type_name", ""),
            exception_data.get("message", ""),
            trace_id,
        ))
        conn.commit()

    def finalize_trace(self, trace_id: str, result_data: dict[str, Any]) -> None:
        """Finalize trace."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE traces
            SET ended_at_ns = ?, result_repr = ?
            WHERE trace_id = ?
        """, (
            result_data.get("ended_at_ns"),
            result_data.get("result_repr", ""),
            trace_id,
        ))
        conn.commit()

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Retrieve a complete trace."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,))
        trace_row = cursor.fetchone()
        if not trace_row:
            return None

        # Get all steps
        cursor.execute("""
            SELECT * FROM steps WHERE trace_id = ? ORDER BY step_id
        """, (trace_id,))
        step_rows = cursor.fetchall()

        trace_data = {
            "trace_id": trace_row["trace_id"],
            "module": trace_row["module"],
            "qualname": trace_row["qualname"],
            "python_version": trace_row["python_version"],
            "platform": trace_row["platform"],
            "started_at_ns": trace_row["started_at_ns"],
            "ended_at_ns": trace_row["ended_at_ns"],
            "result_repr": trace_row["result_repr"],
            "steps": []
        }

        for step_row in step_rows:
            step = {
                "step_id": step_row["step_id"],
                "timestamp_ns": step_row["timestamp_ns"],
                "filename": step_row["filename"],
                "function": step_row["function"],
                "line_no": step_row["line_no"],
                "locals_snapshot": json.loads(step_row["locals_json"]),
            }
            trace_data["steps"].append(step)

        if trace_row["exception_type"]:
            trace_data["exception"] = {
                "type_name": trace_row["exception_type"],
                "message": trace_row["exception_message"],
            }

        return trace_data

    def get_step(self, trace_id: str, step_id: int) -> dict[str, Any] | None:
        """Retrieve a single step."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM steps WHERE trace_id = ? AND step_id = ?
        """, (trace_id, step_id))
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "step_id": row["step_id"],
            "timestamp_ns": row["timestamp_ns"],
            "filename": row["filename"],
            "function": row["function"],
            "line_no": row["line_no"],
            "locals_snapshot": json.loads(row["locals_json"]),
        }

    def list_traces(self) -> list[str]:
        """List all stored trace IDs."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT trace_id FROM traces")
        return [row["trace_id"] for row in cursor.fetchall()]

    def query_traces(
        self,
        module: str | None = None,
        qualname: str | None = None,
        exception_only: bool = False,
    ) -> list[str]:
        """Query traces by criteria."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT trace_id FROM traces WHERE 1=1"
        params = []

        if module:
            query += " AND module = ?"
            params.append(module)

        if qualname:
            query += " AND qualname = ?"
            params.append(qualname)

        if exception_only:
            query += " AND exception_type IS NOT NULL"

        cursor.execute(query, params)
        return [row["trace_id"] for row in cursor.fetchall()]

    def delete_trace(self, trace_id: str) -> None:
        """Delete a trace and all its steps."""
        self.initialize()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM steps WHERE trace_id = ?", (trace_id,))
        cursor.execute("DELETE FROM traces WHERE trace_id = ?", (trace_id,))
        conn.commit()

    def shutdown(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
