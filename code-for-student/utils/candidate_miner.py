"""Generate lightweight clickable UI element candidates.

The first version is intentionally heuristic. It gives common mobile regions
stable names so downstream logic can choose an element instead of a bare point.
"""

from __future__ import annotations

from typing import List

from .ui_elements import UIElement


class CandidateMiner:
    def build(self, input_data, memory, task_slots) -> List[UIElement]:
        top_search_bbox = self._top_search_bbox(input_data, memory, task_slots)
        top_right_bbox = self._top_right_bbox(task_slots)
        first_card_bbox = self._first_card_bbox(input_data, memory, task_slots)
        bottom_right_tab_bbox = self._bottom_right_tab_bbox(input_data, task_slots)
        search_submit_bbox = self._search_submit_bbox(memory, task_slots)
        candidates = [
            UIElement(1, "top_search", top_search_bbox, hint=self._top_search_hint(input_data, memory, task_slots)),
            UIElement(2, "top_right", top_right_bbox, hint="top-right search, skip, close or done"),
            UIElement(3, "first_card", first_card_bbox, hint=self._first_card_hint(input_data, memory, task_slots)),
            UIElement(4, "middle_button", (300, 420, 700, 620), hint="middle primary button"),
            UIElement(5, "bottom_input", (80, 780, 760, 940), hint="bottom input area"),
            # Keep centers equal to the proven legacy points for compatibility.
            UIElement(6, "bottom_right_send", (794, 852, 980, 980), hint="bottom-right send"),
            UIElement(7, "bottom_center_submit", (300, 886, 700, 990), hint="bottom-center review form submit"),
            UIElement(8, "left_top_back", (0, 20, 140, 150), hint="back or close"),
            UIElement(9, "bottom_right_tab", bottom_right_tab_bbox, hint="bottom-right My/Profile tab"),
            UIElement(10, "search_submit_or_suggestion", search_submit_bbox, hint="search button or first suggestion row"),
        ]

        if self._review_like_context(input_data, memory):
            candidates = self._boost(candidates, {"bottom_right_send", "bottom_center_submit", "bottom_input"})
        elif self._just_typed_search(memory):
            candidates = self._boost(candidates, {"top_right", "search_submit_or_suggestion"})
            candidates = self._penalize(candidates, {"bottom_center_submit"})
        elif self._profile_like_context(input_data):
            candidates = self._boost(candidates, {"bottom_right_tab"})
        return candidates

    @staticmethod
    def _review_like_context(input_data, memory) -> bool:
        instruction = input_data.instruction or ""
        if any(word in instruction for word in ("评价", "评论", "晒单", "发表", "发布", "发送", "提交")):
            return True
        return getattr(memory, "pending_after_type", "") == "review_finish"

    @staticmethod
    def _top_right_bbox(task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        if app == "爱奇艺":
            return (725, 25, 945, 67)
        if app == "百度地图":
            return (758, 21, 950, 57)
        if app == "芒果TV":
            return (750, 59, 947, 98)
        if app == "腾讯视频":
            return (831, 59, 962, 99)
        return (790, 20, 980, 150)

    @staticmethod
    def _top_search_bbox(input_data, memory, task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        if app == "芒果TV" and "下载" in instruction and CandidateMiner._last_click_is_bottom_right_tab(memory):
            return (102, 627, 256, 683)
        return (160, 35, 840, 130)

    @staticmethod
    def _top_search_hint(input_data, memory, task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        if app == "芒果TV" and "下载" in instruction and CandidateMiner._last_click_is_bottom_right_tab(memory):
            return "my downloads entry"
        return "top search box"

    @staticmethod
    def _first_card_bbox(input_data, memory, task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        if app == "百度地图" and "导航语音包" in instruction and CandidateMiner._last_click_is_bottom_right_tab(memory):
            return (427, 298, 570, 360)
        return (80, 160, 920, 340)

    @staticmethod
    def _first_card_hint(input_data, memory, task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        if app == "百度地图" and "导航语音包" in instruction and CandidateMiner._last_click_is_bottom_right_tab(memory):
            return "navigation voice package entry"
        return "first result or card"

    @staticmethod
    def _bottom_right_tab_bbox(input_data, task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        if app == "百度地图" and "导航语音包" in instruction:
            return (847, 880, 939, 938)
        if app == "芒果TV" and "下载" in instruction:
            return (850, 894, 941, 947)
        return (820, 860, 970, 980)

    @staticmethod
    def _search_submit_bbox(memory, task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        if app == "腾讯视频":
            return (31, 115, 991, 209)
        if CandidateMiner._just_typed_search(memory):
            return (31, 115, 991, 220)
        return (760, 70, 980, 180)

    @staticmethod
    def _just_typed_search(memory) -> bool:
        last = memory.last_action() if hasattr(memory, "last_action") else None
        return bool(last and last.get("action") == "TYPE" and getattr(memory, "pending_after_type", "") != "review_finish")

    @staticmethod
    def _profile_like_context(input_data) -> bool:
        instruction = input_data.instruction or ""
        return any(word in instruction for word in ("我的", "下载", "个人中心", "语音包"))

    @staticmethod
    def _last_click_is_bottom_right_tab(memory) -> bool:
        last = memory.last_action() if hasattr(memory, "last_action") else None
        if not last or last.get("action") != "CLICK":
            return False
        point = last.get("parameters", {}).get("point", [])
        return len(point) == 2 and point[0] >= 800 and point[1] >= 850

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

    @staticmethod
    def _penalize(elements: List[UIElement], kinds: set[str]) -> List[UIElement]:
        penalized = []
        for element in elements:
            if element.kind in kinds:
                penalized.append(
                    UIElement(
                        element.element_id,
                        element.kind,
                        element.bbox,
                        element.text,
                        element.hint,
                        element.score - 0.2,
                    )
                )
            else:
                penalized.append(element)
        return penalized
