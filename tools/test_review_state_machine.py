"""Focused checks for review/comment finish safeguards.

This script is intentionally dependency-light and can run without a VLM key.
It validates the high-risk review/sun-post paths that have repeatedly affected
hidden leaderboard results.
"""

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
from utils.candidate_miner import CandidateMiner  # noqa: E402
from utils.memory import AgentMemory  # noqa: E402
from utils.task_parser import parse_task  # noqa: E402
from utils.ui_elements import UIElement  # noqa: E402
from utils.validator import ActionValidator  # noqa: E402


@dataclass
class Scenario:
    name: str
    instruction: str
    step_count: int
    prior_actions: List[Dict[str, Any]] = field(default_factory=list)
    typed_texts: List[str] = field(default_factory=list)
    pending_after_type: str | None = None
    decision: Dict[str, Any] = field(default_factory=dict)
    expected_action: str = ""
    expected_point: List[int] | None = None
    expected_stage: str | None = None


def make_input(instruction: str, step_count: int) -> AgentInput:
    return AgentInput(
        instruction=instruction,
        current_image=Image.new("RGB", (480, 1056), "white"),
        step_count=step_count,
        history_messages=[],
        history_actions=[],
    )


def make_memory(scenario: Scenario, input_data: AgentInput) -> AgentMemory:
    memory = AgentMemory()
    memory.actions = list(scenario.prior_actions)
    memory.typed_texts = list(scenario.typed_texts)
    memory.pending_after_type = scenario.pending_after_type
    memory.stage = scenario.pending_after_type or "unknown"
    task_slots = parse_task(scenario.instruction)
    memory.task_slots = task_slots
    memory.last_candidates = CandidateMiner().build(input_data, memory, task_slots)
    # Make the expected legacy review/send points explicit for state-machine checks.
    memory.last_candidates.extend(
        [
            UIElement(101, "bottom_right_send", (794, 852, 980, 980), hint="test bottom-right send"),
            UIElement(102, "bottom_center_submit", (300, 886, 700, 990), hint="test bottom-center submit"),
            UIElement(103, "review_form_top_submit", (650, 105, 740, 185), hint="test top form submit"),
        ]
    )
    return memory


def run_scenario(scenario: Scenario) -> None:
    input_data = make_input(scenario.instruction, scenario.step_count)
    task_slots = parse_task(scenario.instruction)
    memory = make_memory(scenario, input_data)
    output = ActionValidator().validate(scenario.decision, input_data, memory, task_slots)

    assert output.action == scenario.expected_action, (
        f"{scenario.name}: expected action {scenario.expected_action}, got {output.action} {output.parameters}"
    )
    if scenario.expected_point is not None:
        assert output.parameters.get("point") == scenario.expected_point, (
            f"{scenario.name}: expected point {scenario.expected_point}, got {output.parameters}"
        )
    if scenario.expected_stage is not None:
        memory.update(output, input_data)
        assert memory.review_stage == scenario.expected_stage, (
            f"{scenario.name}: expected review_stage {scenario.expected_stage}, got {memory.review_stage}"
        )


