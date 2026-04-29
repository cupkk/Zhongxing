"""Map natural-language instructions to official app names."""

from __future__ import annotations

from typing import Optional


APP_KEYWORDS = [
    ("高德地图", ("高德地图", "高德")),
    ("携程旅行", ("携程旅行", "携程")),
    ("飞猪旅行", ("飞猪旅行", "飞猪")),
    ("去哪儿旅行", ("去哪儿旅行", "去哪儿", "去哪旅行", "机票", "酒店预订")),
    ("百度地图", ("百度地图", "地图", "导航", "路线", "打车")),
    ("哔哩哔哩", ("哔哩哔哩", "bilibili", "B站", "b站")),
    ("芒果TV", ("芒果TV", "芒果 tv", "芒果TV", "芒果视频", "芒果")),
    ("腾讯视频", ("腾讯视频",)),
    ("爱奇艺", ("爱奇艺",)),
    ("喜马拉雅", ("喜马拉雅",)),
    ("小红书", ("小红书",)),
    ("微博", ("微博",)),
    ("淘宝", ("淘宝",)),
    ("京东", ("京东",)),
    ("拼多多", ("拼多多",)),
    ("支付宝", ("支付宝",)),
    ("微信", ("微信",)),
    ("QQ", ("QQ", "qq")),
    ("网易云音乐", ("网易云音乐", "网易云")),
    ("QQ音乐", ("QQ音乐", "qq音乐")),
    ("快手", ("快手",)),
    ("抖音", ("抖音",)),
    ("美团", ("美团外卖", "美团", "外卖")),
    ("中兴管家", ("中兴管家",)),
]


def detect_app_name(instruction: str) -> Optional[str]:
    text = instruction or ""
    lower = text.lower()
    for app_name, keywords in APP_KEYWORDS:
        for keyword in keywords:
            if keyword in text or keyword.lower() in lower:
                return app_name
    return None


def normalize_app_name(app_name: str, instruction: str = "") -> str:
    raw = (app_name or "").strip()
    if raw:
        detected = detect_app_name(raw)
        if detected:
            return detected
        # Common informal names that should be converted exactly.
        aliases = {
            "B站": "哔哩哔哩",
            "b站": "哔哩哔哩",
            "bilibili": "哔哩哔哩",
            "芒果": "芒果TV",
            "芒果视频": "芒果TV",
            "去哪儿": "去哪儿旅行",
            "携程": "携程旅行",
            "飞猪": "飞猪旅行",
            "高德": "高德地图",
            "网易云": "网易云音乐",
        }
        if raw in aliases:
            return aliases[raw]
        return raw
    return detect_app_name(instruction) or ""
