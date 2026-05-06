"""Measure whether CandidateMiner candidates cover public CLICK ref boxes.

The report answers: for each public ref CLICK step, is there at least one
candidate center inside one of the official acceptable boxes?
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "code-for-student"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_base import AgentInput, AgentOutput  # noqa: E402
from utils.candidate_miner import CandidateMiner  # noqa: E402
from utils.memory import AgentMemory  # noqa: E402
from utils.task_parser import parse_task  # noqa: E402


def point_in_box(point: List[int], params: Dict[str, Any]) -> bool:
    x_range = params.get("x") or []
    y_range = params.get("y") or []
    return (
        len(point) == 2
        and len(x_range) == 2
        and len(y_range) == 2
        and x_range[0] <= point[0] <= x_range[1]
        and y_range[0] <= point[1] <= y_range[1]
    )


def normalize_moves(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def make_output(move: Dict[str, Any]) -> AgentOutput:
    action = move.get("action", "")
    params = move.get("params", {})
    if action == "CLICK":
        x_range = params.get("x", [500, 500])
        y_range = params.get("y", [500, 500])
        return AgentOutput(action="CLICK", parameters={"point": [int((x_range[0] + x_range[1]) / 2), int((y_range[0] + y_range[1]) / 2)]})
    if action == "TYPE":
        return AgentOutput(action="TYPE", parameters={"text": params.get("text", "")})
    if action == "OPEN":
        return AgentOutput(action="OPEN", parameters={"app_name": params.get("app", "")})
    if action == "SCROLL":
        return AgentOutput(
            action="SCROLL",
            parameters={
                "start_point": params.get("start_point", [500, 800]),
                "end_point": params.get("end_point", [500, 300]),
            },
        )
    return AgentOutput(action="COMPLETE", parameters={})


def iter_nominal_steps(ref_data: Dict[str, Any]) -> Iterable[tuple[str, Dict[str, Any], List[Dict[str, Any]]]]:
    status = "0"
    seen = set()
    while status and status != "#" and status not in seen:
        seen.add(status)
        moves = normalize_moves(ref_data.get(status, []))
        if not moves:
            break
        yield status, moves[0], moves
        status = moves[0].get("next", "#")


def analyze_case(case_dir: Path) -> List[Dict[str, Any]]:
    ref_data = json.loads((case_dir / "ref.json").read_text(encoding="utf-8"))
    overview = ref_data.get("case_overview", {})
    instruction = overview.get("instruction", "")
    task_slots = parse_task(instruction)
    memory = AgentMemory()
    miner = CandidateMiner()
    rows = []

    for status, nominal_move, acceptable_moves in iter_nominal_steps(ref_data):
        screenshot = case_dir / f"{status}.png"
        if screenshot.exists():
            image = Image.open(screenshot).convert("RGB")
        else:
            image = Image.new("RGB", (480, 1056), "white")
        step_count = len(memory.actions) + 1
        input_data = AgentInput(instruction=instruction, current_image=image, step_count=step_count)
        memory.task_slots = task_slots
        candidates = miner.build(input_data, memory, task_slots)
        memory.last_candidates = candidates

        click_moves = [move for move in acceptable_moves if move.get("action") == "CLICK"]
        if click_moves:
            matches = []
            for candidate in candidates:
                for move in click_moves:
                    if point_in_box(candidate.center, move.get("params", {})):
                        matches.append(candidate)
                        break
            rows.append(
                {
                    "case": case_dir.name,
                    "status": status,
                    "step": step_count,
                    "covered": bool(matches),
                    "matched": [f"{item.element_id}:{item.kind}@{item.center}" for item in matches],
                    "candidate_count": len(candidates),
                    "acceptable_boxes": [move.get("params", {}) for move in click_moves],
                }
            )

        memory.update(make_output(nominal_move), input_data)
    return rows


def summarize(rows: List[Dict[str, Any]]) -> str:
    total = len(rows)
    covered = sum(1 for row in rows if row["covered"])
    by_case = defaultdict(lambda: [0, 0])
    uncovered_by_case = defaultdict(list)
    for row in rows:
        by_case[row["case"]][0] += 1
        if row["covered"]:
            by_case[row["case"]][1] += 1
        else:
            uncovered_by_case[row["case"]].append(row)

    lines = [
        "# Candidate Coverage Report",
        "",
        f"- CLICK steps: {total}",
        f"- Covered: {covered}",
        f"- Coverage: {covered / total:.2%}" if total else "- Coverage: n/a",
        "",
        "## Coverage By Case",
    ]
    for case, (case_total, case_covered) in sorted(by_case.items()):
        lines.append(f"- {case}: {case_covered}/{case_total} = {case_covered / case_total:.2%}")

    lines.extend(["", "## Uncovered CLICK Steps"])
    for case, case_rows in sorted(uncovered_by_case.items()):
        for row in case_rows:
            boxes = row["acceptable_boxes"]
            lines.append(
                f"- {case} status={row['status']} step={row['step']} candidates={row['candidate_count']} boxes={boxes}"
            )

    matched_counter = Counter()
    for row in rows:
        for matched in row["matched"]:
            matched_counter[matched.split("@", 1)[0]] += 1
    lines.extend(["", "## Matched Candidate Kinds"])
    for key, count in matched_counter.most_common():
        lines.append(f"- {key}: {count}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=SRC / "test_data" / "offline")
    parser.add_argument("--output", "-o", type=Path, help="Optional markdown output path")
    args = parser.parse_args()

    rows: List[Dict[str, Any]] = []
    for case_dir in sorted(args.data_dir.iterdir()):
        if (case_dir / "ref.json").exists():
            rows.extend(analyze_case(case_dir))

    report = summarize(rows)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
