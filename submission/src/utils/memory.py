"""Small per-case memory used to avoid loops and choose TYPE slots."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class AgentMemory:
    def __init__(self):
        self.reset()

    def reset(self):
        self.actions: List[Dict[str, Any]] = []
        self.opened_app: Optional[str] = None
        self.typed_texts: List[str] = []
        self.task_slots = None

    def update(self, output, input_data):
        record = {
            "step": input_data.step_count,
            "action": output.action,
            "parameters": output.parameters,
        }
        self.actions.append(record)
        if output.action == "OPEN":
            self.opened_app = output.parameters.get("app_name")
        elif output.action == "TYPE":
            text = output.parameters.get("text", "")
            if text:
                self.typed_texts.append(text)

    def recent_actions(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.actions[-limit:]

    def last_action(self) -> Optional[Dict[str, Any]]:
        return self.actions[-1] if self.actions else None

    def has_opened(self, app_name: str) -> bool:
        return bool(app_name and self.opened_app == app_name)

    def repeated_click_count(self, point, radius: int = 30) -> int:
        if not point or len(point) != 2:
            return 0
        count = 0
        for action in reversed(self.actions):
            if action.get("action") != "CLICK":
                break
            old = action.get("parameters", {}).get("point", [])
            if len(old) != 2:
                break
            if abs(old[0] - point[0]) <= radius and abs(old[1] - point[1]) <= radius:
                count += 1
            else:
                break
        return count

