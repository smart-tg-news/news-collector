import aiosqlite
from typing import Set, List
from pathlib import Path
from datetime import datetime


DB_PATH = Path(__file__).resolve().parent / 'feeds.db'

class CrawlerDB:
    """
    Async SQLite client for persisting job data
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: aiosqlite.Connection

    async def initialize(self) -> None:
        """
        Open connection, set PRAGMAs, and create table if it doesn't exist.
        """
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("PRAGMA journal_mode=WAL;")
        await self.conn.execute("PRAGMA foreign_keys = ON;")
        # Create tables
        await self._create_seen_ids_table()
        await self._create_latest_dates_table()
        await self.conn.commit()

    async def _create_seen_ids_table(self) -> None:
        """
        Create the table for GUID-based filtering.
        """
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_item_ids (
                feed_id   TEXT NOT NULL,
                guid      TEXT    NOT NULL,
                PRIMARY KEY(feed_id, guid)
            );
        """)

    async def _create_latest_dates_table(self) -> None:
        """
        Create the table for publish-date-based filtering.
        """
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_latest_dates (
                feed_id     TEXT PRIMARY KEY,
                latest_date TEXT    NOT NULL
            );
        """)

    async def close(self) -> None:
        """
        Close the underlying database connection.
        """
        await self.conn.close()


    """ Methods for id-based filtering """


    async def get_seen_ids(self, feed_id: str) -> Set[str]:
        """
        Fetch all GUIDs previously seen for a given feed_id.
        """
        cursor = await self.conn.execute(
            "SELECT guid FROM seen_item_ids WHERE feed_id = ?",
            (feed_id,)
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

    async def replace_seen_ids(self, feed_id: str, guids: List[str]) -> None:
        """
        Atomically wipe out old GUIDs and insert the current batch.
        """
        await self.conn.execute("BEGIN;")
        await self.conn.execute(
            "DELETE FROM seen_item_ids WHERE feed_id = ?",
            (feed_id,)
        )
        await self.conn.executemany(
            "INSERT INTO seen_item_ids(feed_id, guid) VALUES (?, ?)",
            [(feed_id, guid) for guid in guids]
        )
        await self.conn.commit()


    """ Methods for publish-date-based filtering """


    async def get_latest_date(self, feed_id: str) -> datetime:
        """
        Retrieve the stored latest publish date for a given feed_id.
        Returns datetime.min if no date is stored yet.
        """
        cursor = await self.conn.execute(
            "SELECT latest_date FROM feed_latest_dates WHERE feed_id = ?",
            (feed_id,)
        )
        row = await cursor.fetchone()
        if row:
            # stored as ISO 8601 text
            return datetime.fromisoformat(row[0])
        # fallback when no date is present
        return datetime.min

    async def set_latest_date(self, feed_id: str, latest_date: datetime) -> None:
        """
        Store or update the latest publish date for a given feed_id.
        """
        iso_dt = latest_date.isoformat()
        await self.conn.execute("""
            INSERT INTO feed_latest_dates(feed_id, latest_date)
            VALUES (?, ?)
            ON CONFLICT(feed_id) DO UPDATE SET latest_date = excluded.latest_date;
        """, (feed_id, iso_dt))
        await self.conn.commit()


    """
    TODO: check if connection closed by 
    mistake and reopen before any db commit
    """
