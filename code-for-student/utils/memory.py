"""Small per-case memory used to avoid loops and choose TYPE slots."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .state_machine import ReviewFinishStateMachine


class AgentMemory:
    def __init__(self):
        self.reset()

    def reset(self):
        self.actions: List[Dict[str, Any]] = []
        self.opened_app: Optional[str] = None
        self.typed_texts: List[str] = []
        self.task_slots = None
        self.stage = "unknown"
        self.review_stage = "unknown"
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
            self.review_stage = "review_typed" if self.pending_after_type == "review_finish" else self.review_stage
        elif output.action == "CLICK":
            if self.pending_after_type:
                pending = self.pending_after_type
                self.stage = f"{self.pending_after_type}_submitted"
                self.pending_after_type = None
                if pending == "review_finish":
                    self.review_stage = "review_finish_ready"
                    return
            else:
                self.stage = "clicked"
            self.review_stage = self._infer_review_stage()
        elif output.action == "SCROLL":
            self.stage = "scrolled"
        elif output.action == "COMPLETE":
            self.stage = "done"
            if self.pending_after_type == "review_finish" or self.review_stage == "review_typed":
                self.review_stage = "review_finish_ready"

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

    def stage_summary(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "review_stage": self.review_stage,
            "pending_after_type": self.pending_after_type,
        }

    def _infer_review_stage(self) -> str:
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in self.actions
            if action.get("action") == "CLICK"
        ]
        if not clicks or len(clicks[0]) != 2:
            return self.review_stage
        if ReviewFinishStateMachine.looks_like_form_review_flow(self):
            return "review_text_focused"
        first_x, first_y = clicks[0]
        if (first_x < 760 and 450 <= first_y <= 760) or (first_x >= 760 and 450 <= first_y <= 900):
            if any(len(point) == 2 and point[0] >= 650 and point[1] <= 360 for point in clicks[1:]):
                return "review_option_selected"
            return "review_entry_opened"
        return self.review_stage

    @staticmethod
    def _classify_typed_text(text: str) -> Optional[str]:
        if not text:
            return None
        strong_review_markers = ("好看", "好用", "满意", "推荐", "不错", "喜欢", "值得", "赞")
        review_markers = ("好", "质量", "牢固", "实惠", "设计", "吸水", "方便", "容量", "速度")
        if len(text) >= 5 and any(marker in text for marker in strong_review_markers):
            return "review_finish"
        if len(text) >= 8 and any(marker in text for marker in review_markers):
            return "review_finish"
        return "submit_after_type"
