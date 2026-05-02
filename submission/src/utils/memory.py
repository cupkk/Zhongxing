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
        self.stage = "unknown"
        self.pending_after_type: Optional[str] = None
        self.last_candidates: List[Any] = []

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
            self.pending_after_type = self._classify_typed_text(text)
            self.stage = self.pending_after_type or "typed"
        elif output.action == "CLICK":
            if self.pending_after_type:
                self.stage = f"{self.pending_after_type}_submitted"
                self.pending_after_type = None
            else:
                self.stage = "clicked"
        elif output.action == "SCROLL":
            self.stage = "scrolled"
        elif output.action == "COMPLETE":
            self.stage = "done"

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

    @staticmethod
    def _classify_typed_text(text: str) -> Optional[str]:
        if not text:
            return None
        review_markers = ("好", "满意", "质量", "牢固", "实惠", "设计", "吸水", "喜欢", "推荐", "不错")
        if len(text) >= 8 and any(marker in text for marker in review_markers):
            return "review_finish"
        return "submit_after_type"
