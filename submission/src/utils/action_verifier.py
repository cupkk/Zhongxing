"""Lightweight decision verification before schema validation.

The verifier only rewrites high-risk decisions where task phase and recent
history make the model choice impossible or clearly unsafe. It keeps normal VLM
choices untouched so target_id grounding still drives the main path.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Optional

from .action_schema import clamp_point
from .ui_elements import find_by_id, find_by_kind


class ActionVerifier:
    REVIEW_ENTRY_KINDS = (
        "right_middle_review_entry",
        "lower_middle_review_entry",
        "right_upper_review_entry",
        "center_review_entry",
        "lower_right_review_entry",
        "bottom_right_review_entry",
        "review_entry_list_row",
        "review_star_or_score_area",
        "middle_button",
    )
    REVIEW_TEXT_ENTRY_KINDS = (
        "review_text_area",
        "review_star_or_score_area",
        "center_review_entry",
    )
    INITIAL_REVIEW_FORBIDDEN_KINDS = {
        "bottom_right_send",
        "bottom_center_submit",
        "left_top_back",
        "keyboard_search_button",
        "top_right_text_button",
    }
    SEARCH_SUBMIT_KINDS = (
        "search_submit_or_suggestion",
        "keyboard_search_button",
        "top_right_text_button",
        "top_right",
        "top_far_right_action",
    )
    FORM_TOP_ACTION_KINDS = (
        "review_form_top_submit",
        "top_mid_right_action",
        "top_right_text_button",
        "top_right",
    )
    POPUP_KINDS = (
        "popup_close_top_right",
        "popup_cancel_bottom",
        "popup_allow_bottom",
        "top_right",
    )
    CONTENT_KINDS = {
        "first_card",
        "media_content_left_panel",
        "media_result_row",
        "media_result_lower_row",
        "full_result_row_top",
        "address_result_full_row_1",
        "address_result_full_row_2",
    }

    def verify(self, decision: Dict[str, Any], input_data, memory, task_slots) -> Dict[str, Any]:
        revised = deepcopy(decision or {})
        action = (revised.get("action") or revised.get("next_action") or "").upper()

        review = self._verify_initial_review(revised, action, input_data, memory, task_slots)
        if review:
            return review

        review_form = self._verify_review_form_text_entry(revised, action, input_data, memory, task_slots)
        if review_form:
            return review_form

        typed = self._verify_after_type(revised, action, memory)
        if typed:
            return typed

        popup = self._verify_popup(revised, action, input_data, memory)
        if popup:
            return popup

        complete = self._verify_complete(revised, action, input_data, memory, task_slots)
        if complete:
            return complete

        return revised

    def _verify_initial_review(self, decision: Dict[str, Any], action: str, input_data, memory, task_slots):
        if input_data.step_count != 1 or getattr(memory, "actions", []):
            return None
        if not self._looks_like_review_task(getattr(input_data, "instruction", "")):
            return None

        if action in {"COMPLETE", "SCROLL", "TYPE"}:
            return self._target_kind_decision(memory, self._initial_review_kinds(task_slots), "verify_initial_review_action")

        if action != "CLICK":
            return None

        kind = self._decision_kind(decision, memory)
        if kind in self.INITIAL_REVIEW_FORBIDDEN_KINDS:
            return self._target_kind_decision(memory, self._initial_review_kinds(task_slots), "verify_initial_review_forbidden_target")
        if getattr(task_slots, "app_name", "") == "京东" and kind in {"center_review_entry", "middle_button"}:
            return self._target_kind_decision(memory, self._initial_review_kinds(task_slots), "verify_initial_review_center_target")

        point = self._decision_point(decision, memory)
        if point:
            x, y = point
            scene = self._initial_review_scene(task_slots)
            if y >= 820 or (x <= 140 and y <= 160):
                return self._target_kind_decision(memory, self._initial_review_kinds(task_slots), "verify_initial_review_forbidden_point")
            if self._is_center_default_point(point):
                return self._target_kind_decision(memory, self._initial_review_kinds(task_slots), "verify_initial_review_center_point")
            if scene in {"douyin", "jingdong"} and x >= 760 and 420 <= y <= 720:
                return self._target_kind_decision(memory, self._initial_review_kinds(task_slots), "verify_initial_review_scene_point")
            if scene == "jingdong" and not (760 <= x <= 950 and 760 <= y <= 900):
                return self._target_kind_decision(memory, self._initial_review_kinds(task_slots), "verify_initial_review_scene_point")
        return None

    def _verify_review_form_text_entry(self, decision: Dict[str, Any], action: str, input_data, memory, task_slots):
        if getattr(memory, "typed_texts", []):
            return None
        if not self._looks_like_review_task(getattr(input_data, "instruction", "")):
            return None

        point = self._decision_point(decision, memory)
        scene = self._initial_review_scene(task_slots)
        if (
            action == "CLICK"
            and scene == "douyin"
            and self._looks_like_douyin_form_top_step(memory)
            and point
            and (
                (300 <= point[0] <= 650 and 520 <= point[1] <= 720)
                or (750 <= point[0] <= 950 and 80 <= point[1] <= 210)
            )
        ):
            return self._target_kind_decision(
                memory,
                self.FORM_TOP_ACTION_KINDS,
                "verify_douyin_form_top_step",
            )

        if (
            scene == "jingdong"
            and self._looks_like_jingdong_review_entry_opened(memory)
            and (
                action in {"TYPE", "SCROLL", "COMPLETE"}
                or (point and 650 <= point[0] <= 850 and 650 <= point[1] <= 820)
            )
        ):
            return {"action": "CLICK", "point": [500, 695], "reason": "verify_jingdong_review_step2_mid_form"}

        if self._looks_like_review_text_focused(memory):
            if action == "TYPE":
                return None
            text = task_slots.next_type_text(getattr(memory, "typed_texts", [])) if task_slots else ""
            if text:
                return {"action": "TYPE", "text": text, "reason": "verify_review_form_ready_to_type"}
            return None

        if not self._looks_like_pre_type_review_form(memory):
            return None

        kind = self._decision_kind(decision, memory)
        invalid_kind = kind in {
            "bottom_input",
            "bottom_right_send",
            "bottom_center_submit",
            "keyboard_search_button",
            "bottom_right_tab",
            "bottom_tab_1",
            "bottom_tab_2",
            "bottom_tab_3",
            "bottom_tab_4",
            "bottom_tab_5",
        }
        invalid_point = bool(point and point[1] >= 760)
        if (
            point
            and scene == "jingdong"
            and 300 <= point[0] <= 650
            and 520 <= point[1] <= 720
        ):
            invalid_point = True
        if action in {"TYPE", "SCROLL", "COMPLETE"} or invalid_kind or invalid_point:
            return self._target_kind_decision(
                memory,
                self.REVIEW_TEXT_ENTRY_KINDS,
                "verify_review_form_text_entry",
            )
        return None

    def _verify_after_type(self, decision: Dict[str, Any], action: str, memory):
        last = memory.last_action() if hasattr(memory, "last_action") else None
        if not last or last.get("action") != "TYPE":
            return None
        pending = getattr(memory, "pending_after_type", None)

        if pending == "submit_after_type":
            kind = self._decision_kind(decision, memory)
            if action in {"COMPLETE", "SCROLL"} or kind in self.CONTENT_KINDS:
                return self._target_kind_decision(memory, self.SEARCH_SUBMIT_KINDS, "verify_search_submit_after_type")
        elif pending == "review_finish":
            if action in {"OPEN", "TYPE"}:
                return {"action": "COMPLETE", "reason": "verify_review_finish_invalid_action"}
        return None

    def _verify_popup(self, decision: Dict[str, Any], action: str, input_data, memory):
        if not self._early_popup_context(input_data, memory):
            return None
        if action != "CLICK":
            return None
        kind = self._decision_kind(decision, memory)
        if kind in self.CONTENT_KINDS:
            return self._target_kind_decision(memory, self.POPUP_KINDS, "verify_popup_content_click")
        return None

    def _verify_complete(self, decision: Dict[str, Any], action: str, input_data, memory, task_slots):
        if action != "COMPLETE":
            return None
        if decision.get("force_complete"):
            return None
        if self._can_complete(input_data, memory, task_slots):
            return None
        last = memory.last_action() if hasattr(memory, "last_action") else None
        if last and last.get("action") == "TYPE":
            return self._target_kind_decision(memory, self.SEARCH_SUBMIT_KINDS, "verify_complete_after_type")
        if getattr(task_slots, "query_candidates", []) and not getattr(memory, "typed_texts", []):
            return {"action": "TYPE", "text": task_slots.next_type_text(memory.typed_texts), "reason": "verify_complete_before_type"}
        return {"action": "SCROLL", "scroll_direction": "down", "reason": "verify_premature_complete"}

    def _target_kind_decision(self, memory, kinds: Iterable[str], reason: str) -> Optional[Dict[str, Any]]:
        for kind in kinds:
            element = find_by_kind(getattr(memory, "last_candidates", []), kind)
            if element:
                return {"action": "CLICK", "target_id": element.element_id, "reason": reason}
        return None

    def _initial_review_kinds(self, task_slots) -> Iterable[str]:
        scene = self._initial_review_scene(task_slots)
        if scene == "jingdong":
            return (
                "bottom_right_review_entry",
                "lower_right_review_entry",
                "right_middle_review_entry",
                "lower_middle_review_entry",
                "right_upper_review_entry",
                "center_review_entry",
                "review_entry_list_row",
                "middle_button",
            )
        if scene == "douyin":
            return (
                "lower_middle_review_entry",
                "right_middle_review_entry",
                "right_upper_review_entry",
                "center_review_entry",
                "lower_right_review_entry",
                "bottom_right_review_entry",
                "review_entry_list_row",
                "middle_button",
            )
        return self.REVIEW_ENTRY_KINDS

    def _initial_review_scene(self, task_slots) -> str:
        app = getattr(task_slots, "app_name", "") or ""
        instruction = getattr(task_slots, "instruction", "") or ""
        if app == "京东" or self._looks_like_jingdong_lp_review(instruction):
            return "jingdong"
        if app == "拼多多" or any(word in instruction for word in ("纸巾", "吸水", "柔软", "亲肤")):
            return "pinduoduo"
        if app == "抖音" or self._looks_like_douyin_lp_review(instruction):
            return "douyin"
        return ""

    @staticmethod
    def _decision_kind(decision: Dict[str, Any], memory) -> str:
        target_id = decision.get("target_id") or decision.get("element_id")
        if target_id not in (None, "", 0, "0"):
            try:
                element = find_by_id(getattr(memory, "last_candidates", []), int(target_id))
                return element.kind if element else ""
            except (TypeError, ValueError):
                return ""
        return ""

    @staticmethod
    def _decision_point(decision: Dict[str, Any], memory) -> Optional[list[int]]:
        target_id = decision.get("target_id") or decision.get("element_id")
        if target_id not in (None, "", 0, "0"):
            try:
                element = find_by_id(getattr(memory, "last_candidates", []), int(target_id))
                return element.center if element else None
            except (TypeError, ValueError):
                return None
        raw_point = (
            decision.get("point")
            or decision.get("position")
            or decision.get("coordinate")
            or decision.get("coordinates")
        )
        return clamp_point(raw_point, [500, 500]) if raw_point else None

    @staticmethod
    def _looks_like_review_task(instruction: str) -> bool:
        review_words = ("评价", "评论", "晒单", "好评", "差评", "评分", "打分", "写一段", "发表感受")
        return any(word in (instruction or "") for word in review_words)

    @staticmethod
    def _looks_like_jingdong_lp_review(instruction: str) -> bool:
        text = instruction or ""
        return any(word in text for word in ("充电宝", "容量", "充电速度", "外出携带"))

    @staticmethod
    def _looks_like_douyin_lp_review(instruction: str) -> bool:
        text = instruction or ""
        if any(word in text for word in ("纸巾", "吸水", "柔软", "亲肤")):
            return False
        if any(word in text for word in ("充电宝", "容量", "充电速度", "外出携带")):
            return False
        return any(word in text for word in ("手机支架", "支架", "吸附", "牢固", "设计美观")) or (
            "评价" in text and not any(app in text for app in ("京东", "拼多多", "淘宝", "快手", "小红书", "抖音"))
        )

    @staticmethod
    def _is_center_default_point(point) -> bool:
        if not point or len(point) != 2:
            return False
        x, y = point
        return 420 <= x <= 620 and 420 <= y <= 620

    @staticmethod
    def _looks_like_pre_type_review_form(memory) -> bool:
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in getattr(memory, "actions", [])
            if action.get("action") == "CLICK"
        ]
        if not clicks or len(clicks[0]) != 2:
            return False
        first_x, first_y = clicks[0]
        has_review_entry = (first_x < 760 and 450 <= first_y <= 760) or (first_x >= 760 and 450 <= first_y <= 900)
        has_score_or_option = any(
            len(point) == 2 and point[0] >= 650 and point[1] <= 360
            for point in clicks[1:]
        )
        has_mid_form_entry = first_x >= 760 and any(
            len(point) == 2 and 420 <= point[0] <= 620 and 600 <= point[1] <= 760
            for point in clicks[1:]
        )
        has_text_area_click = any(
            len(point) == 2 and 300 <= point[0] <= 650 and 300 <= point[1] <= 460
            for point in clicks[1:]
        )
        return has_review_entry and (has_score_or_option or has_mid_form_entry) and not has_text_area_click

    @staticmethod
    def _looks_like_douyin_form_top_step(memory) -> bool:
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in getattr(memory, "actions", [])
            if action.get("action") == "CLICK"
        ]
        if len(clicks) != 2 or any(len(point) != 2 for point in clicks):
            return False
        first_x, first_y = clicks[0]
        second_x, second_y = clicks[1]
        first_is_douyin_entry = 520 <= first_x <= 700 and 620 <= first_y <= 760
        second_is_mid_sheet = 420 <= second_x <= 580 and 460 <= second_y <= 580
        return first_is_douyin_entry and second_is_mid_sheet

    @staticmethod
    def _looks_like_jingdong_review_entry_opened(memory) -> bool:
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in getattr(memory, "actions", [])
            if action.get("action") == "CLICK"
        ]
        if len(clicks) != 1 or len(clicks[0]) != 2:
            return False
        x, y = clicks[0]
        return 760 <= x <= 900 and 760 <= y <= 900

    @staticmethod
    def _looks_like_review_text_focused(memory) -> bool:
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in getattr(memory, "actions", [])
            if action.get("action") == "CLICK"
        ]
        if not clicks:
            return False
        point = clicks[-1]
        if len(point) != 2:
            return False
        x, y = point
        if 300 <= x <= 650 and 300 <= y <= 460:
            return len(clicks) >= 2
        if 300 <= x <= 650 and 460 < y <= 700:
            return len(clicks) >= 4
        return False

    @staticmethod
    def _early_popup_context(input_data, memory) -> bool:
        instruction = input_data.instruction or ""
        return input_data.step_count <= 3 and any(
            word in instruction for word in ("弹窗", "广告", "跳过", "关闭", "权限", "允许", "取消", "升级", "青少年")
        )

    @staticmethod
    def _can_complete(input_data, memory, task_slots) -> bool:
        last = memory.last_action() if hasattr(memory, "last_action") else None
        if not last:
            return False
        if last.get("action") in {"OPEN", "TYPE"}:
            return False
        instruction = input_data.instruction or ""
        min_actions = 3
        if any(word in instruction for word in ("评论", "评价", "购买", "下单", "打车", "导航", "航班", "酒店", "筛选", "收藏", "点赞", "下载")):
            min_actions = 5
        if len(getattr(memory, "actions", [])) < min_actions:
            return False
        if getattr(task_slots, "query_candidates", []) and not getattr(memory, "typed_texts", []):
            return False
        return True
