"""SQLite ma'lumotlar bazasi: foydalanuvchilar, signallar, sevimlilar, narx tarixi, statistika."""
import time

import aiosqlite

from config import DB_PATH

SCHEMA = [
    "CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, lang TEXT, "
    "digest INTEGER NOT NULL DEFAULT 0, first_seen INTEGER, last_seen INTEGER)",
    "CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
    "name TEXT NOT NULL, target REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER NOT NULL, name TEXT NOT NULL, "
    "PRIMARY KEY(user_id, name))",
    "CREATE TABLE IF NOT EXISTS price_history(name TEXT NOT NULL, ts INTEGER NOT NULL, price REAL NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_ph ON price_history(name, ts)",
    "CREATE TABLE IF NOT EXISTS tracked(name TEXT PRIMARY KEY, last_seen INTEGER)",
    "CREATE TABLE IF NOT EXISTS stats_search(query TEXT PRIMARY KEY, cnt INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS stats_view(name TEXT PRIMARY KEY, cnt INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE IF NOT EXISTS channel_posted(name TEXT PRIMARY KEY, ts INTEGER NOT NULL)",
]


async def _exec(sql: str, params: tuple = ()) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(sql, params)
        await db.commit()


async def _all(sql: str, params: tuple = ()) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, params)
        return await cur.fetchall()


async def _one(sql: str, params: tuple = ()):
    rows = await _all(sql, params)
    return rows[0] if rows else None


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for s in SCHEMA:
            await db.execute(s)
        # Eski versiyadagi bazani yangilash (signal yo'nalishi ustuni)
        cur = await db.execute("PRAGMA table_info(alerts)")
        cols = [r[1] for r in await cur.fetchall()]
        if "direction" not in cols:
            await db.execute("ALTER TABLE alerts ADD COLUMN direction TEXT NOT NULL DEFAULT 'below'")
        await db.commit()


# ---------- Foydalanuvchilar ----------
async def touch_user(uid: int) -> None:
    now = int(time.time())
    await _exec(
        "INSERT INTO users(user_id, first_seen, last_seen) VALUES(?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET last_seen=excluded.last_seen",
        (uid, now, now),
    )


async def get_lang(uid: int):
    row = await _one("SELECT lang FROM users WHERE user_id=?", (uid,))
    return row[0] if row and row[0] else None


async def set_lang(uid: int, lang: str) -> None:
    now = int(time.time())
    await _exec(
        "INSERT INTO users(user_id, lang, first_seen, last_seen) VALUES(?,?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang",
        (uid, lang, now, now),
    )


async def get_digest(uid: int) -> bool:
    row = await _one("SELECT digest FROM users WHERE user_id=?", (uid,))
    return bool(row and row[0])


async def set_digest(uid: int, on: bool) -> None:
    await _exec("UPDATE users SET digest=? WHERE user_id=?", (1 if on else 0, uid))


async def digest_users() -> list:
    return await _all("SELECT user_id, COALESCE(lang,'uz') FROM users WHERE digest=1")


# ---------- Signallar ----------
async def add_alert(uid: int, name: str, target: float, direction: str) -> None:
    await _exec("INSERT INTO alerts(user_id, name, target, direction) VALUES (?,?,?,?)",
                (uid, name, target, direction))
    await track(name)


async def count_alerts(uid: int) -> int:
    row = await _one("SELECT COUNT(*) FROM alerts WHERE user_id=?", (uid,))
    return row[0] if row else 0


async def list_alerts(uid: int) -> list:
    return await _all("SELECT id, name, target, direction FROM alerts WHERE user_id=? ORDER BY id", (uid,))


async def all_alerts() -> list:
    return await _all("SELECT id, user_id, name, target, direction FROM alerts")


async def delete_alert(aid: int, uid: int | None = None) -> None:
    if uid is None:
        await _exec("DELETE FROM alerts WHERE id=?", (aid,))
    else:
        await _exec("DELETE FROM alerts WHERE id=? AND user_id=?", (aid, uid))


# ---------- Sevimlilar ----------
async def is_fav(uid: int, name: str) -> bool:
    return await _one("SELECT 1 FROM favorites WHERE user_id=? AND name=?", (uid, name)) is not None


async def count_favs(uid: int) -> int:
    row = await _one("SELECT COUNT(*) FROM favorites WHERE user_id=?", (uid,))
    return row[0] if row else 0


async def toggle_fav(uid: int, name: str) -> bool:
    """Qo'shilsa True, olib tashlansa False qaytaradi."""
    if await is_fav(uid, name):
        await _exec("DELETE FROM favorites WHERE user_id=? AND name=?", (uid, name))
        return False
    await _exec("INSERT OR IGNORE INTO favorites(user_id, name) VALUES (?,?)", (uid, name))
    await track(name)
    return True


