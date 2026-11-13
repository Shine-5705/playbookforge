from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import PlaybookRule


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlaybookStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pass_rate_before REAL,
                    pass_rate_after REAL,
                    simulated INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    parent_version INTEGER,
                    replay_json TEXT,
                    PRIMARY KEY (id, version)
                );
                CREATE TABLE IF NOT EXISTS replays (
                    replay_id TEXT PRIMARY KEY,
                    rule_id TEXT,
                    rule_version INTEGER,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )

    def next_rule_id(self) -> str:
        return f"rule-{uuid.uuid4().hex[:8]}"

    def insert_rule(self, rule: PlaybookRule, replay_payload: dict[str, Any] | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rules (id, version, text, status, pass_rate_before, pass_rate_after,
                                   simulated, created_at, parent_version, replay_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule.id,
                    rule.version,
                    rule.text,
                    rule.status,
                    rule.pass_rate_before,
                    rule.pass_rate_after,
                    1 if rule.simulated else 0,
                    rule.created_at,
                    rule.parent_version,
                    json.dumps(replay_payload) if replay_payload else None,
                ),
            )

    def list_rules(self) -> list[PlaybookRule]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM rules ORDER BY created_at ASC, version ASC"
            ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def get_rule(self, rule_id: str, version: int | None = None) -> PlaybookRule | None:
        with self._connect() as conn:
            if version is None:
                row = conn.execute(
                    "SELECT * FROM rules WHERE id = ? ORDER BY version DESC LIMIT 1",
                    (rule_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM rules WHERE id = ? AND version = ?",
                    (rule_id, version),
                ).fetchone()
        return self._row_to_rule(row) if row else None

    def _row_to_rule(self, row: sqlite3.Row) -> PlaybookRule:
        return PlaybookRule(
            id=row["id"],
            text=row["text"],
            version=row["version"],
            status=row["status"],
            pass_rate_before=row["pass_rate_before"],
            pass_rate_after=row["pass_rate_after"],
            simulated=bool(row["simulated"]),
            created_at=row["created_at"],
            parent_version=row["parent_version"],
        )

    def promote(self, rule_id: str, version: int) -> PlaybookRule:
        rule = self.get_rule(rule_id, version)
        if not rule:
            raise ValueError(f"Rule {rule_id} v{version} not found")
        new = PlaybookRule(
            id=rule.id,
            text=rule.text,
            version=rule.version + 1,
            status="promoted",
            pass_rate_before=rule.pass_rate_before,
            pass_rate_after=rule.pass_rate_after,
            simulated=rule.simulated,
            created_at=_utc_now(),
            parent_version=rule.version,
        )
        self.insert_rule(new)
        return new

    def rollback(self, rule_id: str) -> PlaybookRule:
        current = self.get_rule(rule_id)
        if not current:
            raise ValueError(f"Rule {rule_id} not found")
        parent = self.get_rule(rule_id, current.parent_version) if current.parent_version else None
        text = parent.text if parent else current.text
        rolled = PlaybookRule(
            id=rule_id,
            text=text,
            version=current.version + 1,
            status="rolled_back",
            pass_rate_before=current.pass_rate_before,
            pass_rate_after=current.pass_rate_after,
            simulated=current.simulated,
            created_at=_utc_now(),
            parent_version=current.version,
        )
        self.insert_rule(rolled)
        return rolled

    def save_replay(self, payload: dict[str, Any], rule_id: str | None = None, rule_version: int | None = None) -> str:
        replay_id = f"replay-{uuid.uuid4().hex[:8]}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO replays (replay_id, rule_id, rule_version, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (replay_id, rule_id, rule_version, _utc_now(), json.dumps(payload)),
            )
        return replay_id

    def latest_replay(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM replays ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_meta(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def get_replay_json(self, rule_id: str, version: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT replay_json FROM rules WHERE id = ? AND version = ?",
                (rule_id, version),
            ).fetchone()
        if not row or not row["replay_json"]:
            return None
        return json.loads(row["replay_json"])
