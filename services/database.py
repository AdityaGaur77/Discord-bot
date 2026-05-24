import aiosqlite
import logging
from typing import Optional

log = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        """Create all tables if they don't exist."""
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                -- Per-server configuration
                CREATE TABLE IF NOT EXISTS server_config (
                    guild_id    INTEGER PRIMARY KEY,
                    team_number INTEGER,
                    season      INTEGER DEFAULT 2024,
                    timezone    TEXT    DEFAULT 'America/Los_Angeles',
                    tasks_channel    INTEGER,
                    scouting_channel INTEGER,
                    modlog_channel   INTEGER
                );

                -- FTC roles available in the server
                CREATE TABLE IF NOT EXISTS ftc_roles (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name     TEXT    NOT NULL,
                    role_id  INTEGER NOT NULL,
                    UNIQUE(guild_id, name)
                );

                -- Team tasks / to-dos
                CREATE TABLE IF NOT EXISTS tasks (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id   INTEGER NOT NULL,
                    title      TEXT    NOT NULL,
                    owner_id   INTEGER,
                    subteam    TEXT,
                    due_date   TEXT,
                    priority   TEXT    DEFAULT 'medium',
                    status     TEXT    DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Meeting records
                CREATE TABLE IF NOT EXISTS meetings (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id   INTEGER NOT NULL,
                    started_by INTEGER NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at   TIMESTAMP,
                    notes      TEXT    DEFAULT ''
                );

                -- Build / code / CAD log entries
                CREATE TABLE IF NOT EXISTS build_logs (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id   INTEGER NOT NULL,
                    author_id  INTEGER NOT NULL,
                    log_type   TEXT    NOT NULL DEFAULT 'build',
                    entry      TEXT    NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Match scouting data
                CREATE TABLE IF NOT EXISTS scouting (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id     INTEGER NOT NULL,
                    team_number  INTEGER NOT NULL,
                    event_code   TEXT,
                    scout_id     INTEGER,
                    auto_score   INTEGER DEFAULT 0,
                    teleop_score INTEGER DEFAULT 0,
                    endgame_score INTEGER DEFAULT 0,
                    notes        TEXT    DEFAULT '',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Pit scouting data
                CREATE TABLE IF NOT EXISTS pit_scouting (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id     INTEGER NOT NULL,
                    team_number  INTEGER NOT NULL,
                    event_code   TEXT,
                    scout_id     INTEGER,
                    drivetrain   TEXT,
                    max_height   TEXT,
                    auto_capable TEXT,
                    cycle_time   TEXT,
                    strengths    TEXT,
                    weaknesses   TEXT,
                    notes        TEXT    DEFAULT '',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, team_number, event_code)
                );

                -- Outreach events
                CREATE TABLE IF NOT EXISTS outreach (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id   INTEGER NOT NULL,
                    event_name TEXT    NOT NULL,
                    hours      REAL    DEFAULT 0,
                    students   INTEGER DEFAULT 0,
                    date       TEXT,
                    notes      TEXT    DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Moderation warnings
                CREATE TABLE IF NOT EXISTS warnings (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id     INTEGER NOT NULL,
                    user_id      INTEGER NOT NULL,
                    reason       TEXT,
                    moderator_id INTEGER,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Configurable word filter per server
                CREATE TABLE IF NOT EXISTS word_filter (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    word     TEXT    NOT NULL,
                    UNIQUE(guild_id, word)
                );

                -- Attendance records
                CREATE TABLE IF NOT EXISTS attendance (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id   INTEGER NOT NULL,
                    meeting_id INTEGER,
                    user_id    INTEGER NOT NULL,
                    checked_in TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, meeting_id, user_id)
                );

                -- Competition countdown tracking
                CREATE TABLE IF NOT EXISTS countdowns (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id   INTEGER NOT NULL,
                    event_code TEXT    NOT NULL,
                    event_name TEXT,
                    event_date TEXT,
                    channel_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, event_code)
                );
            """)
            await db.commit()
        log.info("Database initialized at %s", self.path)

    # ── Server Config ─────────────────────────────────────────────────────────

    async def get_config(self, guild_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM server_config WHERE guild_id = ?", (guild_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def set_config(self, guild_id: int, **kwargs):
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        updates = ", ".join(f"{k} = excluded.{k}" for k in kwargs)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"""INSERT INTO server_config (guild_id, {cols})
                    VALUES (?, {placeholders})
                    ON CONFLICT(guild_id) DO UPDATE SET {updates}""",
                (guild_id, *kwargs.values()),
            )
            await db.commit()

    # ── Tasks ─────────────────────────────────────────────────────────────────

    async def add_task(self, guild_id, title, owner_id=None, subteam=None, due_date=None, priority="medium") -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO tasks (guild_id, title, owner_id, subteam, due_date, priority) VALUES (?,?,?,?,?,?)",
                (guild_id, title, owner_id, subteam, due_date, priority),
            )
            await db.commit()
            return cur.lastrowid

    async def get_tasks(self, guild_id: int, status: str = "open", subteam: str = None) -> list:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if subteam:
                async with db.execute(
                    "SELECT * FROM tasks WHERE guild_id=? AND status=? AND subteam=? ORDER BY id",
                    (guild_id, status, subteam),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]
            else:
                async with db.execute(
                    "SELECT * FROM tasks WHERE guild_id=? AND status=? ORDER BY id",
                    (guild_id, status),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]

    async def close_task(self, guild_id: int, task_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "UPDATE tasks SET status='done' WHERE id=? AND guild_id=? AND status='open'",
                (task_id, guild_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def assign_task(self, guild_id: int, task_id: int, owner_id: int) -> bool:
        """Reassign a task to a new owner. Returns True if successful."""
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "UPDATE tasks SET owner_id=? WHERE id=? AND guild_id=? AND status='open'",
                (owner_id, task_id, guild_id),
            )
            await db.commit()
            return cur.rowcount > 0

    # ── Meetings ──────────────────────────────────────────────────────────────

    async def start_meeting(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO meetings (guild_id, started_by) VALUES (?, ?)",
                (guild_id, user_id),
            )
            await db.commit()
            return cur.lastrowid

    async def get_active_meeting(self, guild_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM meetings WHERE guild_id=? AND ended_at IS NULL ORDER BY id DESC LIMIT 1",
                (guild_id,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def end_meeting(self, meeting_id: int, notes: str = ""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE meetings SET ended_at=CURRENT_TIMESTAMP, notes=? WHERE id=?",
                (notes, meeting_id),
            )
            await db.commit()

    async def get_recent_meetings(self, guild_id: int, limit: int = 5) -> list:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM meetings WHERE guild_id=? AND ended_at IS NOT NULL ORDER BY id DESC LIMIT ?",
                (guild_id, limit),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ── Build Logs ────────────────────────────────────────────────────────────

    async def add_log(self, guild_id: int, author_id: int, log_type: str, entry: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO build_logs (guild_id, author_id, log_type, entry) VALUES (?,?,?,?)",
                (guild_id, author_id, log_type, entry),
            )
            await db.commit()
            return cur.lastrowid

    async def get_logs(self, guild_id: int, log_type: str = None, limit: int = 10) -> list:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if log_type:
                async with db.execute(
                    "SELECT * FROM build_logs WHERE guild_id=? AND log_type=? ORDER BY id DESC LIMIT ?",
                    (guild_id, log_type, limit),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]
            else:
                async with db.execute(
                    "SELECT * FROM build_logs WHERE guild_id=? ORDER BY id DESC LIMIT ?",
                    (guild_id, limit),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]

    # ── Scouting ──────────────────────────────────────────────────────────────

    async def add_scout(self, guild_id, team_number, event_code, scout_id,
                        auto, teleop, endgame, notes) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """INSERT INTO scouting
                   (guild_id, team_number, event_code, scout_id, auto_score, teleop_score, endgame_score, notes)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (guild_id, team_number, event_code, scout_id, auto, teleop, endgame, notes),
            )
            await db.commit()
            return cur.lastrowid

    async def get_scout_reports(self, guild_id: int, team_number: int) -> list:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM scouting WHERE guild_id=? AND team_number=? ORDER BY id DESC",
                (guild_id, team_number),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_all_scouts(self, guild_id: int, event_code: str = None) -> list:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if event_code:
                async with db.execute(
                    "SELECT * FROM scouting WHERE guild_id=? AND event_code=? ORDER BY team_number",
                    (guild_id, event_code),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]
            async with db.execute(
                "SELECT * FROM scouting WHERE guild_id=? ORDER BY team_number",
                (guild_id,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ── Outreach ──────────────────────────────────────────────────────────────

    async def add_outreach(self, guild_id, event_name, hours, students, date, notes) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO outreach (guild_id, event_name, hours, students, date, notes) VALUES (?,?,?,?,?,?)",
                (guild_id, event_name, hours, students, date, notes),
            )
            await db.commit()
            return cur.lastrowid

    async def get_outreach(self, guild_id: int) -> list:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM outreach WHERE guild_id=? ORDER BY id DESC",
                (guild_id,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ── Moderation ───────────────────────────────────���────────────────────────

    async def add_warning(self, guild_id, user_id, reason, moderator_id) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO warnings (guild_id, user_id, reason, moderator_id) VALUES (?,?,?,?)",
                (guild_id, user_id, reason, moderator_id),
            )
            await db.commit()
            return cur.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int) -> list:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id",
                (guild_id, user_id),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_word_filter(self, guild_id: int) -> list[str]:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT word FROM word_filter WHERE guild_id=?", (guild_id,)
            ) as cur:
                return [row[0] for row in await cur.fetchall()]

    async def add_filter_word(self, guild_id: int, word: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO word_filter (guild_id, word) VALUES (?,?)",
                (guild_id, word.lower()),
            )
            await db.commit()

    async def remove_filter_word(self, guild_id: int, word: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM word_filter WHERE guild_id=? AND word=?",
                (guild_id, word.lower()),
            )
            await db.commit()

    # ── Attendance ────────────────────────────────────────────────────────────

    async def check_in(self, guild_id: int, user_id: int, meeting_id: int = None) -> bool:
        """Record attendance. Returns True if new check-in, False if already checked in."""
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    "INSERT INTO attendance (guild_id, meeting_id, user_id) VALUES (?,?,?)",
                    (guild_id, meeting_id, user_id),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_attendance_for_meeting(self, guild_id: int, meeting_id: int) -> list:
        """Get all attendees for a specific meeting."""
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT user_id, checked_in FROM attendance WHERE guild_id=? AND meeting_id=?",
                (guild_id, meeting_id),
            ) as cur:
                return [{"user_id": row[0], "checked_in": row[1]} for row in await cur.fetchall()]

    async def get_attendance_stats(self, guild_id: int, limit: int = 30) -> list:
        """Get attendance count per user for recent meetings."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT user_id, COUNT(*) as count 
                   FROM attendance 
                   WHERE guild_id=? 
                   GROUP BY user_id 
                   ORDER BY count DESC 
                   LIMIT ?""",
                (guild_id, limit),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_total_meetings_count(self, guild_id: int) -> int:
        """Get total number of completed meetings."""
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM meetings WHERE guild_id=? AND ended_at IS NOT NULL",
                (guild_id,),
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    # ── Countdowns ────────────────────────────────────────────────────────────

    async def set_countdown(self, guild_id: int, event_code: str, event_name: str, 
                           event_date: str, channel_id: int = None):
        """Set or update a competition countdown."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO countdowns (guild_id, event_code, event_name, event_date, channel_id)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(guild_id, event_code) DO UPDATE SET 
                   event_name=excluded.event_name, event_date=excluded.event_date, channel_id=excluded.channel_id""",
                (guild_id, event_code.upper(), event_name, event_date, channel_id),
            )
            await db.commit()

    async def get_countdowns(self, guild_id: int) -> list:
        """Get all countdowns for a guild."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM countdowns WHERE guild_id=? ORDER BY event_date",
                (guild_id,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def remove_countdown(self, guild_id: int, event_code: str) -> bool:
        """Remove a countdown. Returns True if removed."""
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "DELETE FROM countdowns WHERE guild_id=? AND event_code=?",
                (guild_id, event_code.upper()),
            )
            await db.commit()
            return cur.rowcount > 0
