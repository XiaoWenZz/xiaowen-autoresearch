from __future__ import annotations

import hashlib
from pathlib import Path
import unittest


REFERENCE = Path(__file__).parents[1] / "references" / "portfolio-lanes.md"
EXPECTED_SHA256 = (
    "f83c19f8edbdc4445a3fa4d548b3f19392d12fc02f25748f3938195ec323650e"
)


def extract_block(lines: list[str], block_id: int) -> list[str]:
    start_marker = f"<!-- dirty-semantic-block-{block_id}:start -->"
    end_marker = f"<!-- dirty-semantic-block-{block_id}:end -->"
    start = lines.index(start_marker) + 1
    end = lines.index(end_marker)
    if end <= start:
        raise AssertionError(f"semantic block {block_id} is empty")
    return lines[start:end]


class DirtySemanticPreservationTest(unittest.TestCase):
    def test_exact_three_block_hash_is_preserved(self) -> None:
        lines = REFERENCE.read_text(encoding="utf-8").splitlines()
        selected: list[str] = []
        for block_id in (1, 2, 3):
            selected.extend(extract_block(lines, block_id))
        payload = ("\n".join(selected) + "\n").encode("utf-8")
        self.assertEqual(len(selected), 48)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SHA256)


if __name__ == "__main__":
    unittest.main()
