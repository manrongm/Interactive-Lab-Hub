"""Append conversation turns to the Lab 3B interactions CSV dataset."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


FIELDNAMES = [
    "timestamp",
    "participant_id",
    "user_present",
    "transcript",
    "detected_intent",
    "system_response",
    "response_time_seconds",
]
DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "data" / "interactions.csv"


def log_interaction(
    participant_id: str,
    user_present: bool,
    transcript: str,
    detected_intent: str,
    system_response: str,
    response_time_seconds: float,
    log_path: str | Path = DEFAULT_LOG_PATH,
) -> dict[str, str]:
    """Append one completed interaction, creating the folder and CSV header."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "participant_id": participant_id,
        "user_present": str(user_present).lower(),
        "transcript": transcript,
        "detected_intent": detected_intent,
        "system_response": system_response,
        "response_time_seconds": f"{response_time_seconds:.2f}",
    }

    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        if needs_header:
            writer.writeheader()
        writer.writerow(record)

    return record