async def list_favs(uid: int) -> list[str]:
    rows = await _all("SELECT name FROM favorites WHERE user_id=? ORDER BY rowid", (uid,))
    return [r[0] for r in rows]


# ---------- Kuzatilayotgan skinlar va narx tarixi ----------
async def track(name: str) -> None:
    await _exec(
        "INSERT INTO tracked(name, last_seen) VALUES(?,?) "
        "ON CONFLICT(name) DO UPDATE SET last_seen=excluded.last_seen",
        (name, int(time.time())),
    )


async def tracked_names() -> list[str]:
    rows = await _all("SELECT name FROM tracked UNION SELECT name FROM favorites UNION SELECT name FROM alerts")
    return [r[0] for r in rows]


async def record_prices(prices: dict) -> None:
    """Har bir skin uchun 30 daqiqada bittadan ko'p nuqta saqlamaydi."""
    if not prices:
        return
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT DISTINCT name FROM price_history WHERE ts > ?", (now - 1800,))
        recent = {r[0] for r in await cur.fetchall()}
        rows = [(n, now, p) for n, p in prices.items() if n not in recent and p]
        if rows:
            await db.executemany("INSERT INTO price_history(name, ts, price) VALUES (?,?,?)", rows)
            await db.commit()


async def get_history(name: str, days: int = 30) -> list:
    since = int(time.time()) - days * 86400
    return await _all("SELECT ts, price FROM price_history WHERE name=? AND ts>=? ORDER BY ts", (name, since))


async def price_at(name: str, target_ts: int, max_gap: int = 36 * 3600):
    """target_ts vaqtidagi (yoki undan oldingi eng yaqin) narx; juda eski bo'lsa None."""
    row = await _one(
        "SELECT ts, price FROM price_history WHERE name=? AND ts<=? ORDER BY ts DESC LIMIT 1",
        (name, target_ts),
    )
    if row and target_ts - row[0] <= max_gap:
        return row[1]
    return None


async def prune_history(days: int = 45) -> None:
    await _exec("DELETE FROM price_history WHERE ts < ?", (int(time.time()) - days * 86400,))


# ---------- Statistika ----------
async def bump_search(query: str) -> None:
    await _exec(
        "INSERT INTO stats_search(query, cnt) VALUES(?,1) ON CONFLICT(query) DO UPDATE SET cnt=cnt+1",
        (query[:60],),
    )


async def bump_view(name: str) -> None:
    await _exec(
        "INSERT INTO stats_view(name, cnt) VALUES(?,1) ON CONFLICT(name) DO UPDATE SET cnt=cnt+1", (name,)
    )


async def _count(sql: str, params: tuple = ()) -> int:
    row = await _one(sql, params)
    return row[0] if row else 0


async def stats_summary() -> dict:
    now = int(time.time())
    return {
        "users": await _count("SELECT COUNT(*) FROM users"),
        "new24": await _count("SELECT COUNT(*) FROM users WHERE first_seen>?", (now - 86400,)),
        "active24": await _count("SELECT COUNT(*) FROM users WHERE last_seen>?", (now - 86400,)),
        "active7": await _count("SELECT COUNT(*) FROM users WHERE last_seen>?", (now - 7 * 86400,)),
        "digest": await _count("SELECT COUNT(*) FROM users WHERE digest=1"),
        "alerts": await _count("SELECT COUNT(*) FROM alerts"),
        "favs": await _count("SELECT COUNT(*) FROM favorites"),
        "tracked": len(await tracked_names()),
        "top_search": await _all("SELECT query, cnt FROM stats_search ORDER BY cnt DESC LIMIT 10"),
        "top_views": await _all("SELECT name, cnt FROM stats_view ORDER BY cnt DESC LIMIT 10"),
    }


# ---------- Umumiy kalit-qiymat va kanal ----------
async def kv_get(key: str):
    row = await _one("SELECT value FROM kv WHERE key=?", (key,))
    return row[0] if row else None


async def kv_set(key: str, value: str) -> None:
    await _exec("INSERT INTO kv(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value))


async def recently_posted(name: str, hours: int) -> bool:
    row = await _one("SELECT ts FROM channel_posted WHERE name=?", (name,))
    return bool(row and row[0] > int(time.time()) - hours * 3600)


async def mark_posted(name: str) -> None:
    await _exec("INSERT INTO channel_posted(name, ts) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET ts=excluded.ts",
                (name, int(time.time())))
