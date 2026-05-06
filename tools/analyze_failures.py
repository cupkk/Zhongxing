"""Analyze official runner logs and group first-failure causes.

Usage:
    python tools/analyze_failures.py path/to/log.txt
    python tools/analyze_failures.py path/to/log.txt --csv failures.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


CASE_RE = re.compile(r"Start testing case:\s*(?P<case>\S+)")
STEP_RE = re.compile(r"--- Step (?P<step>\d+):")
ACTION_RE = re.compile(r"Agent Output: action=(?P<action>[A-Z]+), params=(?P<params>.*)")
RESULT_RE = re.compile(r"\[No\.\s*(?P<no>\d+):\s*(?P<case>[^\]]+)\]\s+Result:\s+(?P<result>PASS|FAIL)")
TOKEN_RE = re.compile(r"Token usage:.*total:\s*(?P<used>\d+)/(?P<limit>\d+)")


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


def extract_expected_action(line: str) -> str:
    match = re.search(r"expect \[([A-Z]+)\]", line)
    return match.group(1) if match else ""


def extract_actual_action(line: str) -> str:
    match = re.search(r"got \[([A-Z]+)\]", line)
    return match.group(1) if match else ""


def extract_click_point(line: str) -> str:
    match = re.search(r"\(([-\d]+),\s*([-\d]+)\)", line)
    if match:
        return f"{match.group(1)},{match.group(2)}"
    return ""


def _parse_point(point: str) -> tuple[int, int] | None:
    if not point:
        return None
    parts = point.split(",", 1)
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def infer_mechanism(row: dict) -> str:
    """Map raw checker failures to an actionable first-failure mechanism."""
    case = row.get("case", "")
    step = row.get("step", "")
    category = row.get("category", "")
    point = _parse_point(row.get("click_point", ""))

    if category == "click_miss" and step == "1":
        if any(token in case for token in ("douyin_lp", "jingdong_lp")) and point:
            x, y = point
            if x >= 760 and 420 <= y <= 720:
                return "initial_review_entry_scene_collapse"
        if any(token in case for token in ("jingdong_lp", "jd_lp")) and point:
            x, y = point
            if 420 <= x <= 620 and 420 <= y <= 620:
                return "initial_review_center_default_misclick"
        if any(token in case for token in ("douyin_lp", "pinduoduo_sl", "review", "comment")):
            return "initial_review_entry_misclick"
        if point:
            x, y = point
            if y >= 820 or (x <= 140 and y <= 160):
                return "initial_review_entry_misclick"
            if 420 <= x <= 620 and 420 <= y <= 620:
                return "initial_review_center_default_misclick"
    if category == "click_miss" and any(token in case for token in ("douyin_lp", "jingdong_lp", "review", "comment")) and point:
        x, y = point
        if "douyin_lp" in case and int(step or 0) == 3 and 300 <= x <= 650 and 520 <= y <= 720:
            return "douyin_form_top_step_mid_misclick"
        if "douyin_lp" in case and int(step or 0) >= 5 and 680 <= x <= 730 and 90 <= y <= 210:
            return "douyin_form_top_submit_point_miss"
        if int(step or 0) >= 5 and 430 <= x <= 570 and y >= 880:
            return "review_form_after_type_submit_point_miss"
        if int(step or 0) >= 3 and 300 <= x <= 650 and 520 <= y <= 720:
            return "review_form_mid_area_misclick"
        if int(step or 0) >= 3 and y >= 760:
            return "review_form_pre_type_bottom_misclick"
        if int(step or 0) >= 3 and 300 <= x <= 650 and 460 <= y <= 720:
            return "review_form_ready_type_reclick"
    if category == "wrong_action" and any(token in case for token in ("douyin_lp", "jingdong_lp", "review", "comment")):
        expected = row.get("expected_action", "")
        actual = row.get("actual_action", "")
        if expected == "TYPE" and actual == "CLICK":
            return "review_form_ready_type_reclick"
    if category == "click_miss":
        return "click_grounding_miss"
    if category == "early_complete":
        return "premature_complete"
    if category == "extra_click_after_done":
        return "extra_action_after_done"
    if category == "type_mismatch":
        return "type_slot_mismatch"
    return category or "other"


def suggest_fix(mechanism: str) -> str:
    suggestions = {
        "initial_review_entry_misclick": "keep narrow ActionVerifier/Validator guard; prefer review-entry candidates over send/back on step 1",
        "initial_review_entry_scene_collapse": "do not collapse all landing-page review tasks to the same entry; route by task text semantics",
        "initial_review_center_default_misclick": "snap generic center fallback to app-specific review-entry candidate on step 1",
        "review_form_pre_type_bottom_misclick": "before review text is typed, redirect bottom/input/send clicks to the large review text area",
        "review_form_ready_type_reclick": "after the review text area is focused, convert repeated clicks to TYPE with parsed review text",
        "douyin_form_top_step_mid_misclick": "for Douyin LP review forms, after entry and mid-sheet confirmation, route middle text-area clicks to the top form action first",
        "douyin_form_top_submit_point_miss": "for Douyin LP review forms after TYPE, snap near-miss top form submit points to the proven in-scope top action point",
        "review_form_mid_area_misclick": "in right-side ecommerce review forms, redirect middle/lower generic clicks to the large review text area",
        "review_form_after_type_submit_point_miss": "after form review text is typed, avoid excluded bottom-center/right-bottom points; try the form top publish/submit action",
        "click_grounding_miss": "inspect candidate coverage for the ref box; add task-family candidate before validator coordinate correction",
        "premature_complete": "tighten ActionVerifier complete gating using memory stage and required typed slots",
        "extra_action_after_done": "preserve force_complete only for known terminal rule paths; otherwise allow COMPLETE",
        "type_slot_mismatch": "fix task slot extraction or clean_text normalization; avoid hard-coded output text",
    }
    return suggestions.get(mechanism, "inspect first screenshot/state and add the narrowest guard")


def covered_by_current_guard(mechanism: str) -> str:
    coverage = {
        "initial_review_entry_misclick": "yes: ActionVerifier initial-review guard, Validator fallback, review state-machine tests, pseudo-hidden cases",
        "initial_review_entry_scene_collapse": "yes after 2026-05-04 fix: text-semantic lp review entry routing",
        "initial_review_center_default_misclick": "yes after 2026-05-03 lower-score fix: ActionVerifier center guard plus Validator center fallback",
        "review_form_pre_type_bottom_misclick": "yes after 2026-05-03 lower-score fix: pre-type review-form text-area guard",
        "review_form_ready_type_reclick": "yes after 2026-05-04 mid-form fix: text-focused review form guard converts repeated clicks to TYPE",
        "douyin_form_top_step_mid_misclick": "yes after 2026-05-04 44.83 fix: Douyin step3 middle click routes to review_form_top_submit",
        "douyin_form_top_submit_point_miss": "yes after 2026-05-06 fix: Douyin after-TYPE top submit candidate and raw point snap to [695,145]",
        "review_form_mid_area_misclick": "yes after 2026-05-04 latest fix: Jingdong mid-form generic points route to review_text_area",
        "review_form_after_type_submit_point_miss": "yes after 2026-05-04 latest fix: form review finish uses the top form submit candidate after bottom-center/right-bottom were excluded",
        "premature_complete": "partial: ActionVerifier complete guard and force_complete exception tests",
        "click_grounding_miss": "partial: CandidateMiner coverage report and target_id grounding",
        "extra_action_after_done": "partial: force_complete tests",
        "type_slot_mismatch": "partial: task parser and validator text cleanup",
    }
    return coverage.get(mechanism, "unknown")


def analyze(text: str):
    current_case = ""
    current_step = ""
    last_action = ""
    token_total = ""
    rows = []
    results = {}

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

        token_match = TOKEN_RE.search(line)
        if token_match:
            token_total = token_match.group("used")
            continue

        result_match = RESULT_RE.search(line)
        if result_match:
            results[result_match.group("case")] = result_match.group("result")
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
                row := {
                    "case": current_case,
                    "step": current_step,
                    "category": classify(line),
                    "last_action": last_action,
                    "checker": line.strip(),
                    "expected_action": extract_expected_action(line),
                    "actual_action": extract_actual_action(line),
                    "click_point": extract_click_point(line),
                    "token_total": token_total,
                }
            )
            row["mechanism"] = infer_mechanism(row)
            row["suggested_fix"] = suggest_fix(row["mechanism"])
            row["covered_by_current_guard"] = covered_by_current_guard(row["mechanism"])

    return rows, results


def first_failures(rows):
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case"]].append(row)
    return [case_rows[0] for _, case_rows in by_case.items()]


def write_csv(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case",
        "step",
        "category",
        "mechanism",
        "expected_action",
        "actual_action",
        "click_point",
        "last_action",
        "checker",
        "token_total",
        "suggested_fix",
        "covered_by_current_guard",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", help="official runner log file")
    parser.add_argument("--csv", type=Path, help="Optional CSV path for first-failure table")
    args = parser.parse_args()

    text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    rows, results = analyze(text)
    first_rows = first_failures(rows)
    counts = Counter(row["category"] for row in rows)
    first_counts = Counter(row["category"] for row in first_rows)

    print("Failure category counts:")
    for category, count in counts.most_common():
        print(f"- {category}: {count}")

    print("\nFirst-failure category counts:")
    for category, count in first_counts.most_common():
        print(f"- {category}: {count}")

    if results:
        result_counts = Counter(results.values())
        print("\nCase result counts:")
        for result, count in result_counts.most_common():
            print(f"- {result}: {count}")

    print("\nFirst failure per case:")
    for row in first_rows:
        case = row["case"]
        print(f"- {case} step {row['step']} [{row['category']} / {row.get('mechanism', '')}]")
        if row.get("expected_action") or row.get("actual_action") or row.get("click_point"):
            print(
                "  parsed: "
                f"expect={row.get('expected_action', '') or '?'} "
                f"got={row.get('actual_action', '') or '?'} "
                f"point={row.get('click_point', '') or '?'}"
            )
        print(f"  action: {row['last_action']}")
        print(f"  checker: {row['checker']}")
        if row.get("suggested_fix"):
            print(f"  suggested_fix: {row['suggested_fix']}")
        if row.get("covered_by_current_guard"):
            print(f"  covered_by_current_guard: {row['covered_by_current_guard']}")

    if args.csv:
        write_csv(args.csv, first_rows)
        print(f"\nWrote first-failure CSV: {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
