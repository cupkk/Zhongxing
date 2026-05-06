"""Focused tests for high-risk ActionVerifier rewrites."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "code-for-student"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_base import AgentInput  # noqa: E402
from utils.action_verifier import ActionVerifier  # noqa: E402
from utils.candidate_miner import CandidateMiner  # noqa: E402
from utils.memory import AgentMemory  # noqa: E402
from utils.task_parser import parse_task  # noqa: E402
from utils.ui_elements import find_by_kind  # noqa: E402


@dataclass
class Scenario:
    name: str
    instruction: str
    step_count: int
    decision: Dict[str, Any]
    prior_actions: List[Dict[str, Any]] = field(default_factory=list)
    typed_texts: List[str] = field(default_factory=list)
    pending_after_type: str | None = None
    expected_action: str = ""
    expected_kind: str = ""
    expected_point: List[int] | None = None
    expected_text: str = ""
    expected_reason: str = ""


def make_context(scenario: Scenario):
    input_data = AgentInput(
        instruction=scenario.instruction,
        current_image=Image.new("RGB", (480, 1056), "white"),
        step_count=scenario.step_count,
    )
    task_slots = parse_task(scenario.instruction)
    memory = AgentMemory()
    memory.actions = list(scenario.prior_actions)
    memory.typed_texts = list(scenario.typed_texts)
    memory.pending_after_type = scenario.pending_after_type
    memory.stage = scenario.pending_after_type or "unknown"
    memory.task_slots = task_slots
    memory.last_candidates = CandidateMiner().build(input_data, memory, task_slots)
    return input_data, memory, task_slots


def assert_scenario(scenario: Scenario) -> None:
    input_data, memory, task_slots = make_context(scenario)
    revised = ActionVerifier().verify(scenario.decision, input_data, memory, task_slots)
    assert revised.get("action") == scenario.expected_action, f"{scenario.name}: {revised}"
    if scenario.expected_kind:
        element = find_by_kind(memory.last_candidates, scenario.expected_kind)
        assert element is not None, f"{scenario.name}: missing candidate {scenario.expected_kind}"
        assert revised.get("target_id") == element.element_id, f"{scenario.name}: {revised}, expected {element}"
    if scenario.expected_point is not None:
        assert revised.get("point") == scenario.expected_point, f"{scenario.name}: {revised}"
    if scenario.expected_text:
        assert revised.get("text") == scenario.expected_text, f"{scenario.name}: {revised}"
    if scenario.expected_reason:
        assert revised.get("reason") == scenario.expected_reason, f"{scenario.name}: {revised}"


def build_scenarios() -> List[Scenario]:
    return [
        Scenario(
            name="initial_review_forbidden_send_target",
            instruction="去抖音给商品写评价：这个东西很好用，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "target_id": 6},
            expected_action="CLICK",
            expected_kind="lower_middle_review_entry",
            expected_reason="verify_initial_review_forbidden_target",
        ),
        Scenario(
            name="initial_review_forbidden_back_point",
            instruction="去拼多多晒单评价：这个东西很好用，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [70, 85]},
            expected_action="CLICK",
            expected_kind="right_middle_review_entry",
            expected_reason="verify_initial_review_forbidden_point",
        ),
        Scenario(
            name="initial_jingdong_center_default_to_bottom_entry",
            instruction="去京东评价充电宝：这个充电宝很好用，容量大，充电速度快，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [500, 500]},
            expected_action="CLICK",
            expected_kind="bottom_right_review_entry",
            expected_reason="verify_initial_review_center_point",
        ),
        Scenario(
            name="official_lp_jingdong_without_app_name_right_default_to_bottom_entry",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [865, 550]},
            expected_action="CLICK",
            expected_kind="bottom_right_review_entry",
            expected_reason="verify_initial_review_scene_point",
        ),
        Scenario(
            name="official_lp_jingdong_without_app_name_lower_default_to_bottom_entry",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [605, 695]},
            expected_action="CLICK",
            expected_kind="bottom_right_review_entry",
            expected_reason="verify_initial_review_scene_point",
        ),
        Scenario(
            name="official_lp_douyin_without_app_name_right_default_to_lower_entry",
            instruction="给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=1,
            decision={"action": "CLICK", "point": [865, 550]},
            expected_action="CLICK",
            expected_kind="lower_middle_review_entry",
            expected_reason="verify_initial_review_scene_point",
        ),
        Scenario(
            name="initial_review_scroll_to_entry",
            instruction="去淘宝写一段商品评价：这个东西很好用，值得推荐！",
            step_count=1,
            decision={"action": "SCROLL", "scroll_direction": "down"},
            expected_action="CLICK",
            expected_kind="right_middle_review_entry",
            expected_reason="verify_initial_review_action",
        ),
        Scenario(
            name="official_douyin_step3_mid_click_to_top_submit",
            instruction="\u7ed9\u624b\u673a\u652f\u67b6\u5199\u8bc4\u4ef7\uff1a\u8fd9\u4e2a\u624b\u673a\u652f\u67b6\u5f88\u597d\u7528\uff0c\u5438\u9644\u7262\u56fa\uff0c\u8bbe\u8ba1\u7f8e\u89c2\uff0c\u975e\u5e38\u6ee1\u610f\uff01",
            step_count=3,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
            ],
            decision={"action": "CLICK", "point": [505, 600]},
            expected_action="CLICK",
            expected_kind="review_form_top_submit",
            expected_reason="verify_douyin_form_top_step",
        ),
        Scenario(
            name="official_douyin_step3_top_right_click_to_top_submit",
            instruction="\u7ed9\u624b\u673a\u652f\u67b6\u5199\u8bc4\u4ef7\uff1a\u8fd9\u4e2a\u624b\u673a\u652f\u67b6\u5f88\u597d\u7528\uff0c\u5438\u9644\u7262\u56fa\uff0c\u8bbe\u8ba1\u7f8e\u89c2\uff0c\u975e\u5e38\u6ee1\u610f\uff01",
            step_count=3,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
            ],
            decision={"action": "CLICK", "point": [885, 125]},
            expected_action="CLICK",
            expected_kind="review_form_top_submit",
            expected_reason="verify_douyin_form_top_step",
        ),
        Scenario(
            name="official_jingdong_step2_right_lower_click_to_mid_form",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=2,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [842, 836]}},
            ],
            decision={"action": "CLICK", "point": [760, 745]},
            expected_action="CLICK",
            expected_point=[500, 695],
            expected_reason="verify_jingdong_review_step2_mid_form",
        ),
        Scenario(
            name="pre_type_review_form_bottom_area_to_textbox",
            instruction="去抖音给商品写评价：这个东西很好用，值得推荐！",
            step_count=4,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [695, 145]}},
            ],
            decision={"action": "CLICK", "point": [420, 860]},
            expected_action="CLICK",
            expected_kind="review_text_area",
            expected_reason="verify_review_form_text_entry",
        ),
        Scenario(
            name="official_douyin_text_area_focused_click_to_type",
            instruction="给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=5,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [695, 145]}},
                {"step": 4, "action": "CLICK", "parameters": {"point": [505, 600]}},
            ],
            decision={"action": "CLICK", "point": [505, 600]},
            expected_action="TYPE",
            expected_text="这个手机支架很好用，吸附牢固，设计美观，非常满意",
            expected_reason="verify_review_form_ready_to_type",
        ),
        Scenario(
            name="official_jingdong_mid_form_bottom_to_textbox",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=3,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [842, 836]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 695]}},
            ],
            decision={"action": "CLICK", "point": [420, 860]},
            expected_action="CLICK",
            expected_kind="review_text_area",
            expected_reason="verify_review_form_text_entry",
        ),
        Scenario(
            name="official_jingdong_mid_form_generic_to_textbox",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=3,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [842, 836]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 695]}},
            ],
            decision={"action": "CLICK", "point": [505, 600]},
            expected_action="CLICK",
            expected_kind="review_text_area",
            expected_reason="verify_review_form_text_entry",
        ),
        Scenario(
            name="search_after_type_complete_to_submit",
            instruction="在腾讯视频搜索扫毒风暴",
            step_count=5,
            prior_actions=[{"step": 4, "action": "TYPE", "parameters": {"text": "扫毒风暴"}}],
            typed_texts=["扫毒风暴"],
            pending_after_type="submit_after_type",
            decision={"action": "COMPLETE"},
            expected_action="CLICK",
            expected_kind="search_submit_or_suggestion",
            expected_reason="verify_search_submit_after_type",
        ),
        Scenario(
            name="search_after_type_content_click_to_submit",
            instruction="在哔哩哔哩搜索三体",
            step_count=4,
            prior_actions=[{"step": 3, "action": "TYPE", "parameters": {"text": "三体"}}],
            typed_texts=["三体"],
            pending_after_type="submit_after_type",
            decision={"action": "CLICK", "target_id": 3},
            expected_action="CLICK",
            expected_kind="search_submit_or_suggestion",
            expected_reason="verify_search_submit_after_type",
        ),
        Scenario(
            name="popup_content_click_to_close",
            instruction="打开爱奇艺，跳过广告后搜索狂飙",
            step_count=2,
            prior_actions=[{"step": 1, "action": "OPEN", "parameters": {"app_name": "爱奇艺"}}],
            decision={"action": "CLICK", "target_id": 3},
            expected_action="CLICK",
            expected_kind="popup_close_top_right",
            expected_reason="verify_popup_content_click",
        ),
        Scenario(
            name="premature_complete_before_type_to_type",
            instruction="在喜马拉雅搜索三体并播放",
            step_count=3,
            prior_actions=[{"step": 1, "action": "OPEN", "parameters": {"app_name": "喜马拉雅"}}],
            decision={"action": "COMPLETE"},
            expected_action="TYPE",
            expected_text="三体",
            expected_reason="verify_complete_before_type",
        ),
        Scenario(
            name="safe_media_result_click_unchanged",
            instruction="在腾讯视频搜索扫毒风暴",
            step_count=6,
            prior_actions=[
                {"step": 4, "action": "TYPE", "parameters": {"text": "扫毒风暴"}},
                {"step": 5, "action": "CLICK", "parameters": {"point": [511, 162]}},
            ],
            typed_texts=["扫毒风暴"],
            decision={"action": "CLICK", "target_id": 3},
            expected_action="CLICK",
            expected_kind="first_card",
        ),
        Scenario(
            name="force_complete_unchanged",
            instruction="去芒果TV播放我的下载里的新还珠格格第2集",
            step_count=7,
            prior_actions=[
                {"step": 1, "action": "OPEN", "parameters": {"app_name": "芒果TV"}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [848, 78]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [895, 920]}},
                {"step": 4, "action": "CLICK", "parameters": {"point": [179, 655]}},
                {"step": 5, "action": "CLICK", "parameters": {"point": [479, 107]}},
                {"step": 6, "action": "CLICK", "parameters": {"point": [310, 251]}},
            ],
            decision={"action": "COMPLETE", "force_complete": True},
            expected_action="COMPLETE",
        ),
    ]


def main() -> int:
    for scenario in build_scenarios():
        assert_scenario(scenario)
        print(f"PASS {scenario.name}")
    print("All ActionVerifier checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
