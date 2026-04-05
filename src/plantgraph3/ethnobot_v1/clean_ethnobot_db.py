import sqlite3
from typing import List


class EthnobotDBCleaner:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def drop_tables(self, tables: List[str]) -> None:
        """Drop selected tables safely."""
        conn = self._connect()
        cursor = conn.cursor()

        print("Disabling foreign key constraints...")
        cursor.execute("PRAGMA foreign_keys = OFF;")

        for table in tables:
            print(f"Dropping table if exists: {table}")
            cursor.execute(f"DROP TABLE IF EXISTS {table};")

        print("Re-enabling foreign key constraints...")
        cursor.execute("PRAGMA foreign_keys = ON;")

        conn.commit()
        conn.close()
        print("Table cleanup complete.\n")

    def list_tables(self) -> List[str]:
        """Return remaining tables in the database."""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        conn.close()

        print("Remaining tables:")
        for table in tables:
            print(f" - {table}")

        return tables