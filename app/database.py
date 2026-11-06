"""
SQLite Persistence & Automatic Data Ingestion Module.
Automatically seeds children.csv, rounds.json, and encounters.jsonl at startup.
"""
import os
import csv
import json
import sqlite3
from typing import List, Dict, Any, Optional

DB_PATH = os.environ.get("ZERO_DOSE_DB_PATH", "zero_dose.db")
DATA_DIR = os.environ.get("ZERO_DOSE_DATA_DIR", "data")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(force_reseed: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS children (
        child_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        dob TEXT NOT NULL,
        guardian_name TEXT NOT NULL,
        settlement TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rounds (
        round_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS encounters (
        event_id TEXT PRIMARY KEY,
        child_id TEXT NOT NULL,
        round_id TEXT NOT NULL,
        device_id TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        type TEXT NOT NULL,
        zero_dose_answer INTEGER,
        vaccinated_since_last TEXT,
        vaccinated_elsewhere INTEGER,
        comment TEXT,
        FOREIGN KEY (child_id) REFERENCES children(child_id),
        FOREIGN KEY (round_id) REFERENCES rounds(round_id)
    )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM children")
    has_children = cursor.fetchone()[0] > 0

    if not has_children or force_reseed:
        seed_data(conn)

    conn.close()

def seed_data(conn: sqlite3.Connection):
    cursor = conn.cursor()
    children_path = os.path.join(DATA_DIR, "children.csv")
    rounds_path = os.path.join(DATA_DIR, "rounds.json")
    encounters_path = os.path.join(DATA_DIR, "encounters.jsonl")

    # Ingest children
    if os.path.exists(children_path):
        with open(children_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                INSERT OR REPLACE INTO children (child_id, name, dob, guardian_name, settlement)
                VALUES (?, ?, ?, ?, ?)
                """, (row["child_id"], row["name"], row["dob"], row["guardian_name"], row["settlement"]))

    # Ingest rounds
    if os.path.exists(rounds_path):
        with open(rounds_path, "r", encoding="utf-8") as f:
            rounds = json.load(f)
            for r in rounds:
                cursor.execute("""
                INSERT OR REPLACE INTO rounds (round_id, name, start_date, end_date)
                VALUES (?, ?, ?, ?)
                """, (r["round_id"], r["name"], r["start_date"], r["end_date"]))

    # Ingest encounters
    if os.path.exists(encounters_path):
        with open(encounters_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                z_ans = None if e.get("zero_dose_answer") is None else (1 if e.get("zero_dose_answer") else 0)
                v_els = None if e.get("vaccinated_elsewhere") is None else (1 if e.get("vaccinated_elsewhere") else 0)
                cursor.execute("""
                INSERT OR REPLACE INTO encounters (
                    event_id, child_id, round_id, device_id, recorded_at, type,
                    zero_dose_answer, vaccinated_since_last, vaccinated_elsewhere, comment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    e["event_id"],
                    e["child_id"],
                    e["round_id"],
                    e.get("device_id", "DEV-UNKNOWN"),
                    e["recorded_at"],
                    e["type"],
                    z_ans,
                    e.get("vaccinated_since_last"),
                    v_els,
                    e.get("comment")
                ))

    conn.commit()

def get_all_rounds() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rounds ORDER BY start_date ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_all_children() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM children ORDER BY child_id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_child_by_id(child_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM children WHERE child_id = ?", (child_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_encounters_for_child(child_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM encounters WHERE child_id = ? ORDER BY recorded_at ASC, event_id ASC", (child_id,))
    rows = []
    for r in cursor.fetchall():
        d = dict(r)
        d["zero_dose_answer"] = None if d["zero_dose_answer"] is None else bool(d["zero_dose_answer"])
        d["vaccinated_elsewhere"] = None if d["vaccinated_elsewhere"] is None else bool(d["vaccinated_elsewhere"])
        rows.append(d)
    conn.close()
    return rows

def insert_encounter(enc: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    z_ans = None if enc.get("zero_dose_answer") is None else (1 if enc.get("zero_dose_answer") else 0)
    v_els = None if enc.get("vaccinated_elsewhere") is None else (1 if enc.get("vaccinated_elsewhere") else 0)
    cursor.execute("""
    INSERT INTO encounters (
        event_id, child_id, round_id, device_id, recorded_at, type,
        zero_dose_answer, vaccinated_since_last, vaccinated_elsewhere, comment
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        enc["event_id"],
        enc["child_id"],
        enc["round_id"],
        enc.get("device_id", "DEV-PORTAL"),
        enc["recorded_at"],
        enc.get("type", "revisit"),
        z_ans,
        enc.get("vaccinated_since_last"),
        v_els,
        enc.get("comment")
    ))
    conn.commit()
    conn.close()