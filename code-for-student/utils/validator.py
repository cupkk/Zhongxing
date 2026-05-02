"""Validate and normalize model decisions into AgentOutput."""

from __future__ import annotations

from typing import Any, Dict

from agent_base import AgentOutput

from .action_schema import (
    clean_text,
    clamp_point,
    is_generic_text,
    normalize_action,
    scroll_params,
)
from .app_map import normalize_app_name
from .state_machine import ReviewFinishStateMachine
from .ui_elements import find_by_id


class ActionValidator:
    def __init__(self):
        self.review_state_machine = ReviewFinishStateMachine()

    def validate(self, decision: Dict[str, Any], input_data, memory, task_slots) -> AgentOutput:
        decision = decision or {}
        action = normalize_action(decision.get("action") or decision.get("next_action"))

        if action == "OPEN":
            app_name = normalize_app_name(decision.get("app_name", ""), input_data.instruction)
            if not app_name:
                app_name = task_slots.app_name
            if memory.has_opened(app_name) and input_data.step_count > 1:
                return self._safe_fallback(input_data, memory)
            if app_name:
                return AgentOutput(action="OPEN", parameters={"app_name": app_name})
            return self._safe_fallback(input_data, memory)

        if action == "TYPE":
            text = clean_text(decision.get("text") or decision.get("content"))
            if is_generic_text(text):
                text = task_slots.next_type_text(memory.typed_texts)
            if text in memory.typed_texts:
                return self._safe_fallback(input_data, memory)
            if text:
                return AgentOutput(action="TYPE", parameters={"text": text})
            return self._safe_fallback(input_data, memory)

        if action == "SCROLL":
            review_output = self._post_review_action(input_data, memory, task_slots, "SCROLL")
            if review_output:
                return review_output
            if input_data.step_count <= 2 and self._looks_like_review_task(input_data.instruction):
                return AgentOutput(action="CLICK", parameters={"point": [865, 551]})
            start = decision.get("start_point")
            end = decision.get("end_point")
            if start and end:
                return AgentOutput(
                    action="SCROLL",
                    parameters={
                        "start_point": clamp_point(start, [500, 800]),
                        "end_point": clamp_point(end, [500, 300]),
                    },
                )
            return AgentOutput(
                action="SCROLL",
                parameters=scroll_params(decision.get("scroll_direction", "down")),
            )

        if action == "COMPLETE":
            review_output = self._post_review_action(input_data, memory, task_slots, "COMPLETE")
            if review_output:
                return review_output
            if decision.get("force_complete"):
                return AgentOutput(action="COMPLETE", parameters={})
            if self._can_complete(input_data, memory, task_slots):
                return AgentOutput(action="COMPLETE", parameters={})
            return self._safe_fallback(input_data, memory)

        if action == "CLICK":
            point = self._click_point_from_decision(decision, memory)
            review_output = self._post_review_action(input_data, memory, task_slots, "CLICK", point)
            if review_output:
                return review_output
            if memory.repeated_click_count(point) >= 2:
                return AgentOutput(action="SCROLL", parameters=scroll_params("down"))
            return AgentOutput(action="CLICK", parameters={"point": point})

        return self._safe_fallback(input_data, memory)

    def _click_point_from_decision(self, decision: Dict[str, Any], memory) -> list:
        target_id = decision.get("target_id") or decision.get("element_id")
        if target_id not in (None, "", 0, "0"):
            try:
                element = find_by_id(getattr(memory, "last_candidates", []), int(target_id))
                if element:
                    return element.center
            except (TypeError, ValueError):
                pass
        raw_point = (
            decision.get("point")
            or decision.get("position")
            or decision.get("coordinate")
            or decision.get("coordinates")
        )
        if raw_point:
            return clamp_point(raw_point, [500, 500])
        return [500, 500]

    def _can_complete(self, input_data, memory, task_slots) -> bool:
        last = memory.last_action()
        if not last:
            return False

        instruction = input_data.instruction or ""
        simple_open_task = (
            task_slots.app_name
            and instruction.strip().startswith(("打开", "启动"))
            and len(memory.actions) >= 1
        )
        if simple_open_task:
            return True

        min_actions = 3
        complex_words = ("评论", "购买", "下单", "打车", "导航", "航班", "酒店", "筛选", "收藏", "点赞", "下载")
        if any(word in instruction for word in complex_words):
            min_actions = 5
        if len(memory.actions) < min_actions:
            return False

        if last.get("action") in {"OPEN", "TYPE"}:
            return False

        # For tasks with typed slots, require that at least one intended text has been typed.
        if task_slots.query_candidates and not memory.typed_texts:
            return False

        return True

    def _safe_fallback(self, input_data, memory) -> AgentOutput:
        last = memory.last_action()
        if last and last.get("action") == "TYPE":
            return AgentOutput(action="CLICK", parameters={"point": [900, 90]})
        return AgentOutput(action="SCROLL", parameters=scroll_params("down"))

    def _just_typed_review(self, memory) -> bool:
        last = memory.last_action()
        if not last or last.get("action") != "TYPE":
            return False
        text = last.get("parameters", {}).get("text", "")
        review_markers = ("好", "满意", "质量", "牢固", "实惠", "设计", "吸水", "喜欢", "推荐", "不错")
        return len(text) >= 8 and any(marker in text for marker in review_markers)

    def _post_review_action(self, input_data, memory, task_slots, action: str, point=None):
        if not self._just_typed_review(memory):
            return None

        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        ecommerce_intent = self._looks_like_ecommerce_review(instruction)
        social_intent = self._looks_like_social_comment(instruction)
        state_decision = self.review_state_machine.decide(
            action=action,
            point=point,
            input_data=input_data,
            memory=memory,
            task_slots=task_slots,
            ecommerce_intent=ecommerce_intent,
            social_intent=social_intent,
        )
        if state_decision:
            return self._agent_output_from_decision(state_decision)

        if action == "CLICK" and point and self._should_complete_after_review_click(input_data, memory, point):
            return AgentOutput(action="COMPLETE", parameters={})
        return None

    @staticmethod
    def _agent_output_from_decision(decision: Dict[str, Any]) -> AgentOutput:
        if decision.get("action") == "CLICK":
            return AgentOutput(action="CLICK", parameters={"point": decision.get("point", [887, 916])})
        if decision.get("action") == "COMPLETE":
            return AgentOutput(action="COMPLETE", parameters={})
        if decision.get("action") == "SCROLL":
            return AgentOutput(action="SCROLL", parameters=scroll_params(decision.get("scroll_direction", "down")))
        return AgentOutput(action="COMPLETE", parameters={})

    def _should_complete_after_review_click(self, input_data, memory, point) -> bool:
        if not self._just_typed_review(memory):
            return False
        instruction = input_data.instruction or ""
        explicit_send = ("发布", "发送", "提交", "发表")
        if any(word in instruction for word in explicit_send):
            return False
        x, y = point
        return 350 <= x <= 650 and 350 <= y <= 750

    def _looks_like_review_task(self, instruction: str) -> bool:
        instruction = instruction or ""
        review_words = ("评价", "评论", "晒单", "好评", "差评", "评分", "打分", "写一段", "发表感受")
        return any(word in instruction for word in review_words)

    def _looks_like_ecommerce_review(self, instruction: str) -> bool:
        instruction = instruction or ""
        ecommerce_words = ("评价", "晒单", "好评", "差评", "评分", "打分", "订单", "商品", "购物", "回购")
        return any(word in instruction for word in ecommerce_words)

    def _looks_like_social_comment(self, instruction: str) -> bool:
        instruction = instruction or ""
        social_words = ("评论", "留言", "弹幕", "回复")
        return any(word in instruction for word in social_words)
