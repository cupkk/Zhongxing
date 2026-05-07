"""Pseudo-hidden mechanism tests for GUI Agent safeguards.

These checks do not replace the official runner. They stress failure modes that
hidden cases have exposed: review entry misclicks, TYPE-after-review finish,
search submit, popup recovery, target_id grounding, candidate ordering, and
ActionVerifier boundaries.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List

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
from utils.validator import ActionValidator  # noqa: E402


@dataclass
class CheckCase:
    name: str
    instruction: str
    step_count: int
    prior_actions: List[Dict[str, Any]] = field(default_factory=list)
    typed_texts: List[str] = field(default_factory=list)
    pending_after_type: str | None = None
    decision: Dict[str, Any] = field(default_factory=dict)
    predicate: Callable[[Any, AgentMemory], bool] | None = None
    use_verifier: bool = False
    expected_verified_action: str = ""
    expected_verified_kind: str = ""
    expected_verified_point: List[int] | None = None
    expected_verified_text: str = ""
    expected_verified_reason: str = ""


def make_context(case: CheckCase) -> tuple[AgentInput, AgentMemory, Any]:
    input_data = AgentInput(
        instruction=case.instruction,
        current_image=Image.new("RGB", (480, 1056), "white"),
        step_count=case.step_count,
    )
    task_slots = parse_task(case.instruction)
    memory = AgentMemory()
    memory.actions = list(case.prior_actions)
    memory.typed_texts = list(case.typed_texts)
    memory.pending_after_type = case.pending_after_type
    memory.stage = case.pending_after_type or "unknown"
    memory.task_slots = task_slots
    memory.last_candidates = CandidateMiner().build(input_data, memory, task_slots)
    return input_data, memory, task_slots


def expect_action(action: str) -> Callable[[Any, AgentMemory], bool]:
    return lambda output, _memory: output.action == action


def expect_point(point: List[int]) -> Callable[[Any, AgentMemory], bool]:
    return lambda output, _memory: output.action == "CLICK" and output.parameters.get("point") == point


def expect_target_kind(kind: str) -> Callable[[Any, AgentMemory], bool]:
    return lambda output, memory: (
        output.action == "CLICK"
        and find_by_kind(memory.last_candidates, kind) is not None
        and output.parameters.get("point") == find_by_kind(memory.last_candidates, kind).center
    )


def candidate_exists(kind: str) -> Callable[[Any, AgentMemory], bool]:
    return lambda _output, memory: find_by_kind(memory.last_candidates, kind) is not None


def combined(*predicates: Callable[[Any, AgentMemory], bool]) -> Callable[[Any, AgentMemory], bool]:
    return lambda output, memory: all(predicate(output, memory) for predicate in predicates)


def make_type_action(step: int, text: str) -> Dict[str, Any]:
    return {"step": step, "action": "TYPE", "parameters": {"text": text}}


def make_click_action(step: int, point: List[int]) -> Dict[str, Any]:
    return {"step": step, "action": "CLICK", "parameters": {"point": point}}


def build_review_finish_cases() -> List[CheckCase]:
    review_texts = [
        "这个东西很好用，质量不错，使用方便，值得推荐！",
        "真是太好看了",
        "容量大，充电速度快，外出携带很方便，值得推荐！",
        "设计美观，吸附牢固，非常满意！",
    ]
    cases: List[CheckCase] = [
        CheckCase(
            "review_initial_bottom_send_douyin",
            "去抖音给商品写评价：这个东西很好用，质量不错，使用方便，值得推荐！",
            1,
            decision={"action": "CLICK", "point": [887, 916]},
            predicate=expect_point([605, 695]),
        ),
        CheckCase(
            "review_initial_top_left_pdd",
            "去拼多多晒单评价：这个东西很好用，质量不错，使用方便，值得推荐！",
            1,
            decision={"action": "CLICK", "point": [70, 85]},
            predicate=expect_point([865, 550]),
        ),
        CheckCase(
            "review_initial_center_jingdong",
            "去京东评价充电宝：这个充电宝很好用，容量大，充电速度快，值得推荐！",
            1,
            decision={"action": "CLICK", "point": [500, 500]},
            predicate=expect_point([842, 836]),
        ),
        CheckCase(
            "official_lp_douyin_right_default_redirect",
            "给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            1,
            decision={"action": "CLICK", "point": [865, 550]},
            predicate=expect_point([605, 695]),
        ),
        CheckCase(
            "official_lp_jingdong_right_default_redirect",
            "评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            1,
            decision={"action": "CLICK", "point": [865, 550]},
            predicate=expect_point([842, 836]),
        ),
        CheckCase(
            "official_lp_jingdong_lower_default_redirect",
            "评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            1,
            decision={"action": "CLICK", "point": [605, 695]},
            predicate=expect_point([842, 836]),
        ),
        CheckCase(
            "official_lp_pinduoduo_right_default_keep",
            "评价这款纸巾：这款纸巾质量很好，吸水性强，柔软亲肤，价格实惠，非常满意！",
            1,
            decision={"action": "CLICK", "point": [865, 550]},
            predicate=expect_point([865, 550]),
        ),
        CheckCase(
            "review_initial_scroll_guard",
            "去淘宝写一段商品评价：这个东西很好用，质量不错，使用方便，值得推荐！",
            1,
            decision={"action": "SCROLL", "scroll_direction": "down"},
            predicate=expect_point([865, 551]),
        ),
        CheckCase(
            "target_id_review_form_top_submit",
            "去抖音给商品写评价：这个东西很好用，质量不错，使用方便，值得推荐！",
            5,
            decision={"action": "CLICK", "target_id": 68},
            predicate=expect_point([695, 145]),
        ),
    ]

    social_apps = ["快手", "爱奇艺", "哔哩哔哩", "腾讯视频", "抖音"]
    for index, app in enumerate(social_apps, start=1):
        text = review_texts[index % len(review_texts)]
        cases.append(
            CheckCase(
                f"social_comment_complete_to_send_{index}_{app}",
                f"去{app}视频下面发布评论：{text}",
                6,
                prior_actions=[
                    {"step": 1, "action": "OPEN", "parameters": {"app_name": app}},
                    make_type_action(5, text),
                ],
                typed_texts=[text],
                pending_after_type="review_finish",
                decision={"action": "COMPLETE"},
                predicate=expect_point([887, 916]),
            )
        )
        cases.append(
            CheckCase(
                f"social_comment_scroll_to_send_{index}_{app}",
                f"去{app}视频评论区发送评论：{text}",
                6,
                prior_actions=[
                    {"step": 1, "action": "OPEN", "parameters": {"app_name": app}},
                    make_type_action(5, text),
                ],
                typed_texts=[text],
                pending_after_type="review_finish",
                decision={"action": "SCROLL", "scroll_direction": "down"},
                predicate=expect_point([887, 916]),
            )
        )

    ecommerce_apps = ["京东", "拼多多", "淘宝"]
    for index, app in enumerate(ecommerce_apps, start=1):
        text = review_texts[(index + 1) % len(review_texts)]
        cases.append(
            CheckCase(
                f"ecommerce_review_complete_{index}_{app}",
                f"去{app}评价订单：{text}",
                6,
                prior_actions=[
                    {"step": 1, "action": "OPEN", "parameters": {"app_name": app}},
                    make_type_action(5, text),
                ],
                typed_texts=[text],
                pending_after_type="review_finish",
                decision={"action": "COMPLETE"},
                predicate=expect_action("COMPLETE"),
            )
        )

    douyin_finish_decisions = [
        ("complete", {"action": "COMPLETE"}),
        ("top_raw", {"action": "CLICK", "point": [695, 145]}),
        ("top_submit_raw", {"action": "CLICK", "point": [705, 145]}),
        ("after_type_right_top_raw", {"action": "CLICK", "point": [850, 145]}),
        ("top_right_raw", {"action": "CLICK", "point": [885, 125]}),
        ("bottom_center_raw", {"action": "CLICK", "point": [500, 938]}),
        ("bottom_send", {"action": "CLICK", "point": [887, 916]}),
        ("scroll", {"action": "SCROLL", "scroll_direction": "down"}),
    ]
    douyin_step_variants = [
        ([605, 695], [500, 520], [700, 145], [400, 370]),
        ([605, 695], [500, 520], [695, 145], [420, 365]),
        ([605, 695], [500, 520], [705, 145], [500, 370]),
        ([600, 690], [505, 520], [700, 145], [500, 370]),
    ]
    for variant_index, points in enumerate(douyin_step_variants, start=1):
        first, second, third, fourth = points
        text = review_texts[variant_index % len(review_texts)]
        for decision_name, decision in douyin_finish_decisions:
            cases.append(
                CheckCase(
                    f"douyin_lp_form_after_type_submit_{variant_index}_{decision_name}",
                    "去抖音给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
                    6,
                    prior_actions=[
                        make_click_action(1, first),
                        make_click_action(2, second),
                        make_click_action(3, third),
                        make_click_action(4, fourth),
                        make_type_action(5, text),
                    ],
                    typed_texts=[text],
                    pending_after_type="review_finish",
                    decision=decision,
                    predicate=expect_target_kind("review_form_after_type_submit"),
                )
            )

    explicit_publish_words = ["发布", "发送", "提交", "发表"]
    for index, word in enumerate(explicit_publish_words, start=1):
        text = review_texts[index % len(review_texts)]
        cases.append(
            CheckCase(
                f"douyin_lp_form_explicit_publish_keeps_click_{index}_{word}",
                f"去抖音给手机支架写评价并{word}：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
                6,
                prior_actions=[
                    make_click_action(1, [605, 695]),
                    make_click_action(2, [500, 520]),
                    make_click_action(3, [700, 145]),
                    make_click_action(4, [400, 370]),
                    make_type_action(5, text),
                ],
                typed_texts=[text],
                pending_after_type="review_finish",
                decision={"action": "COMPLETE"},
                predicate=expect_point([695, 145]),
            )
        )

    ecommerce_variants = [
        ("京东", [842, 836], [500, 692], [420, 450]),
        ("拼多多", [865, 550], [500, 690], [420, 365]),
        ("淘宝", [865, 550], [500, 690], [420, 365]),
    ]
    ecommerce_finish_decisions = [
        ("complete", {"action": "COMPLETE"}),
        ("top_click", {"action": "CLICK", "point": [695, 145]}),
        ("bottom_send", {"action": "CLICK", "point": [887, 916]}),
        ("scroll", {"action": "SCROLL", "scroll_direction": "down"}),
    ]
    for app_index, (app, entry, form, text_area) in enumerate(ecommerce_variants, start=1):
        for text_index, text in enumerate(review_texts, start=1):
            for decision_name, decision in ecommerce_finish_decisions:
                cases.append(
                    CheckCase(
                        f"ecommerce_after_type_stays_complete_{app_index}_{text_index}_{decision_name}_{app}",
                        f"去{app}评价订单：{text}",
                        6,
                        prior_actions=[
                            make_click_action(1, entry),
                            make_click_action(2, form),
                            make_click_action(3, text_area),
                            make_type_action(5, text),
                        ],
                        typed_texts=[text],
                        pending_after_type="review_finish",
                        decision=decision,
                        predicate=expect_action("COMPLETE"),
                    )
                )

    comment_decisions = [
        ("complete", {"action": "COMPLETE"}),
        ("scroll", {"action": "SCROLL", "scroll_direction": "down"}),
        ("left_click", {"action": "CLICK", "point": [180, 900]}),
        ("top_click", {"action": "CLICK", "point": [850, 125]}),
    ]
    for app_index, app in enumerate(social_apps, start=1):
        for decision_name, decision in comment_decisions:
            text = review_texts[(app_index + len(decision_name)) % len(review_texts)]
            cases.append(
                CheckCase(
                    f"social_comment_after_type_still_sends_{app_index}_{decision_name}_{app}",
                    f"去{app}视频下面发布评论：{text}",
                    7,
                    prior_actions=[
                        {"step": 1, "action": "OPEN", "parameters": {"app_name": app}},
                        make_click_action(5, [360, 923]),
                        make_type_action(6, text),
                    ],
                    typed_texts=[text],
                    pending_after_type="review_finish",
                    decision=decision,
                    predicate=expect_point([887, 916]),
                )
            )
    return cases


def build_candidate_presence_cases() -> List[CheckCase]:
    cases: List[CheckCase] = []
    search_apps = ["腾讯视频", "哔哩哔哩", "快手", "喜马拉雅", "百度地图", "爱奇艺", "芒果TV"]
    for index, app in enumerate(search_apps, start=1):
        cases.append(
            CheckCase(
                f"search_submit_candidates_{index}_{app}",
                f"在{app}搜索测试关键词",
                4,
                prior_actions=[make_type_action(3, "测试关键词")],
                typed_texts=["测试关键词"],
                pending_after_type="submit_after_type",
                decision={"action": "CLICK", "target_id": 10},
                predicate=combined(candidate_exists("search_submit_or_suggestion"), candidate_exists("keyboard_search_button")),
            )
        )

    popup_instructions = [
        "打开百度地图，关闭广告后搜索路线",
        "打开爱奇艺，跳过广告后搜索电视剧",
        "打开芒果TV，关闭弹窗后进入我的下载",
        "打开腾讯视频，跳过开屏广告后搜索视频",
        "打开美团，取消升级弹窗后点外卖",
        "打开抖音，关闭青少年模式弹窗后搜索视频",
        "打开哔哩哔哩，允许权限后搜索视频",
    ]
    for index, instruction in enumerate(popup_instructions, start=1):
        cases.append(
            CheckCase(
                f"popup_candidates_{index}",
                instruction,
                2,
                prior_actions=[{"step": 1, "action": "OPEN", "parameters": {"app_name": parse_task(instruction).app_name}}],
                decision={"action": "CLICK", "target_id": 13},
                predicate=combined(
                    candidate_exists("popup_close_top_right"),
                    candidate_exists("popup_cancel_bottom"),
                    candidate_exists("popup_allow_bottom"),
                ),
            )
        )

    review_candidate_instructions = [
        "去抖音给商品写评价：这个东西很好用，质量不错，使用方便，值得推荐！",
        "去拼多多晒单评价：这个东西很好用，质量不错，使用方便，值得推荐！",
        "去京东评价订单：这个东西很好用，质量不错，使用方便，值得推荐！",
        "去淘宝写一段商品评价：这个东西很好用，质量不错，使用方便，值得推荐！",
        "去快手发布评论：这个东西很好用，质量不错，使用方便，值得推荐！",
        "去小红书回复评论：这个东西很好用，值得推荐！",
    ]
    for index, instruction in enumerate(review_candidate_instructions, start=1):
        cases.append(
            CheckCase(
                f"initial_review_candidates_{index}",
                instruction,
                1,
                decision={"action": "CLICK", "target_id": 21},
                predicate=combined(
                    candidate_exists("right_middle_review_entry"),
                    candidate_exists("right_upper_review_entry"),
                    candidate_exists("center_review_entry"),
                    candidate_exists("lower_right_review_entry"),
                    candidate_exists("review_entry_list_row"),
                ),
            )
        )

    nav_instructions = [
        "去百度地图更换导航语音包为孟子义",
        "去芒果TV播放我的下载里的电视剧",
        "打开抖音我的喜欢",
        "打开淘宝个人中心查看订单",
        "打开京东我的订单",
        "打开美团我的地址",
    ]
    for index, instruction in enumerate(nav_instructions, start=1):
        cases.append(
            CheckCase(
                f"bottom_nav_candidates_{index}",
                instruction,
                3,
                decision={"action": "CLICK", "target_id": 20},
                predicate=combined(
                    candidate_exists("bottom_tab_1"),
                    candidate_exists("bottom_tab_2"),
                    candidate_exists("bottom_tab_3"),
                    candidate_exists("bottom_tab_4"),
                    candidate_exists("bottom_tab_5"),
                ),
            )
        )

    family_expectations = [
        ("media_family_candidates_tencent", "在腾讯视频搜索扫毒风暴并播放第三集", ["media_result_row", "media_right_mid_action", "episode_card_mid"]),
        ("media_family_candidates_douyin", "打开抖音我的喜欢并搜索李白", ["media_content_left_panel", "right_mid_icon", "top_far_right_action"]),
        ("map_family_candidates_taxi", "去百度地图从钟楼打车到回民街", ["map_form_row_mid", "address_result_full_row_1", "map_header_right_action"]),
        ("map_family_candidates_voice", "去百度地图更换导航语音包为孟子义", ["map_voice_entry_small", "map_right_result_action", "bottom_tab_5"]),
        ("takeaway_family_candidates", "去美团在肯德基店铺购买鸡腿堡", ["service_grid_left_top", "right_add_button", "checkout_button"]),
        ("travel_family_candidates", "去去哪儿旅行查询北京飞上海的航班", ["travel_flight_entry_tile", "travel_city_search_box", "travel_sort_filter_right"]),
    ]
    for name, instruction, kinds in family_expectations:
        cases.append(
            CheckCase(
                name,
                instruction,
                3,
                decision={"action": "CLICK", "target_id": 3},
                predicate=combined(*(candidate_exists(kind) for kind in kinds)),
            )
        )
    return cases


def build_verifier_cases() -> List[CheckCase]:
    cases: List[CheckCase] = []
    review_apps = ["抖音", "拼多多", "京东", "淘宝", "快手", "小红书"]
    forbidden_decisions = [
        ("send_target", {"action": "CLICK", "target_id": 6}, "verify_initial_review_forbidden_target"),
        ("back_point", {"action": "CLICK", "point": [70, 85]}, "verify_initial_review_forbidden_point"),
        ("scroll", {"action": "SCROLL", "scroll_direction": "down"}, "verify_initial_review_action"),
    ]
    for app_index, app in enumerate(review_apps, start=1):
        for variant, decision, reason in forbidden_decisions:
            if app == "抖音":
                expected_kind = "lower_middle_review_entry"
            elif app == "京东":
                expected_kind = "bottom_right_review_entry"
            else:
                expected_kind = "right_middle_review_entry"
            cases.append(
                CheckCase(
                    f"verifier_initial_review_{variant}_{app_index}_{app}",
                    f"去{app}给商品写评价：这个东西很好用，值得推荐！",
                    1,
                    decision=decision,
                    use_verifier=True,
                    expected_verified_action="CLICK",
                    expected_verified_kind=expected_kind,
                    expected_verified_reason=reason,
                    predicate=expect_target_kind(expected_kind),
                )
            )

    cases.append(
        CheckCase(
            "verifier_jingdong_initial_center_to_bottom_entry",
            "去京东评价充电宝：这个充电宝很好用，容量大，充电速度快，值得推荐！",
            1,
            decision={"action": "CLICK", "point": [500, 500]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="bottom_right_review_entry",
            expected_verified_reason="verify_initial_review_center_point",
            predicate=expect_target_kind("bottom_right_review_entry"),
        )
    )

    cases.append(
        CheckCase(
            "verifier_official_lp_douyin_right_default_to_lower_entry",
            "给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            1,
            decision={"action": "CLICK", "point": [865, 550]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="lower_middle_review_entry",
            expected_verified_reason="verify_initial_review_scene_point",
            predicate=expect_target_kind("lower_middle_review_entry"),
        )
    )

    cases.append(
        CheckCase(
            "verifier_official_lp_jingdong_right_default_to_bottom_entry",
            "评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            1,
            decision={"action": "CLICK", "point": [865, 550]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="bottom_right_review_entry",
            expected_verified_reason="verify_initial_review_scene_point",
            predicate=expect_target_kind("bottom_right_review_entry"),
        )
    )

    cases.append(
        CheckCase(
            "verifier_official_douyin_step3_mid_click_to_top_submit",
            "\u7ed9\u624b\u673a\u652f\u67b6\u5199\u8bc4\u4ef7\uff1a\u8fd9\u4e2a\u624b\u673a\u652f\u67b6\u5f88\u597d\u7528\uff0c\u5438\u9644\u7262\u56fa\uff0c\u8bbe\u8ba1\u7f8e\u89c2\uff0c\u975e\u5e38\u6ee1\u610f\uff01",
            3,
            prior_actions=[
                make_click_action(1, [605, 695]),
                make_click_action(2, [500, 520]),
            ],
            decision={"action": "CLICK", "point": [505, 600]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="review_form_top_submit",
            expected_verified_reason="verify_douyin_form_top_step",
            predicate=expect_target_kind("review_form_top_submit"),
        )
    )

    cases.append(
        CheckCase(
            "verifier_official_douyin_step3_top_right_to_top_submit",
            "\u7ed9\u624b\u673a\u652f\u67b6\u5199\u8bc4\u4ef7\uff1a\u8fd9\u4e2a\u624b\u673a\u652f\u67b6\u5f88\u597d\u7528\uff0c\u5438\u9644\u7262\u56fa\uff0c\u8bbe\u8ba1\u7f8e\u89c2\uff0c\u975e\u5e38\u6ee1\u610f\uff01",
            3,
            prior_actions=[
                make_click_action(1, [605, 695]),
                make_click_action(2, [500, 520]),
            ],
            decision={"action": "CLICK", "point": [885, 125]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="review_form_top_submit",
            expected_verified_reason="verify_douyin_form_top_step",
            predicate=expect_target_kind("review_form_top_submit"),
        )
    )

    cases.append(
        CheckCase(
            "verifier_official_jingdong_step2_right_lower_to_mid_form",
            "评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            2,
            prior_actions=[
                make_click_action(1, [842, 836]),
            ],
            decision={"action": "CLICK", "point": [760, 745]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_point=[500, 695],
            expected_verified_reason="verify_jingdong_review_step2_mid_form",
            predicate=expect_point([500, 695]),
        )
    )

    cases.append(
        CheckCase(
            "verifier_douyin_pre_type_bottom_to_text_area",
            "去抖音给商品写评价：这个东西很好用，值得推荐！",
            4,
            prior_actions=[
                make_click_action(1, [605, 695]),
                make_click_action(2, [500, 520]),
                make_click_action(3, [695, 145]),
            ],
            decision={"action": "CLICK", "point": [420, 860]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="review_text_area",
            expected_verified_reason="verify_review_form_text_entry",
            predicate=expect_target_kind("review_text_area"),
        )
    )

    cases.append(
        CheckCase(
            "verifier_official_douyin_focused_text_area_to_type",
            "给手机支架写评价：这个手机支架很好用，吸附牢固，设计美观，非常满意！",
            5,
            prior_actions=[
                make_click_action(1, [605, 695]),
                make_click_action(2, [500, 520]),
                make_click_action(3, [695, 145]),
                make_click_action(4, [505, 600]),
            ],
            decision={"action": "CLICK", "point": [505, 600]},
            use_verifier=True,
            expected_verified_action="TYPE",
            expected_verified_text="这个手机支架很好用，吸附牢固，设计美观，非常满意",
            expected_verified_reason="verify_review_form_ready_to_type",
            predicate=expect_action("TYPE"),
        )
    )

    cases.append(
        CheckCase(
            "verifier_official_jingdong_mid_form_bottom_to_text_area",
            "评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            3,
            prior_actions=[
                make_click_action(1, [842, 836]),
                make_click_action(2, [500, 695]),
            ],
            decision={"action": "CLICK", "point": [420, 860]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="review_text_area",
            expected_verified_reason="verify_review_form_text_entry",
            predicate=expect_target_kind("review_text_area"),
        )
    )
    cases.append(
        CheckCase(
            "verifier_official_jingdong_mid_form_generic_to_text_area",
            "评价这个充电宝：这个充电宝很好用，容量大，充电速度快，外出携带很方便，值得推荐！",
            3,
            prior_actions=[
                make_click_action(1, [842, 836]),
                make_click_action(2, [500, 695]),
            ],
            decision={"action": "CLICK", "point": [505, 600]},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="review_text_area",
            expected_verified_reason="verify_review_form_text_entry",
            predicate=expect_target_kind("review_text_area"),
        )
    )

    search_apps = ["腾讯视频", "哔哩哔哩", "快手", "喜马拉雅", "百度地图", "爱奇艺", "芒果TV"]
    for index, app in enumerate(search_apps, start=1):
        cases.append(
            CheckCase(
                f"verifier_search_complete_to_submit_{index}_{app}",
                f"在{app}搜索测试关键词",
                4,
                prior_actions=[make_type_action(3, "测试关键词")],
                typed_texts=["测试关键词"],
                pending_after_type="submit_after_type",
                decision={"action": "COMPLETE"},
                use_verifier=True,
                expected_verified_action="CLICK",
                expected_verified_kind="search_submit_or_suggestion",
                expected_verified_reason="verify_search_submit_after_type",
                predicate=expect_target_kind("search_submit_or_suggestion"),
            )
        )
        cases.append(
            CheckCase(
                f"verifier_search_content_to_submit_{index}_{app}",
                f"在{app}搜索测试关键词",
                4,
                prior_actions=[make_type_action(3, "测试关键词")],
                typed_texts=["测试关键词"],
                pending_after_type="submit_after_type",
                decision={"action": "CLICK", "target_id": 3},
                use_verifier=True,
                expected_verified_action="CLICK",
                expected_verified_kind="search_submit_or_suggestion",
                expected_verified_reason="verify_search_submit_after_type",
                predicate=expect_target_kind("search_submit_or_suggestion"),
            )
        )

    popup_instructions = [
        "打开爱奇艺，跳过广告后搜索狂飙",
        "打开腾讯视频，关闭弹窗后搜索扫毒风暴",
        "打开美团，取消升级弹窗后点外卖",
        "打开百度地图，允许权限后搜索路线",
        "打开抖音，关闭青少年模式弹窗后搜索李白",
    ]
    for index, instruction in enumerate(popup_instructions, start=1):
        cases.append(
            CheckCase(
                f"verifier_popup_content_to_close_{index}",
                instruction,
                2,
                prior_actions=[{"step": 1, "action": "OPEN", "parameters": {"app_name": parse_task(instruction).app_name}}],
                decision={"action": "CLICK", "target_id": 3},
                use_verifier=True,
                expected_verified_action="CLICK",
                expected_verified_kind="popup_close_top_right",
                expected_verified_reason="verify_popup_content_click",
                predicate=expect_target_kind("popup_close_top_right"),
            )
        )

    premature_tasks = [
        ("喜马拉雅", "三体"),
        ("腾讯视频", "扫毒风暴"),
        ("哔哩哔哩", "黑神话悟空"),
        ("快手", "健身教程"),
        ("百度地图", "回民街"),
    ]
    for index, (app, query) in enumerate(premature_tasks, start=1):
        cases.append(
            CheckCase(
                f"verifier_premature_complete_to_type_{index}_{app}",
                f"在{app}搜索{query}",
                3,
                prior_actions=[{"step": 1, "action": "OPEN", "parameters": {"app_name": app}}],
                decision={"action": "COMPLETE"},
                use_verifier=True,
                expected_verified_action="TYPE",
                expected_verified_text=query,
                expected_verified_reason="verify_complete_before_type",
                predicate=expect_action("TYPE"),
            )
        )

    safe_cases = [
        CheckCase(
            "verifier_safe_media_result_click_unchanged",
            "在腾讯视频搜索扫毒风暴",
            6,
            prior_actions=[make_type_action(4, "扫毒风暴"), make_click_action(5, [511, 162])],
            typed_texts=["扫毒风暴"],
            decision={"action": "CLICK", "target_id": 3},
            use_verifier=True,
            expected_verified_action="CLICK",
            expected_verified_kind="first_card",
            predicate=expect_target_kind("first_card"),
        ),
        CheckCase(
            "verifier_force_complete_unchanged",
            "去芒果TV播放我的下载里的新还珠格格第2集",
            7,
            prior_actions=[
                {"step": 1, "action": "OPEN", "parameters": {"app_name": "芒果TV"}},
                make_click_action(2, [848, 78]),
                make_click_action(3, [895, 920]),
                make_click_action(4, [179, 655]),
                make_click_action(5, [479, 107]),
                make_click_action(6, [310, 251]),
            ],
            decision={"action": "COMPLETE", "force_complete": True},
            use_verifier=True,
            expected_verified_action="COMPLETE",
            predicate=expect_action("COMPLETE"),
        ),
    ]
    cases.extend(safe_cases)
    return cases


def build_cases() -> List[CheckCase]:
    cases: List[CheckCase] = []
    cases.extend(build_review_finish_cases())
    cases.extend(build_candidate_presence_cases())
    cases.extend(build_verifier_cases())
    assert len(cases) >= 150, len(cases)
    return cases


def _assert_verified(case: CheckCase, revised: Dict[str, Any], memory: AgentMemory) -> None:
    if case.expected_verified_action:
        assert revised.get("action") == case.expected_verified_action, f"{case.name}: verified={revised}"
    if case.expected_verified_kind:
        element = find_by_kind(memory.last_candidates, case.expected_verified_kind)
        assert element is not None, f"{case.name}: missing candidate {case.expected_verified_kind}"
        assert revised.get("target_id") == element.element_id, f"{case.name}: verified={revised}, expected={element}"
    if case.expected_verified_point is not None:
        assert revised.get("point") == case.expected_verified_point, f"{case.name}: verified={revised}"
    if case.expected_verified_text:
        assert revised.get("text") == case.expected_verified_text, f"{case.name}: verified={revised}"
    if case.expected_verified_reason:
        assert revised.get("reason") == case.expected_verified_reason, f"{case.name}: verified={revised}"


def run_case(case: CheckCase) -> None:
    input_data, memory, task_slots = make_context(case)
    decision = case.decision
    if case.use_verifier:
        decision = ActionVerifier().verify(case.decision, input_data, memory, task_slots)
        _assert_verified(case, decision, memory)
    output = ActionValidator().validate(decision, input_data, memory, task_slots)
    assert case.predicate is not None
    assert case.predicate(output, memory), (
        f"{case.name}: output={output} decision={decision} candidates={[c.to_dict() for c in memory.last_candidates]}"
    )


def main() -> int:
    cases = build_cases()
    for case in cases:
        run_case(case)
        print(f"PASS {case.name}")
    print(f"All {len(cases)} pseudo-hidden mechanism checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
