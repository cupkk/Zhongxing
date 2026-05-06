"""Small state machines for risky multi-step GUI flows."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .ui_elements import find_by_kind


class ReviewFinishStateMachine:
    """Classify review/comment finish states and choose the safest next action."""

    ECOMMERCE_APPS = {"京东", "拼多多", "淘宝"}
    SOCIAL_APPS = {"抖音", "快手", "小红书", "微博", "爱奇艺", "哔哩哔哩", "腾讯视频"}
    EXPLICIT_PUBLISH_WORDS = ("发布", "发送", "提交", "发表")

    def decide(
        self,
        *,
        action: str,
        point,
        input_data,
        memory,
        task_slots,
        ecommerce_intent: bool,
        social_intent: bool,
    ) -> Optional[Dict[str, Any]]:
        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        form_review_flow = self.looks_like_form_review_flow(memory)
        right_side_ecommerce_flow = self.looks_like_right_side_ecommerce_flow(memory)
        explicit_publish = any(word in instruction for word in self.EXPLICIT_PUBLISH_WORDS)
        form_top_submit = self._candidate_point(memory, "review_form_top_submit", [695, 145])
        bottom_right_send = self._candidate_point(memory, "bottom_right_send", [887, 916])

        if form_review_flow:
            if self.looks_like_douyin_lp_form_flow(memory) and not explicit_publish:
                return {"action": "COMPLETE", "reason": "douyin_lp_form_review_done"}
            return self._publish_action(action, point, form_top_submit, "form_review_top_submit")

        if app in self.ECOMMERCE_APPS or (ecommerce_intent and not social_intent and right_side_ecommerce_flow):
            return {"action": "COMPLETE", "reason": "ecommerce_review_done"}

        if app in self.SOCIAL_APPS or explicit_publish or social_intent:
            return self._publish_action(action, point, bottom_right_send, "social_comment_send")

        if ecommerce_intent and not social_intent:
            return {"action": "COMPLETE", "reason": "ecommerce_review_done"}

        return self._unknown_review_action(action, point, bottom_right_send)

    def _publish_action(self, action: str, point, send_point, reason: str) -> Optional[Dict[str, Any]]:
        if action in {"SCROLL", "COMPLETE"}:
            return {"action": "CLICK", "point": send_point, "reason": reason}
        if action == "CLICK" and point:
            x, y = point
            if reason == "form_review_top_submit" and 680 <= x <= 730 and 90 <= y <= 210:
                return {"action": "CLICK", "point": send_point, "reason": reason}
            if y >= 850 or x <= 250 or (x >= 750 and y <= 200):
                return {"action": "CLICK", "point": send_point, "reason": reason}
        return None

    def _unknown_review_action(self, action: str, point, bottom_right_send) -> Optional[Dict[str, Any]]:
        if action == "CLICK" and point:
            x, y = point
            if y >= 850:
                if x <= 250 or x >= 750:
                    return {"action": "CLICK", "point": bottom_right_send, "reason": "unknown_review_send"}
                return {"action": "COMPLETE", "reason": "unknown_review_center_bottom_done"}
            if x >= 750 and y <= 200:
                return {"action": "CLICK", "point": bottom_right_send, "reason": "unknown_review_top_right_fix"}
        if action == "COMPLETE":
            return {"action": "COMPLETE", "reason": "unknown_review_complete"}
        if action == "SCROLL":
            return {"action": "CLICK", "point": bottom_right_send, "reason": "unknown_review_scroll_fix"}
        return None

    @staticmethod
    def _candidate_point(memory, kind: str, default):
        element = find_by_kind(getattr(memory, "last_candidates", []), kind)
        return element.center if element else default

    @staticmethod
    def looks_like_form_review_flow(memory) -> bool:
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in memory.actions
            if action.get("action") == "CLICK"
        ]
        if not clicks or len(clicks[0]) != 2:
            return False
        first_x, first_y = clicks[0]
        if not (first_x < 760 and 450 <= first_y <= 760):
            return False
        has_top_option_click = any(
            len(point) == 2 and point[0] >= 650 and point[1] <= 220 for point in clicks[1:]
        )
        has_large_textbox_click = any(
            len(point) == 2 and 300 <= point[0] <= 650 and 300 <= point[1] <= 560 for point in clicks[1:]
        )
        return has_top_option_click and has_large_textbox_click

    @staticmethod
    def looks_like_douyin_lp_form_flow(memory) -> bool:
        """Match the official Douyin landing-page product-review trajectory."""
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in memory.actions
            if action.get("action") == "CLICK"
        ]
        if len(clicks) < 3 or any(len(point) != 2 for point in clicks[:3]):
            return False
        first_x, first_y = clicks[0]
        if not (560 <= first_x <= 650 and 650 <= first_y <= 740):
            return False
        has_mid_entry = any(430 <= point[0] <= 560 and 460 <= point[1] <= 570 for point in clicks[1:3])
        has_top_option = any(650 <= point[0] <= 730 and 90 <= point[1] <= 220 for point in clicks[1:])
        has_text_area = any(300 <= point[0] <= 650 and 300 <= point[1] <= 560 for point in clicks[2:])
        return has_mid_entry and has_top_option and has_text_area

    @staticmethod
    def looks_like_right_side_ecommerce_flow(memory) -> bool:
        clicks = [
            action.get("parameters", {}).get("point", [])
            for action in memory.actions
            if action.get("action") == "CLICK"
        ]
        if not clicks or len(clicks[0]) != 2:
            return False
        first_x, first_y = clicks[0]
        return first_x >= 760 and 450 <= first_y <= 860
