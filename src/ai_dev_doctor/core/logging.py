"""Explicit local JSON-lines logging with minimal fields and mandatory redaction."""

import json
from datetime import UTC, datetime
from typing import TextIO

from ai_dev_doctor.core.redaction import Redactor


def write_event(stream: TextIO, redactor: Redactor, event: str, **fields: object) -> None:
    data = {"timestamp": datetime.now(UTC).isoformat(), "event": event, **fields}
    stream.write(json.dumps(redactor.clean(data), ensure_ascii=True) + "\n")
    stream.flush()
