import json
from datetime import datetime, timezone
from pathlib import Path

from regulaai.models.report import RemediationTask


def create_remediation_tasks(tasks: list[RemediationTask], path: str | Path) -> None:
    if not tasks:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    existing += [t.model_dump(mode="json") for t in tasks]
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def append_audit(event: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")