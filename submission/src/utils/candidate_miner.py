"""Generate lightweight clickable UI element candidates.

The first version is intentionally heuristic. It gives common mobile regions
stable names so downstream logic can choose an element instead of a bare point.
"""

from __future__ import annotations

from typing import List

from .ui_elements import UIElement


class CandidateMiner:
    def build(self, input_data, memory, task_slots) -> List[UIElement]:
        candidates = [
            UIElement(1, "top_search", (160, 35, 840, 130), hint="top search box"),
            UIElement(2, "top_right", (790, 20, 980, 150), hint="top-right search or done"),
            UIElement(3, "first_card", (80, 160, 920, 340), hint="first result or card"),
            UIElement(4, "middle_button", (300, 420, 700, 620), hint="middle primary button"),
            UIElement(5, "bottom_input", (80, 780, 760, 940), hint="bottom input area"),
            # Keep centers equal to the proven legacy points for compatibility.
            UIElement(6, "bottom_right_send", (794, 852, 980, 980), hint="bottom-right send"),
            UIElement(7, "bottom_center_submit", (300, 886, 700, 990), hint="bottom-center submit"),
            UIElement(8, "left_top_back", (0, 20, 140, 150), hint="back or close"),
        ]

        if self._review_like_context(input_data, memory):
            candidates = self._boost(candidates, {"bottom_right_send", "bottom_center_submit", "bottom_input"})
        return candidates

    @staticmethod
    def _review_like_context(input_data, memory) -> bool:
        instruction = input_data.instruction or ""
        if any(word in instruction for word in ("评价", "评论", "晒单", "发表", "发布", "发送", "提交")):
            return True
        return getattr(memory, "pending_after_type", "") == "review_finish"

    @staticmethod
    def _boost(elements: List[UIElement], kinds: set[str]) -> List[UIElement]:
        boosted = []
        for element in elements:
            if element.kind in kinds:
                boosted.append(
                    UIElement(
                        element.element_id,
                        element.kind,
                        element.bbox,
                        element.text,
                        element.hint,
                        element.score + 0.2,
                    )
                )
            else:
                boosted.append(element)
        return boosted
