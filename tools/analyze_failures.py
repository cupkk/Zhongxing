"""Analyze official runner logs and group first-failure causes.

Usage:
    python tools/analyze_failures.py path/to/log.txt
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path


CASE_RE = re.compile(r"Start testing case:\s*(?P<case>\S+)")
STEP_RE = re.compile(r"--- Step (?P<step>\d+):")
ACTION_RE = re.compile(r"Agent Output: action=(?P<action>[A-Z]+), params=(?P<params>.*)")


def classify(line: str) -> str:
    if "Action mismatch" in line:
        if "expect [CLICK], got [COMPLETE]" in line:
            return "early_complete"
        if "expect [COMPLETE], got [CLICK]" in line:
            return "extra_click_after_done"
        return "wrong_action"
    if "CLICK failed" in line or "not in scope" in line:
        return "click_miss"
    if "TYPE:" in line:
        return "type_mismatch"
    if "OPEN:" in line:
        return "open_mismatch"
    if "SCROLL:" in line:
        return "scroll_mismatch"
    return "other"


def analyze(text: str):
    current_case = ""
    current_step = ""
    last_action = ""
    rows = []

    for line in text.splitlines():
        case_match = CASE_RE.search(line)
        if case_match:
            current_case = case_match.group("case")
            current_step = ""
            last_action = ""
            continue

        step_match = STEP_RE.search(line)
        if step_match:
            current_step = step_match.group("step")
            last_action = ""
            continue

        action_match = ACTION_RE.search(line)
        if action_match:
            last_action = f"{action_match.group('action')} {action_match.group('params')}"
            continue

        if "[Checker]" in line and (
            "mismatch" in line
            or "failed" in line
            or "not in scope" in line
            or "TYPE:" in line
            or "OPEN:" in line
            or "SCROLL:" in line
        ):
            rows.append(
                {
                    "case": current_case,
                    "step": current_step,
                    "category": classify(line),
                    "last_action": last_action,
                    "checker": line.strip(),
                }
            )

    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", help="official runner log file")
    args = parser.parse_args()

    text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    rows = analyze(text)
    counts = Counter(row["category"] for row in rows)
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case"]].append(row)

    print("Failure category counts:")
    for category, count in counts.most_common():
        print(f"- {category}: {count}")

    print("\nFirst failure per case:")
    for case, case_rows in by_case.items():
        row = case_rows[0]
        print(f"- {case} step {row['step']} [{row['category']}]")
        print(f"  action: {row['last_action']}")
        print(f"  checker: {row['checker']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
