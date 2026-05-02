"""Robust parser for VLM action decisions."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict

from .action_schema import normalize_action


class OutputParser:
    def parse(self, raw_output: str) -> Dict[str, Any]:
        raw = raw_output or ""

        parsed = self._parse_json(raw)
        if parsed:
            parsed["action"] = normalize_action(parsed.get("action") or parsed.get("next_action"))
            return parsed

        parsed = self._parse_competition_style(raw)
        if parsed:
            return parsed

        parsed = self._parse_function_style(raw)
        if parsed:
            return parsed

        parsed = self._parse_labeled_action(raw)
        if parsed:
            return parsed

        action_match = re.search(r"Action\s*[:：]\s*([A-Za-z_\u4e00-\u9fa5]+)", raw, re.I)
        if action_match:
            return {"action": normalize_action(action_match.group(1))}

        return {"action": ""}

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        candidates = []
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S | re.I)
        if fence:
            candidates.append(fence.group(1))

        obj = self._extract_first_json_object(raw)
        if obj:
            candidates.append(obj)

        for candidate in candidates:
            cleaned = candidate.strip()
            try:
                value = json.loads(cleaned)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
            try:
                value = ast.literal_eval(cleaned)
                if isinstance(value, dict):
                    return value
            except (SyntaxError, ValueError):
                pass
        return {}

    @staticmethod
    def _extract_first_json_object(raw: str) -> str:
        start = raw.find("{")
        if start < 0:
            return ""
        depth = 0
        in_string = False
        quote = ""
        escape = False
        for index in range(start, len(raw)):
            ch = raw[index]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote:
                    in_string = False
                continue
            if ch in {'"', "'"}:
                in_string = True
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return raw[start : index + 1]
        return ""

    def _parse_competition_style(self, raw: str) -> Dict[str, Any]:
        text = raw.strip()
        action_match = re.search(r"\b(CLICK|TYPE|SCROLL|OPEN|COMPLETE)\b\s*[:：]\s*(.*)", text, re.I | re.S)
        if not action_match:
            return {}
        action = normalize_action(action_match.group(1))
        rest = action_match.group(2).strip()
        decision: Dict[str, Any] = {"action": action}

        if action == "CLICK":
            target_id = self._extract_target_id(rest)
            if target_id is not None:
                decision["target_id"] = target_id
            nums = re.findall(r"-?\d+(?:\.\d+)?", rest)
            if len(nums) >= 2:
                decision["point"] = [float(nums[0]), float(nums[1])]
        elif action == "SCROLL":
            nums = re.findall(r"-?\d+(?:\.\d+)?", rest)
            if len(nums) >= 4:
                decision["start_point"] = [float(nums[0]), float(nums[1])]
                decision["end_point"] = [float(nums[2]), float(nums[3])]
        elif action == "TYPE":
            content = re.search(r"\[['\"]?(.*?)['\"]?\]", rest, re.S)
            decision["text"] = content.group(1) if content else rest.strip("[]'\" ")
        elif action == "OPEN":
            content = re.search(r"\[['\"]?(.*?)['\"]?\]", rest, re.S)
            decision["app_name"] = content.group(1) if content else rest.strip("[]'\" ")
        return decision

    def _parse_function_style(self, raw: str) -> Dict[str, Any]:
        fn = re.search(r"\b(click|type|scroll|open|complete)\s*\((.*?)\)", raw, re.I | re.S)
        if not fn:
            return {}
        action = normalize_action(fn.group(1))
        args = fn.group(2)
        decision: Dict[str, Any] = {"action": action}

        if action == "CLICK":
            target_id = self._extract_target_id(args)
            if target_id is not None:
                decision["target_id"] = target_id
            nums = re.findall(r"-?\d+(?:\.\d+)?", args)
            if len(nums) >= 2:
                decision["point"] = [float(nums[0]), float(nums[1])]
        elif action == "SCROLL":
            nums = re.findall(r"-?\d+(?:\.\d+)?", args)
            if len(nums) >= 4:
                decision["start_point"] = [float(nums[0]), float(nums[1])]
                decision["end_point"] = [float(nums[2]), float(nums[3])]
        elif action == "TYPE":
            text = re.search(r"(?:content|text)\s*=\s*['\"](.*?)['\"]", args, re.S)
            if not text:
                text = re.search(r"['\"](.*?)['\"]", args, re.S)
            decision["text"] = text.group(1) if text else args.strip(" '\"")
        elif action == "OPEN":
            app = re.search(r"app_name\s*=\s*['\"](.*?)['\"]", args, re.S)
            if not app:
                app = re.search(r"['\"](.*?)['\"]", args, re.S)
            decision["app_name"] = app.group(1) if app else args.strip(" '\"")
        return decision

    def _parse_labeled_action(self, raw: str) -> Dict[str, Any]:
        text = raw.strip()
        label = re.search(r"(?:Action|动作|操作)\s*[:：]\s*(.+)", text, re.I | re.S)
        if label:
            text = label.group(1).strip()

        decision: Dict[str, Any] = {}
        if re.search(r"(CLICK|click|点击|点按|轻点)", text):
            target_id = self._extract_target_id(text)
            if target_id is not None:
                decision = {"action": "CLICK", "target_id": target_id}
                return decision
            nums = re.findall(r"-?\d+(?:\.\d+)?", text)
            if len(nums) >= 2:
                decision = {"action": "CLICK", "point": [float(nums[0]), float(nums[1])]}
        elif re.search(r"(SCROLL|scroll|滑动|滚动|上滑|下滑)", text):
            nums = re.findall(r"-?\d+(?:\.\d+)?", text)
            decision = {"action": "SCROLL"}
            if len(nums) >= 4:
                decision["start_point"] = [float(nums[0]), float(nums[1])]
                decision["end_point"] = [float(nums[2]), float(nums[3])]
            elif "上滑" in text or "向上" in text:
                decision["scroll_direction"] = "down"
            elif "下滑" in text or "向下" in text:
                decision["scroll_direction"] = "up"
        elif re.search(r"(TYPE|type|输入)", text):
            content = re.search(r"['\"“”](.*?)['\"“”]", text, re.S)
            if not content:
                content = re.search(r"(?:内容|文本|content|text)?\s*[:：=]\s*(.+)", text, re.S)
            decision = {"action": "TYPE", "text": content.group(1).strip() if content else ""}
        elif re.search(r"(OPEN|open|打开|启动)", text):
            app = re.search(r"['\"“”](.*?)['\"“”]", text, re.S)
            if not app:
                app = re.search(r"(?:应用|app_name|app)?\s*[:：=]\s*(.+)", text, re.S | re.I)
            decision = {"action": "OPEN", "app_name": app.group(1).strip() if app else ""}
        elif re.search(r"(COMPLETE|complete|完成|结束)", text):
            decision = {"action": "COMPLETE"}

        if decision:
            decision["action"] = normalize_action(decision.get("action"))
        return decision

    @staticmethod
    def _extract_target_id(text: str) -> int | None:
        match = re.search(r"(?:target_id|element_id|候选(?:元素)?id|目标id)\s*[:=：]\s*['\"]?(\d+)", text, re.I)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None
