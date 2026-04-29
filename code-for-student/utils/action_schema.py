"""Action helpers for the competition output schema."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


VALID_ACTIONS = {"CLICK", "SCROLL", "TYPE", "OPEN", "COMPLETE"}

ACTION_ALIASES = {
    "tap": "CLICK",
    "press": "CLICK",
    "click": "CLICK",
    "点击": "CLICK",
    "点按": "CLICK",
    "输入": "TYPE",
    "input": "TYPE",
    "type": "TYPE",
    "scroll": "SCROLL",
    "swipe": "SCROLL",
    "滑动": "SCROLL",
    "滚动": "SCROLL",
    "open": "OPEN",
    "launch": "OPEN",
    "打开": "OPEN",
    "complete": "COMPLETE",
    "finish": "COMPLETE",
    "done": "COMPLETE",
    "完成": "COMPLETE",
}

SCROLL_DOWN = {"start_point": [500, 800], "end_point": [500, 300]}
SCROLL_UP = {"start_point": [500, 300], "end_point": [500, 800]}


def normalize_action(action: Any) -> str:
    """Normalize model action words to the official uppercase constants."""
    if action is None:
        return ""
    raw = str(action).strip().strip('"').strip("'")
    if not raw:
        return ""
    upper = raw.upper()
    if upper in VALID_ACTIONS:
        return upper
    return ACTION_ALIASES.get(raw.lower(), ACTION_ALIASES.get(raw, upper))


def clamp_point(point: Any, default: Optional[List[int]] = None) -> List[int]:
    """Convert a noisy point-like value into a normalized [x, y] pair."""
    if default is None:
        default = [500, 500]

    values = None
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        values = [point[0], point[1]]
    elif isinstance(point, dict):
        if "x" in point and "y" in point:
            values = [point["x"], point["y"]]
        elif "point" in point:
            return clamp_point(point["point"], default)
    elif isinstance(point, str):
        nums = re.findall(r"-?\d+(?:\.\d+)?", point)
        if len(nums) >= 2:
            values = [nums[0], nums[1]]

    if values is None:
        values = default

    try:
        x = int(round(float(values[0])))
        y = int(round(float(values[1])))
    except (TypeError, ValueError):
        x, y = default

    return [max(0, min(1000, x)), max(0, min(1000, y))]


def clean_text(text: Any) -> str:
    """Remove wrappers that models often add around TYPE content."""
    if text is None:
        return ""
    value = str(text).strip()
    if not value:
        return ""

    value = value.strip("`")
    value = re.sub(r"^(TYPE|type|输入)\s*[:：]\s*", "", value).strip()
    value = re.sub(r"^content\s*=\s*", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"^text\s*=\s*", "", value, flags=re.IGNORECASE).strip()
    value = value.strip()

    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        value = value[1:-1]

    value = value.replace("\\n", "\n").strip()
    # Keep user text intact, but remove obvious action/prose pollution.
    value = re.sub(r"\n.*$", "", value).strip()
    return value


def is_generic_text(text: str) -> bool:
    """Detect placeholder text that should be replaced by task slots."""
    if not text:
        return True
    lowered = text.lower()
    generic_words = {
        "内容",
        "搜索内容",
        "需要输入的文本",
        "请输入",
        "query",
        "keyword",
        "search",
        "text",
    }
    return lowered in generic_words or text in generic_words


def click_params(point: Any) -> Dict[str, List[int]]:
    return {"point": clamp_point(point)}


def scroll_params(direction: str = "down") -> Dict[str, List[int]]:
    if str(direction).lower() == "up":
        return dict(SCROLL_UP)
    return dict(SCROLL_DOWN)

