"""Cross-process SQLite cache for deterministic Frama-C verdicts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from acsl_c.framac import Verdict

SCHEMA_VERSION = 1


def verification_key(
    source: str,
    *,
    toolchain_id: str,
    provers: str,
    timeout: int,
    runner_id: str = "",
) -> str:
    payload = json.dumps(
        {
            "schema": SCHEMA_VERSION,
            "source": source,
            "toolchain": toolchain_id,
            "provers": provers,
            "timeout": timeout,
            "runner": runner_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class VerdictCache:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS verdicts (
                cache_key TEXT PRIMARY KEY,
                verdict_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        return connection

    def get(self, key: str) -> Verdict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT verdict_json FROM verdicts WHERE cache_key = ?", (key,)
            ).fetchone()
        return None if row is None else Verdict.from_dict(json.loads(row[0]))

    def put(self, key: str, verdict: Verdict) -> None:
        payload = json.dumps(verdict.to_dict(), sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO verdicts(cache_key, verdict_json, created_at) "
                "VALUES (?, ?, ?)",
                (key, payload, time.time()),
            )


__all__ = ["SCHEMA_VERSION", "VerdictCache", "verification_key"]
