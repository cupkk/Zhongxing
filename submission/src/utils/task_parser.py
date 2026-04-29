"""Lightweight task slot extraction from the user instruction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .app_map import detect_app_name


@dataclass
class TaskSlots:
    app_name: str = ""
    task_type: str = "generic"
    shop: str = ""
    product: str = ""
    origin: str = ""
    destination: str = ""
    query_candidates: List[str] = field(default_factory=list)

    def next_type_text(self, used_texts: List[str]) -> str:
        for item in self.query_candidates:
            if item and item not in used_texts:
                return item
        return self.query_candidates[0] if self.query_candidates else ""


def _clean_candidate(value: str) -> str:
    value = (value or "").strip(" ，,。.!！?？；;：:")
    value = re.sub(r"^(搜索|查找|播放|观看|打开|购买|帮我|给我|去)", "", value).strip()
    value = re.split(r"并|然后|接着|再|筛选|过滤|地址选项|地址选择|并且|同时", value)[0].strip()
    value = value.strip("“”\"'《》")
    value = re.sub(r"(的视频|的作品|相关内容|相关视频|这首歌|这本书|的评论区|评论区|打车|导航|路线|附近|地址)$", "", value).strip()
    return value


def _first_match(patterns: List[str], text: str, group: int = 1) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _clean_candidate(match.group(group))
    return ""


def parse_task(instruction: str) -> TaskSlots:
    text = instruction or ""
    app_name = detect_app_name(text) or ""
    slots = TaskSlots(app_name=app_name)

    if app_name == "美团" or "外卖" in text:
        slots.task_type = "takeaway_order"
    elif app_name == "百度地图" or any(word in text for word in ("打车", "导航", "路线")):
        slots.task_type = "map_search"
    elif app_name in {"哔哩哔哩", "抖音", "快手", "爱奇艺", "腾讯视频", "芒果TV", "喜马拉雅"}:
        slots.task_type = "media_search"
    elif app_name == "去哪儿旅行":
        slots.task_type = "travel"

    shop_match = re.search(r"(?:购买|买|下单)(.+?)店铺(?:的|里|中的)(.+?)(?:，|,|。|$)", text)
    if shop_match:
        slots.shop = _clean_candidate(shop_match.group(1))
        slots.product = _clean_candidate(shop_match.group(2))

    if not slots.shop or not slots.product:
        shop_match = re.search(r"(?:在|去)(.+?)店铺(?:购买|买|下单)(.+?)(?:，|,|。|$)", text)
        if shop_match:
            slots.shop = slots.shop or _clean_candidate(shop_match.group(1))
            slots.product = slots.product or _clean_candidate(shop_match.group(2))

    if not slots.shop:
        shop_match = re.search(r"(.+?)店铺", text)
        if shop_match:
            slots.shop = _clean_candidate(shop_match.group(1))

    if not slots.product:
        product_match = re.search(r"店铺的(.+?)(?:，|,|。|$)", text)
        if product_match:
            slots.product = _clean_candidate(product_match.group(1))

    route_match = re.search(r"(?:从|起点(?:设为|设置为|是)?)(.+?)(?:到|去|前往|终点(?:设为|设置为|是)?)(.+?)(?:，|,|。|$)", text)
    if route_match:
        slots.origin = _clean_candidate(route_match.group(1))
        slots.destination = _clean_candidate(route_match.group(2))

    if not slots.origin:
        slots.origin = _first_match(
            [
                r"起点(?:设为|设置为|是|填|输入)?([^，,。]+)",
                r"出发地(?:设为|设置为|是|填|输入)?([^，,。]+)",
            ],
            text,
        )
    if not slots.destination:
        slots.destination = _first_match(
            [
                r"终点(?:设为|设置为|是|填|输入)?([^，,。]+)",
                r"目的地(?:设为|设置为|是|填|输入)?([^，,。]+)",
                r"到达地(?:设为|设置为|是|填|输入)?([^，,。]+)",
            ],
            text,
        )

    flight_match = re.search(r"([^，,。]*?)飞([^，,。]*?)的航班", text)
    if flight_match:
        origin = _clean_candidate(flight_match.group(1))
        destination = _clean_candidate(flight_match.group(2))
        # Remove date words that are usually not typed into city fields.
        origin = re.sub(r".*(?:今天|明天|后天|大后天|上午|下午|晚上|早上|中午)", "", origin)
        slots.origin = origin or slots.origin
        slots.destination = destination or slots.destination

    if not slots.destination and slots.task_type in {"map_search", "travel"}:
        dest_match = re.search(r"(?:去|到|导航到|搜索)([^，,。]+?)(?:附近|路线|导航|$)", text)
        if dest_match:
            slots.destination = _clean_candidate(dest_match.group(1))

    explicit_query = ""
    comment_text = _first_match(
        [
            r"(?:发布|发送|发表|输入|写下|写|评论)(?:一条)?(?:评论|留言)?(?:内容)?(?:为|是|[:：])\s*[“\"']?(.+?)[”\"']?(?:，|,|。|$)",
            r"[“\"'](.+?)[”\"'](?:这条)?(?:评论|留言)",
            r"(?:评论|留言)[“\"'](.+?)[”\"']",
        ],
        text,
    )

    voice_match = re.search(r"语音包为([^，,。]+)", text)
    if voice_match:
        explicit_query = _clean_candidate(voice_match.group(1))

    if not explicit_query:
        review_match = re.search(r"打开(.+?)的评论区", text)
        if review_match:
            explicit_query = _clean_candidate(review_match.group(1))

    if not explicit_query:
        quote_match = re.search(r"《(.+?)》", text)
        if quote_match:
            explicit_query = _clean_candidate(quote_match.group(1))

    if not explicit_query:
        query_match = re.search(r"(?:搜索|查找|搜一下|找一下|播放|观看|收听|听|打开|找到|点播)([^，,。]+)", text)
    else:
        query_match = None
    if query_match:
        explicit_query = _clean_candidate(query_match.group(1))

    if not explicit_query:
        explicit_query = _first_match(
            [
                r"(?:名为|标题为|关键词为|关键字为)([^，,。]+)",
                r"(?:关于|有关)([^，,。]+?)(?:的视频|的内容|的作品|的文章|$)",
            ],
            text,
        )

    if explicit_query and app_name and explicit_query.startswith(app_name + "的"):
        explicit_query = _clean_candidate(explicit_query[len(app_name) + 1 :])

    candidates: List[str] = []
    for candidate in [
        slots.shop,
        slots.product,
        slots.destination,
        slots.origin,
        explicit_query,
        comment_text,
    ]:
        candidate = _clean_candidate(candidate)
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    # For media/search tasks, the explicit query is often the best first TYPE text.
    if explicit_query and slots.task_type in {"media_search", "generic"}:
        candidates = [explicit_query] + [item for item in candidates if item != explicit_query]

    slots.query_candidates = candidates
    return slots