def build_scenarios() -> List[Scenario]:
    review_text = "这个手机支架很好用，吸附牢固，设计美观，非常满意！"
    return [
        Scenario(
            name="initial_review_bottom_send_misclick",
            instruction="去抖音给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=1,
            decision={"action": "CLICK", "point": [887, 916]},
            expected_action="CLICK",
            expected_point=[605, 695],
        ),
        Scenario(
            name="initial_review_top_left_back_misclick",
            instruction="去拼多多给订单晒单并评价：这个充电宝很好用，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [70, 85]},
            expected_action="CLICK",
            expected_point=[865, 550],
        ),
        Scenario(
            name="initial_jingdong_center_default_misclick",
            instruction="去京东评价充电宝：这个充电宝很好用，容量大，充电速度快，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [500, 500]},
            expected_action="CLICK",
            expected_point=[842, 836],
        ),
        Scenario(
            name="official_lp_douyin_right_default_misclick",
            instruction="给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=1,
            decision={"action": "CLICK", "point": [865, 550]},
            expected_action="CLICK",
            expected_point=[605, 695],
        ),
        Scenario(
            name="official_lp_jingdong_right_default_misclick",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [865, 550]},
            expected_action="CLICK",
            expected_point=[842, 836],
        ),
        Scenario(
            name="official_lp_jingdong_lower_default_misclick",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=1,
            decision={"action": "CLICK", "point": [605, 695]},
            expected_action="CLICK",
            expected_point=[842, 836],
        ),
        Scenario(
            name="official_lp_pinduoduo_right_entry_kept",
            instruction="评价这款纸巾：这款纸巾质量很好，吸水性强，柔软亲肤，价格实惠，非常满意！",
            step_count=1,
            decision={"action": "CLICK", "point": [865, 550]},
            expected_action="CLICK",
            expected_point=[865, 550],
        ),
        Scenario(
            name="official_douyin_text_focus_next_action_types",
            instruction="给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=5,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [695, 145]}},
                {"step": 4, "action": "CLICK", "parameters": {"point": [505, 600]}},
            ],
            decision={"action": "TYPE", "text": "这个手机支架很好用，吸附牢固，设计美观，非常满意！"},
            expected_action="TYPE",
        ),
        Scenario(
            name="official_douyin_step3_top_right_click_to_top_submit",
            instruction="给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=3,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
            ],
            decision={"action": "CLICK", "point": [695, 145]},
            expected_action="CLICK",
            expected_point=[695, 145],
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
        ),
        Scenario(
            name="official_jingdong_mid_form_bottom_click_to_text_area",
            instruction="评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            step_count=3,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [842, 836]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 695]}},
            ],
            decision={"action": "CLICK", "point": [420, 860]},
            expected_action="CLICK",
            expected_point=[420, 365],
        ),
        Scenario(
            name="official_douyin_lp_after_type_completes",
            instruction="去抖音给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=6,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [700, 145]}},
                {"step": 4, "action": "CLICK", "parameters": {"point": [400, 370]}},
                {"step": 5, "action": "TYPE", "parameters": {"text": review_text}},
            ],
            typed_texts=[review_text],
            pending_after_type="review_finish",
            decision={"action": "COMPLETE"},
            expected_action="CLICK",
            expected_point=[500, 760],
            expected_stage="review_finish_ready",
        ),
        Scenario(
            name="social_comment_after_type_sends_bottom_right",
            instruction="去爱奇艺打开狂飙的评论区，发布评论：真是太好看了",
            step_count=10,
            prior_actions=[
                {"step": 1, "action": "OPEN", "parameters": {"app_name": "爱奇艺"}},
                {"step": 8, "action": "CLICK", "parameters": {"point": [360, 923]}},
                {"step": 9, "action": "TYPE", "parameters": {"text": "真是太好看了"}},
            ],
            typed_texts=["真是太好看了"],
            pending_after_type="review_finish",
            decision={"action": "COMPLETE"},
            expected_action="CLICK",
            expected_point=[887, 916],
        ),
        Scenario(
            name="official_douyin_after_type_top_raw_point_completes",
            instruction="去抖音给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            step_count=6,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [605, 695]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 520]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [695, 145]}},
                {"step": 4, "action": "CLICK", "parameters": {"point": [420, 365]}},
                {"step": 5, "action": "TYPE", "parameters": {"text": review_text}},
            ],
            typed_texts=[review_text],
            pending_after_type="review_finish",
            decision={"action": "CLICK", "point": [705, 145]},
            expected_action="CLICK",
            expected_point=[500, 760],
        ),
        Scenario(
            name="ecommerce_review_after_type_completes",
            instruction="去京东评价充电宝：这个充电宝很好用，容量大，充电速度快，值得推荐！",
            step_count=5,
            prior_actions=[
                {"step": 1, "action": "OPEN", "parameters": {"app_name": "京东"}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [842, 836]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [500, 694]}},
                {"step": 4, "action": "TYPE", "parameters": {"text": "这个充电宝很好用，容量大，充电速度快，值得推荐！"}},
            ],
            typed_texts=["这个充电宝很好用，容量大，充电速度快，值得推荐！"],
            pending_after_type="review_finish",
            decision={"action": "COMPLETE"},
            expected_action="COMPLETE",
        ),
        Scenario(
            name="pinduoduo_review_after_type_still_completes",
            instruction="去拼多多评价纸巾：这款纸巾质量很好，吸水性强，柔软亲肤，价格实惠，非常满意！",
            step_count=6,
            prior_actions=[
                {"step": 1, "action": "CLICK", "parameters": {"point": [865, 550]}},
                {"step": 2, "action": "CLICK", "parameters": {"point": [500, 688]}},
                {"step": 3, "action": "CLICK", "parameters": {"point": [725, 305]}},
                {"step": 4, "action": "CLICK", "parameters": {"point": [420, 365]}},
                {"step": 5, "action": "TYPE", "parameters": {"text": "这款纸巾质量很好，吸水性强，柔软亲肤，价格实惠，非常满意！"}},
            ],
            typed_texts=["这款纸巾质量很好，吸水性强，柔软亲肤，价格实惠，非常满意！"],
            pending_after_type="review_finish",
            decision={"action": "CLICK", "point": [695, 145]},
            expected_action="COMPLETE",
        ),
    ]


def main() -> int:
    for scenario in build_scenarios():
        run_scenario(scenario)
        print(f"PASS {scenario.name}")
    print("All review state-machine checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
