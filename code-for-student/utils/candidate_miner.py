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
            UIElement(11, "right_middle_review_entry", (780, 460, 950, 640), hint="right-side review/order entry"),
            UIElement(12, "lower_middle_review_entry", (450, 620, 760, 770), hint="lower-middle product review entry"),
            UIElement(13, "popup_close_top_right", (820, 35, 980, 170), hint="close, skip, or dismiss popup at top-right"),
            UIElement(14, "popup_cancel_bottom", (80, 650, 420, 840), hint="cancel or later button in a popup"),
            UIElement(15, "popup_allow_bottom", (580, 650, 940, 840), hint="allow, agree, continue, or confirm button in a popup"),
            UIElement(16, "bottom_tab_1", (0, 860, 200, 990), hint="bottom navigation tab 1"),
            UIElement(17, "bottom_tab_2", (200, 860, 400, 990), hint="bottom navigation tab 2"),
            UIElement(18, "bottom_tab_3", (400, 860, 600, 990), hint="bottom navigation tab 3"),
            UIElement(19, "bottom_tab_4", (600, 860, 800, 990), hint="bottom navigation tab 4"),
            UIElement(20, "bottom_tab_5", (800, 860, 1000, 990), hint="bottom navigation tab 5 or profile tab"),
            UIElement(21, "right_upper_review_entry", (760, 300, 970, 500), hint="upper-right review or order entry"),
            UIElement(22, "center_review_entry", (250, 500, 760, 700), hint="center review, comment, or rate entry"),
            UIElement(23, "lower_right_review_entry", (680, 600, 970, 820), hint="lower-right review or sun-post entry"),
            UIElement(24, "keyboard_search_button", (740, 850, 990, 990), hint="keyboard search, enter, send, or confirm button"),
            UIElement(25, "top_right_text_button", (780, 60, 990, 190), hint="top-right text button such as search, send, done, or publish"),
        ]
        candidates.extend(self._context_candidates(input_data, memory, task_slots))

        if self._early_popup_context(input_data, memory):
            candidates = self._boost(
                candidates,
                {"top_right", "popup_close_top_right", "popup_cancel_bottom", "popup_allow_bottom"},
            )
        if self._review_like_context(input_data, memory):
            if self._initial_review_entry_context(input_data, memory):
                candidates = self._boost(
                    candidates,
                    {
                        "right_middle_review_entry",
                        "lower_middle_review_entry",
                        "right_upper_review_entry",
                        "center_review_entry",
                        "lower_right_review_entry",
                        "bottom_right_review_entry",
                        "middle_button",
                    },
                )
                candidates = self._penalize(
                    candidates,
                    {"bottom_right_send", "bottom_center_submit", "left_top_back", "keyboard_search_button"},
                )
            elif self._review_form_text_entry_context(input_data, memory):
                candidates = self._boost(
                    candidates,
                    {"review_text_area", "review_star_or_score_area", "center_review_entry"},
                )
                candidates = self._penalize(
                    candidates,
                    {"bottom_input", "bottom_right_send", "bottom_center_submit", "keyboard_search_button"},
                )
            else:
                candidates = self._boost(
                    candidates,
                    {
                        "review_form_top_submit",
                        "bottom_right_send",
                        "bottom_center_submit",
                        "bottom_input",
                        "keyboard_search_button",
                        "top_right_text_button",
                    },
                )
        elif self._just_typed_search(memory):
            candidates = self._boost(candidates, {"top_right", "top_right_text_button", "search_submit_or_suggestion", "keyboard_search_button"})
            candidates = self._penalize(candidates, {"bottom_center_submit"})
        elif self._profile_like_context(input_data):
            candidates = self._boost(candidates, {"bottom_right_tab", "bottom_tab_5"})
        return candidates

    def _context_candidates(self, input_data, memory, task_slots) -> List[UIElement]:
        """Add task family candidates without turning public refs into a flat point table."""
        app = getattr(task_slots, "app_name", "") or ""
        task_type = getattr(task_slots, "task_type", "") or ""
        candidates: List[UIElement] = []

        if task_type == "media_search" or app in {"爱奇艺", "哔哩哔哩", "抖音", "快手", "腾讯视频", "喜马拉雅"}:
            candidates.extend(self._media_candidates(app))

        if app == "百度地图" or task_type == "map_search":
            candidates.extend(self._map_candidates())

        if app == "美团" or task_type == "takeaway_order":
            candidates.extend(self._takeaway_candidates())

        if app == "去哪儿旅行" or task_type == "travel":
            candidates.extend(self._travel_candidates())

        if self._review_like_context(input_data, memory):
            candidates.extend(self._review_candidates())

        return candidates

    @staticmethod
    def _media_candidates(app: str) -> List[UIElement]:
        candidates = [
            UIElement(26, "top_header_search_full", (70, 0, 850, 60), hint="full-width top search or header search field", score=0.05),
            UIElement(27, "top_mid_right_action", (730, 50, 860, 110), hint="top middle-right action button", score=0.05),
            UIElement(28, "top_far_right_action", (840, 50, 980, 90), hint="far top-right search, publish, or confirm button", score=0.05),
            UIElement(29, "right_mid_icon", (800, 500, 950, 550), hint="right-middle action icon such as like, comment, or search", score=0.05),
            UIElement(30, "media_result_lower_row", (20, 600, 720, 700), hint="lower media result row or video item", score=0.05),
            UIElement(31, "bottom_left_action", (80, 850, 300, 950), hint="bottom-left comment, tab, or action button", score=0.05),
            UIElement(32, "upper_left_option", (120, 310, 300, 380), hint="upper-left option or comment entry", score=0.05),
            UIElement(33, "media_content_left_panel", (0, 200, 500, 560), hint="left content/video panel or first content card", score=0.05),
            UIElement(34, "media_result_row", (40, 350, 660, 430), hint="media search result row", score=0.05),
            UIElement(35, "episode_card_mid", (380, 620, 570, 720), hint="middle episode card or playlist item", score=0.05),
            UIElement(36, "right_filter_chip", (900, 100, 970, 145), hint="right filter chip or search option", score=0.05),
            UIElement(37, "mid_filter_option_left", (250, 560, 520, 640), hint="middle-left filter option", score=0.05),
            UIElement(38, "top_right_wide_header", (740, 10, 970, 70), hint="wide top-right header action", score=0.05),
            UIElement(39, "right_middle_search_icon", (890, 550, 970, 595), hint="right-middle search icon or play action", score=0.05),
            UIElement(65, "media_right_mid_action", (620, 430, 740, 520), hint="media right-side favorite, like, or more action", score=0.08),
        ]
        if app == "爱奇艺":
            candidates.append(UIElement(40, "iqiyi_video_result_row", (20, 610, 720, 700), hint="iQIYI video result row", score=0.1))
        if app == "抖音":
            candidates.append(UIElement(41, "douyin_profile_content_panel", (0, 200, 500, 560), hint="Douyin profile content card", score=0.1))
        return candidates

    @staticmethod
    def _map_candidates() -> List[UIElement]:
        return [
            UIElement(42, "map_center_entry", (420, 400, 580, 500), hint="map center taxi, route, or service entry", score=0.1),
            UIElement(43, "map_form_row_mid", (90, 430, 850, 510), hint="map form row such as start or destination field", score=0.1),
            UIElement(44, "address_result_full_row_1", (20, 300, 980, 390), hint="first full-width address result row", score=0.1),
            UIElement(45, "address_result_full_row_2", (20, 150, 980, 230), hint="second or compact address result row", score=0.08),
            UIElement(46, "map_header_right_action", (800, 70, 950, 110), hint="map top-right search or confirm action", score=0.1),
            UIElement(47, "map_right_result_action", (760, 150, 960, 210), hint="right-side map result action", score=0.1),
            UIElement(48, "map_voice_entry_small", (180, 160, 450, 230), hint="small navigation voice package or settings entry", score=0.08),
        ]

    @staticmethod
    def _takeaway_candidates() -> List[UIElement]:
        return [
            UIElement(49, "service_grid_left_top", (30, 140, 180, 250), hint="left-top service grid entry such as takeaway", score=0.1),
            UIElement(50, "top_search_row", (90, 80, 840, 145), hint="top search row or shop search field", score=0.1),
            UIElement(51, "full_result_row_top", (20, 140, 990, 245), hint="top full-width shop or product result row", score=0.1),
            UIElement(52, "top_left_center_action", (320, 50, 430, 95), hint="top centered-left product search action", score=0.08),
            UIElement(53, "right_add_button", (790, 170, 980, 230), hint="right-side add or plus button", score=0.1),
            UIElement(54, "checkout_button", (640, 650, 930, 710), hint="checkout or settlement button", score=0.1),
            UIElement(55, "address_choice_row", (400, 720, 570, 810), hint="address choice or confirm row", score=0.08),
        ]

    @staticmethod
    def _travel_candidates() -> List[UIElement]:
        return [
            UIElement(56, "travel_flight_entry_tile", (20, 280, 340, 380), hint="flight or travel service entry tile", score=0.1),
            UIElement(57, "travel_city_field_left", (40, 260, 460, 320), hint="left departure city field", score=0.1),
            UIElement(58, "travel_city_search_box", (100, 130, 950, 200), hint="city search box", score=0.1),
            UIElement(59, "travel_city_select_left", (100, 155, 600, 205), hint="left city search result", score=0.1),
            UIElement(60, "travel_city_field_right", (540, 260, 940, 320), hint="right arrival city field", score=0.1),
            UIElement(61, "travel_search_button_left", (50, 320, 370, 380), hint="travel search button or main flight query", score=0.1),
            UIElement(62, "travel_sort_filter_right", (840, 270, 960, 340), hint="right sort, filter, or low-price action", score=0.1),
        ]

    @staticmethod
    def _review_candidates() -> List[UIElement]:
        return [
            UIElement(63, "review_entry_list_row", (20, 600, 760, 720), hint="review entry list row", score=0.08),
            UIElement(64, "review_star_or_score_area", (250, 360, 760, 520), hint="review star or score selection area", score=0.08),
            UIElement(66, "bottom_right_review_entry", (760, 782, 924, 890), hint="bottom-right ecommerce review entry", score=0.08),
            UIElement(67, "review_text_area", (300, 300, 540, 430), hint="large review text input area", score=0.08),
            UIElement(68, "review_form_top_submit", (650, 105, 740, 185), hint="top form publish or submit action", score=0.08),
        ]

    @staticmethod
    def _review_like_context(input_data, memory) -> bool:
        instruction = input_data.instruction or ""
        if any(word in instruction for word in ("评价", "评论", "晒单", "发表", "发布", "发送", "提交")):
            return True
        return getattr(memory, "pending_after_type", "") == "review_finish"

    @staticmethod
    def _initial_review_entry_context(input_data, memory) -> bool:
        if input_data.step_count != 1:
            return False
        actions = getattr(memory, "actions", [])
        return not actions and CandidateMiner._review_like_context(input_data, memory)

    @staticmethod
    def _review_form_text_entry_context(input_data, memory) -> bool:
        if getattr(memory, "typed_texts", []):
            return False
        if not CandidateMiner._review_like_context(input_data, memory):
            return False
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
        has_text_area_click = any(
            len(point) == 2 and 300 <= point[0] <= 650 and 300 <= point[1] <= 460
            for point in clicks[1:]
        )
        return has_review_entry and has_score_or_option and not has_text_area_click

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
        if app == "芒果TV" and "下载" in instruction and CandidateMiner._last_click_is_mango_downloads_entry(memory):
            return (20, 64, 939, 150)
        return (80, 160, 920, 340)

    @staticmethod
    def _first_card_hint(input_data, memory, task_slots):
        app = getattr(task_slots, "app_name", "") or ""
        instruction = input_data.instruction or ""
        if app == "百度地图" and "导航语音包" in instruction and CandidateMiner._last_click_is_bottom_right_tab(memory):
            return "navigation voice package entry"
        if app == "芒果TV" and "下载" in instruction and CandidateMiner._last_click_is_mango_downloads_entry(memory):
            return "first downloaded video item"
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
    def _early_popup_context(input_data, memory) -> bool:
        instruction = input_data.instruction or ""
        if input_data.step_count <= 2:
            return True
        if any(word in instruction for word in ("弹窗", "广告", "跳过", "关闭", "权限", "允许", "取消", "升级", "青少年")):
            return True
        last = memory.last_action() if hasattr(memory, "last_action") else None
        return bool(last and last.get("action") == "OPEN" and input_data.step_count <= 3)

    @staticmethod
    def _last_click_is_bottom_right_tab(memory) -> bool:
        last = memory.last_action() if hasattr(memory, "last_action") else None
        if not last or last.get("action") != "CLICK":
            return False
        point = last.get("parameters", {}).get("point", [])
        return len(point) == 2 and point[0] >= 800 and point[1] >= 850

    @staticmethod
    def _last_click_is_mango_downloads_entry(memory) -> bool:
        last = memory.last_action() if hasattr(memory, "last_action") else None
        if not last or last.get("action") != "CLICK":
            return False
        point = last.get("parameters", {}).get("point", [])
        return len(point) == 2 and 102 <= point[0] <= 256 and 627 <= point[1] <= 683

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
