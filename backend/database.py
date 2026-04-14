import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "podbot.db"


async def init_db() -> None:
    """Create tables if they don't exist. Called once at app startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS podcasts (
                id              TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                source_url      TEXT,
                source_filename TEXT,
                llm_provider    TEXT,
                audio_path      TEXT NOT NULL,
                final_script    TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()


async def save_podcast(
    id: str,
    title: str,
    source_url: str | None,
    source_filename: str | None,
    llm_provider: str,
    audio_path: str,
    final_script: str,
) -> None:
    """Insert a completed podcast record into the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO podcasts
                (id, title, source_url, source_filename, llm_provider, audio_path, final_script)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
            """,
            (id, title, source_url, source_filename, llm_provider, audio_path, final_script),
        )
        await db.commit()


async def get_podcast(id: str) -> dict | None:
    """Return a podcast row as a dict, or None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM podcasts WHERE id = ?", (id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_podcasts() -> list[dict]:
    """Return all podcasts ordered newest first, excluding internal fields."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, title, source_url, source_filename, llm_provider, created_at
            FROM podcasts
            ORDER BY created_at DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
