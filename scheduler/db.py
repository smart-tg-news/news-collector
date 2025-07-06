import aiosqlite
from typing import Set, List
from pathlib import Path


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
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_item_ids (
                feed_id   INTEGER NOT NULL,
                guid      TEXT    NOT NULL,
                PRIMARY KEY(feed_id, guid)
            );
        """)
        await self.conn.commit()

    async def close(self) -> None:
        """
        Close the underlying database connection.
        """
        await self.conn.close()



    """Methods for id-based filtering"""

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



    """
    TODO: check if connection closed by 
    mistake and reopen before any db commit
    """
