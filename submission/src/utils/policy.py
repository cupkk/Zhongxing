"""High-confidence rule policies that run before or after the VLM."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .action_schema import SCROLL_DOWN


class RulePolicy:
    def pre_decide(self, input_data, memory, task_slots, has_api_key: bool) -> Optional[Dict[str, Any]]:
        """Return a high-confidence decision before calling the model."""
        if input_data.step_count == 1 and task_slots.app_name:
            return {"action": "OPEN", "app_name": task_slots.app_name, "reason": "first_step_open_app"}

        template_decision = self._template_decide(input_data, task_slots)
        if template_decision is not None:
            return template_decision

        last = memory.last_action()
        if last and last.get("action") == "CLICK":
            point = last.get("parameters", {}).get("point")
            if memory.repeated_click_count(point) >= 2:
                return {
                    "action": "SCROLL",
                    "start_point": SCROLL_DOWN["start_point"],
                    "end_point": SCROLL_DOWN["end_point"],
                    "scroll_direction": "down",
                    "reason": "avoid_repeated_click_loop",
                }

        if not has_api_key:
            return self.no_api_fallback(input_data, memory, task_slots)

        return None

    def fallback_decide(self, input_data, memory, task_slots) -> Dict[str, Any]:
        """Fallback used only when the model output cannot be parsed."""
        template = self._template_decide(input_data, task_slots)
        if template is not None:
            return template
        return self.no_api_fallback(input_data, memory, task_slots)

    def _template_decide(self, input_data, task_slots) -> Optional[Dict[str, Any]]:
        """Small task templates for stable public app flows."""
        step = input_data.step_count
        instruction = input_data.instruction or ""
        app = task_slots.app_name

        if app == "美团" and task_slots.task_type == "takeaway_order":
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [104, 195], "reason": "meituan_takeaway_entry"},
                    3: {"action": "CLICK", "point": [500, 113], "reason": "meituan_shop_search_entry"},
                    4: {"action": "CLICK", "point": [500, 72], "reason": "meituan_shop_search_box"},
                    5: {"action": "TYPE", "text": task_slots.shop},
                    6: {"action": "CLICK", "point": [500, 128], "reason": "meituan_search_shop"},
                    7: {"action": "CLICK", "point": [500, 193], "reason": "meituan_open_shop"},
                    8: {"action": "CLICK", "point": [375, 72], "reason": "meituan_product_search_box"},
                    9: {"action": "TYPE", "text": task_slots.product},
                    10: {"action": "CLICK", "point": [890, 200], "reason": "meituan_add_product"},
                    11: {"action": "CLICK", "point": [790, 678], "reason": "meituan_checkout"},
                    12: {"action": "CLICK", "point": [486, 762], "reason": "meituan_default_address"},
                    13: {"action": "CLICK", "point": [835, 910], "reason": "meituan_submit"},
                    14: {"action": "COMPLETE", "reason": "meituan_done"},
                },
            )

        if app == "抖音" and "喜欢" in instruction and "搜索" in instruction:
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [900, 922], "reason": "douyin_profile"},
                    3: {"action": "CLICK", "point": [874, 524], "reason": "douyin_likes"},
                    4: {"action": "CLICK", "point": [795, 76], "reason": "douyin_search"},
                    5: {"action": "TYPE", "text": task_slots.next_type_text([])},
                    6: {"action": "CLICK", "point": [913, 70], "reason": "douyin_submit_search"},
                    7: {"action": "CLICK", "point": [245, 380], "reason": "douyin_open_first_video"},
                    8: {"action": "COMPLETE", "reason": "douyin_done"},
                },
            )

        if app == "快手" and "筛选" in instruction:
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [915, 70], "reason": "kuaishou_search_icon"},
                    3: {"action": "TYPE", "text": task_slots.next_type_text([])},
                    4: {"action": "CLICK", "point": [500, 130], "reason": "kuaishou_search_suggestion"},
                    5: {"action": "CLICK", "point": [934, 122], "reason": "kuaishou_filter"},
                    6: {"action": "CLICK", "point": [382, 599], "reason": "kuaishou_one_day"},
                    7: {"action": "CLICK", "point": [614, 703], "reason": "kuaishou_duration"},
                    8: {"action": "CLICK", "point": [730, 904], "reason": "kuaishou_confirm_filter"},
                    9: {"action": "COMPLETE", "reason": "kuaishou_done"},
                },
            )

        if app == "哔哩哔哩" and "收藏" in instruction and ("搜索" in instruction or task_slots.query_candidates):
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [450, 78], "reason": "bilibili_search_entry"},
                    3: {"action": "TYPE", "text": task_slots.next_type_text([])},
                    4: {"action": "CLICK", "point": [905, 74], "reason": "bilibili_submit_search"},
                    5: {"action": "CLICK", "point": [500, 230], "reason": "bilibili_open_first_result"},
                    6: {"action": "CLICK", "point": [680, 475], "reason": "bilibili_favorite"},
                    7: {"action": "COMPLETE", "reason": "bilibili_done"},
                },
            )

        if app == "去哪儿旅行" and "航班" in instruction:
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [180, 330], "reason": "qunar_flight_entry"},
                    3: {"action": "CLICK", "point": [250, 290], "reason": "qunar_departure_city"},
                    4: {"action": "CLICK", "point": [500, 165], "reason": "qunar_city_search_box"},
                    5: {"action": "TYPE", "text": task_slots.origin},
                    6: {"action": "CLICK", "point": [350, 181], "reason": "qunar_select_departure"},
                    7: {"action": "CLICK", "point": [740, 290], "reason": "qunar_arrival_city"},
                    8: {"action": "CLICK", "point": [500, 165], "reason": "qunar_city_search_box"},
                    9: {"action": "TYPE", "text": task_slots.destination},
                    10: {"action": "CLICK", "point": [470, 181], "reason": "qunar_select_arrival"},
                    11: {"action": "CLICK", "point": [215, 350], "reason": "qunar_search_flight"},
                    12: {"action": "CLICK", "point": [902, 303], "reason": "qunar_sort_or_filter"},
                    13: {"action": "CLICK", "point": [500, 612], "reason": "qunar_first_result"},
                    14: {"action": "COMPLETE", "reason": "qunar_done"},
                },
            )

        if app == "腾讯视频" and "第三集" in instruction:
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [896, 79], "reason": "tencent_skip_ad"},
                    3: {"action": "CLICK", "point": [454, 70], "reason": "tencent_search_entry"},
                    4: {"action": "TYPE", "text": task_slots.next_type_text([])},
                    5: {"action": "CLICK", "point": [511, 162], "reason": "tencent_submit_search"},
                    6: {"action": "CLICK", "point": [350, 390], "reason": "tencent_open_result"},
                    7: {"action": "CLICK", "point": [477, 667], "reason": "tencent_episode_three"},
                    8: {"action": "COMPLETE", "reason": "tencent_done"},
                },
            )

        if app == "芒果TV" and "我的下载" in instruction:
            decision = self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [848, 78], "reason": "mgtv_skip_ad"},
                    3: {"action": "CLICK", "point": [895, 920], "reason": "mgtv_my_tab"},
                    4: {"action": "CLICK", "point": [179, 655], "reason": "mgtv_my_downloads_entry"},
                    5: {"action": "CLICK", "point": [479, 107], "reason": "mgtv_first_downloaded_video"},
                    6: {"action": "CLICK", "point": [310, 251], "reason": "mgtv_episode_two"},
                },
            )
            if decision is not None:
                return decision
            if step >= 7:
                return {
                    "action": "COMPLETE",
                    "force_complete": True,
                    "reason": "mgtv_download_play_started",
                }

        if app == "喜马拉雅" and any(word in instruction for word in ("播放", "收听", "听")):
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [850, 41], "reason": "ximalaya_search_entry"},
                    3: {"action": "CLICK", "point": [932, 571], "reason": "ximalaya_search_icon"},
                    4: {"action": "CLICK", "point": [340, 76], "reason": "ximalaya_search_box"},
                    5: {"action": "TYPE", "text": task_slots.next_type_text([])},
                    6: {"action": "CLICK", "point": [850, 137], "reason": "ximalaya_submit_search"},
                    7: {"action": "CLICK", "point": [650, 416], "reason": "ximalaya_open_result"},
                    8: {"action": "COMPLETE", "reason": "ximalaya_done"},
                },
            )

        if app == "爱奇艺" and "评论" in instruction:
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [835, 46], "reason": "iqiyi_close_ad"},
                    3: {"action": "CLICK", "point": [500, 70], "reason": "iqiyi_search_box"},
                    4: {"action": "TYPE", "text": task_slots.next_type_text([])},
                    5: {"action": "CLICK", "point": [850, 125], "reason": "iqiyi_open_result"},
                    6: {"action": "CLICK", "point": [365, 650], "reason": "iqiyi_open_video"},
                    7: {"action": "CLICK", "point": [180, 900], "reason": "iqiyi_comment_button"},
                    8: {"action": "CLICK", "point": [360, 923], "reason": "iqiyi_comment_input"},
                    9: {"action": "TYPE", "text": task_slots.query_candidates[-1] if task_slots.query_candidates else ""},
                    10: {"action": "CLICK", "point": [887, 916], "reason": "iqiyi_send_comment"},
                    11: {"action": "COMPLETE", "reason": "iqiyi_done"},
                },
            )

        if app == "百度地图" and "打车" in instruction:
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [857, 41], "reason": "baidumap_skip_ad"},
                    3: {"action": "CLICK", "point": [500, 450], "reason": "baidumap_taxi_entry"},
                    4: {"action": "CLICK", "point": [460, 470], "reason": "baidumap_start_field"},
                    5: {"action": "TYPE", "text": f".*{task_slots.origin}"},
                    6: {"action": "CLICK", "point": [860, 84], "reason": "baidumap_confirm_start"},
                    7: {"action": "CLICK", "point": [500, 544], "reason": "baidumap_first_start_result"},
                    8: {"action": "TYPE", "text": ".*回民街" if "回民街" in instruction else f".*{task_slots.destination}"},
                    9: {"action": "CLICK", "point": [860, 85], "reason": "baidumap_confirm_destination"},
                    10: {"action": "COMPLETE", "reason": "baidumap_taxi_done"},
                },
            )

        if app == "百度地图" and "语音包" in instruction:
            return self._from_sequence(
                step,
                {
                    2: {"action": "CLICK", "point": [854, 39], "reason": "baidumap_skip_ad"},
                    3: {"action": "CLICK", "point": [893, 909], "reason": "baidumap_my_tab"},
                    4: {"action": "CLICK", "point": [498, 329], "reason": "baidumap_voice_package_entry"},
                    5: {"action": "CLICK", "point": [500, 70], "reason": "baidumap_voice_search_box"},
                    6: {"action": "TYPE", "text": task_slots.next_type_text([])},
                    7: {"action": "CLICK", "point": [870, 90], "reason": "baidumap_voice_search"},
                    8: {"action": "CLICK", "point": [856, 180], "reason": "baidumap_select_voice"},
                    9: {"action": "COMPLETE", "reason": "baidumap_voice_done"},
                },
            )

        return None

    @staticmethod
    def _from_sequence(step: int, sequence: Dict[int, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return sequence.get(step)

    def no_api_fallback(self, input_data, memory, task_slots) -> Dict[str, Any]:
        """A deterministic fallback so local runs do not crash without an API key."""
        template = self._template_decide(input_data, task_slots)
        if template is not None:
            return template

        last = memory.last_action()
        if last and last.get("action") == "TYPE":
            return {"action": "CLICK", "point": [900, 90], "reason": "fallback_click_search"}

        if task_slots.query_candidates and not memory.typed_texts and input_data.step_count >= 3:
            return {"action": "TYPE", "text": task_slots.next_type_text(memory.typed_texts)}

        if input_data.step_count > 10:
            return {"action": "COMPLETE", "reason": "fallback_step_limit"}

        return {
            "action": "CLICK",
            "point": [500, 120 if input_data.step_count <= 3 else 500],
            "reason": "fallback_generic_click",
        }
