"""Optional JSONL decision logging for local debugging."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


class DecisionLogger:
    """Write one compact JSON record per decision when enabled by env var."""

    def __init__(self):
        log_path = os.environ.get("GUI_AGENT_JSONL_LOG", "").strip()
        self.path = Path(log_path) if log_path else None

    @property
    def enabled(self) -> bool:
        return self.path is not None

    def log(
        self,
        *,
        input_data,
        task_slots,
        memory,
        source: str,
        raw_output: str,
        parsed_decision: Dict[str, Any],
        final_output,
        error: str = "",
    ) -> None:
        if not self.enabled:
            return

        record = {
            "step": getattr(input_data, "step_count", None),
            "instruction": getattr(input_data, "instruction", ""),
            "source": source,
            "task_slots": self._slots_to_dict(task_slots),
            "recent_actions": memory.recent_actions(8) if memory else [],
            "history_actions": getattr(input_data, "history_actions", [])[-8:],
            "raw_output": raw_output or "",
            "parsed_decision": parsed_decision or {},
            "final_action": {
                "action": getattr(final_output, "action", ""),
                "parameters": getattr(final_output, "parameters", {}),
            },
            "candidates": self._candidates_to_dict(getattr(memory, "last_candidates", [])) if memory else [],
            "memory_stage": getattr(memory, "stage", "unknown") if memory else "unknown",
            "pending_after_type": getattr(memory, "pending_after_type", None) if memory else None,
            "error": error,
        }
        self._write(record)

    def _write(self, record: Dict[str, Any]) -> None:
        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _slots_to_dict(task_slots) -> Dict[str, Any]:
        if task_slots is None:
            return {}
        return {
            "app_name": getattr(task_slots, "app_name", ""),
            "task_type": getattr(task_slots, "task_type", ""),
            "shop": getattr(task_slots, "shop", ""),
            "product": getattr(task_slots, "product", ""),
            "origin": getattr(task_slots, "origin", ""),
            "destination": getattr(task_slots, "destination", ""),
            "query_candidates": getattr(task_slots, "query_candidates", []),
        }

    @staticmethod
    def _candidates_to_dict(candidates) -> list:
        values = []
        for candidate in candidates or []:
            if hasattr(candidate, "to_dict"):
                values.append(candidate.to_dict())
            else:
                values.append(str(candidate))
        return values
