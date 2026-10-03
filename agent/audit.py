from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.getenv("GET_DATA", Path(__file__).resolve().parent.parent / "data"))
AUDIT_LOG = DATA_DIR / "audit" / "decisions.jsonl"
OVERRIDES_LOG = DATA_DIR / "audit" / "overrides.jsonl"
_lock = threading.Lock()

VERDICTS = {"accept", "override"}

SCHEMA = {
    "run_id": "STRING",
    "created_at": "TIMESTAMP",
    "mode": "STRING",
    "model": "STRING",
    "scenario": "STRING",
    "sources": "STRING",
    "skills_run": "STRING",
    "decision": "STRING",
    "action": "STRING",
    "confidence": "FLOAT64",
    "reasoning_chain": "STRING",
    "evidence": "STRING",
    "total_latency_ms": "INT64",
}

TABLE = os.getenv("BIGQUERY_TABLE", "space_bunny.decisions")
DATASET = os.getenv("BIGQUERY_DATASET", "space_bunny_audit")
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")


def log_run(trace: dict) -> str:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(trace, ensure_ascii=False)
    with _lock:
        with AUDIT_LOG.open("a") as fh:
            fh.write(line + "\n")
    if PROJECT and os.getenv("GET_BIGQUERY", "0") == "1":
        _write_bigquery(line)
    return line


def _write_bigquery(line: str) -> None:
    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=PROJECT)
        dataset_id, table_id = TABLE.split(".", 1)
        table_ref = f"{PROJECT}.{dataset_id}.{table_id}"
        rows = []
        parsed = json.loads(line)
        row = {k: parsed.get(k) for k in SCHEMA if k in parsed}
        rows.append(row)
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            print(f"[audit] bigquery insert rejected: {errors}")
        else:
            print(f"[audit] wrote to {table_ref}")
    except Exception as exc:
        print(f"[audit] bigquery write skipped: {exc}")


def ensure_table() -> str | None:
    if not PROJECT or os.getenv("GET_BIGQUERY", "0") != "1":
        return None
    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=PROJECT)
        dataset = bigquery.Dataset(f"{PROJECT}.{DATASET}")
        dataset.location = os.getenv("BIGQUERY_LOCATION", "asia-south1")
        dataset = client.create_dataset(dataset, exists_ok=True)
        table = bigquery.Table(f"{dataset.reference}.{TABLE.split('.')[-1]}")
        table.schema = [
            bigquery.SchemaField(name, field_type)
            for name, field_type in SCHEMA.items()
        ]
        client.create_table(table, exists_ok=True)
        return table.full_table_id
    except Exception as exc:
        print(f"[audit] ensure_table failed: {exc}")
        return None


def recent(limit: int = 20) -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    lines = AUDIT_LOG.read_text().splitlines()[-limit:]
    out = []
    for raw in lines:
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        row["override"] = get_override(row.get("run_id", ""))
        out.append(row)
    return list(reversed(out))


def known_run_ids() -> set[str]:
    if not AUDIT_LOG.exists():
        return set()
    ids = set()
    for raw in AUDIT_LOG.read_text().splitlines():
        try:
            ids.add(json.loads(raw).get("run_id", ""))
        except json.JSONDecodeError:
            continue
    return ids - {""}


def log_override(run_id: str, verdict: str, note: str) -> dict:
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {sorted(VERDICTS)}")
    OVERRIDES_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "type": "override",
        "run_id": run_id,
        "verdict": verdict,
        "note": note.strip(),
        "recorded_at": now(),
    }
    with _lock:
        with OVERRIDES_LOG.open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def get_override(run_id: str) -> dict | None:
    if not run_id or not OVERRIDES_LOG.exists():
        return None
    latest = None
    for raw in OVERRIDES_LOG.read_text().splitlines():
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if record.get("run_id") == run_id:
            latest = record
    return latest


def now() -> str:
    return datetime.now(timezone.utc).isoformat()