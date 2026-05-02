"""Analyze whether real VLM logs use target_id or raw coordinates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def classify_decision(decision: Dict[str, Any]) -> str:
    action = decision.get("action", "")
    if action != "CLICK":
        return action or "UNKNOWN"
    if "target_id" in decision and "point" in decision:
        return "CLICK_TARGET_AND_POINT"
    if "target_id" in decision:
        return "CLICK_TARGET_ID"
    if "point" in decision:
        return "CLICK_POINT_ONLY"
    return "CLICK_NO_GROUNDING"


def summarize(rows: List[Dict[str, Any]]) -> str:
    vlm_rows = [row for row in rows if row.get("source") == "vlm"]
    class_counts = Counter(classify_decision(row.get("parsed_decision", {})) for row in vlm_rows)
    target_ids = Counter(
        row.get("parsed_decision", {}).get("target_id")
        for row in vlm_rows
        if "target_id" in row.get("parsed_decision", {})
    )
    raw_target = sum("target_id" in row.get("raw_output", "") for row in vlm_rows)
    raw_point = sum('"point"' in row.get("raw_output", "") or "'point'" in row.get("raw_output", "") for row in vlm_rows)

    lines = [
        "# target_id 使用分析",
        "",
        f"- 总决策记录：{len(rows)}",
        f"- VLM 决策记录：{len(vlm_rows)}",
        f"- VLM 原始输出包含 target_id：{raw_target}",
        f"- VLM 原始输出包含 point：{raw_point}",
        "",
        "## 解析后动作类型",
    ]
    for key, value in class_counts.most_common():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## target_id 分布"])
    for key, value in target_ids.most_common():
        lines.append(f"- target_id={key}: {value}")

    lines.extend(["", "## VLM 逐步明细"])
    for row in vlm_rows:
        decision = row.get("parsed_decision", {})
        final_action = row.get("final_action", {})
        raw = (row.get("raw_output", "") or "").replace("\n", " ")
        if len(raw) > 140:
            raw = raw[:137] + "..."
        lines.append(
            "- step={step} source={source} parsed={parsed} final={final} raw={raw}".format(
                step=row.get("step"),
                source=row.get("source"),
                parsed=decision,
                final=final_action,
                raw=raw,
            )
        )
        lines.append(f"  instruction={row.get('instruction', '')}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="Path to decisions.jsonl")
    parser.add_argument("--output", "-o", type=Path, help="Optional markdown report path")
    args = parser.parse_args()

    report = summarize(load_jsonl(args.jsonl))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
