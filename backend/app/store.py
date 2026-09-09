import json
from pathlib import Path
from threading import Lock
from typing import Any

class Store:
    def __init__(self, root: str):
        self.path = Path(root) / 'state.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        if not self.path.exists():
            self.write({'projects': {}, 'scenes': {}, 'activities': [], 'diagnostic_events': [], 'jobs': {}})

    def read(self) -> dict[str, Any]:
        with self.lock:
            try:
                return json.loads(self.path.read_text(encoding='utf-8'))
            except (FileNotFoundError, json.JSONDecodeError):
                return {'projects': {}, 'scenes': {}, 'activities': [], 'diagnostic_events': [], 'jobs': {}}

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            tmp.replace(self.path)


    def add_activity(self, item: dict[str, Any], limit: int = 100) -> None:
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                data = {'projects': {}, 'scenes': {}, 'activities': [], 'jobs': {}}
            data.setdefault('activities', [])
            data['activities'].insert(0, item)
            data['activities'] = data['activities'][:limit]
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            tmp.replace(self.path)


    def add_diagnostic_event(self, item: dict[str, Any], limit: int = 1000) -> None:
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                data = {'projects': {}, 'scenes': {}, 'activities': [], 'diagnostic_events': [], 'jobs': {}}
            data.setdefault('diagnostic_events', [])
            data['diagnostic_events'].insert(0, item)
            data['diagnostic_events'] = data['diagnostic_events'][:limit]
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            tmp.replace(self.path)
