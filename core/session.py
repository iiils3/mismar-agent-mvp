from dataclasses import dataclass, field
from datetime import datetime, timezone
import json, sqlite3
from pathlib import Path

DB = Path(".mismar/session.db")

@dataclass
class Session:
    id: str
    request: str
    mode: str
    status: str = "queued"
    events: list[dict] = field(default_factory=list)

def _db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("create table if not exists sessions (id text primary key, data text not null)")
    return c

def save(s: Session):
    c = _db()
    c.execute("insert or replace into sessions values (?,?)",
              (s.id, json.dumps(s.__dict__, ensure_ascii=False)))
    c.commit(); c.close()

def event(s: Session, kind: str, message: str):
    item = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "message": message}
    s.events.append(item)
    save(s)
    return item
