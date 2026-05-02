"""Lightweight UI element candidates used for safer click grounding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class UIElement:
    element_id: int
    kind: str
    bbox: Tuple[int, int, int, int]
    text: str = ""
    hint: str = ""
    score: float = 0.0

    @property
    def center(self) -> List[int]:
        x1, y1, x2, y2 = self.bbox
        return [int((x1 + x2) / 2), int((y1 + y2) / 2)]

    def to_dict(self) -> Dict[str, object]:
        return {
            "element_id": self.element_id,
            "kind": self.kind,
            "bbox": list(self.bbox),
            "center": self.center,
            "text": self.text,
            "hint": self.hint,
            "score": self.score,
        }


def find_by_kind(elements: List[UIElement], kind: str) -> UIElement | None:
    for element in elements:
        if element.kind == kind:
            return element
    return None


def find_by_id(elements: List[UIElement], element_id: int) -> UIElement | None:
    for element in elements:
        if element.element_id == element_id:
            return element
    return None
