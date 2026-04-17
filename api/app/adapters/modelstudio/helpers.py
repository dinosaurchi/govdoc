"""JSON fence stripping helpers per §17.12."""

from __future__ import annotations


def strip_json_fences(s: str) -> str:
    """Strip markdown code fences from AI response, returning clean JSON string.

    Contract:
    - Input '{"a": 1}' -> '{"a": 1}' (unchanged)
    - Input '```json\\n{"a":1}\\n```' -> '{"a":1}'
    - Input '```\\n{"a":1}\\n```' (no lang tag) -> '{"a":1}'
    - Input with surrounding whitespace is .strip()-ed
    - Input 'garbage' -> returned unchanged (caller handles JSONDecodeError)
    - Nested triple backticks inside string literals must not break parsing
    """
    s = s.strip()

    if s.startswith("```"):
        lines = s.split("\n")
        inside = False
        json_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if not inside:
                    # Skip the opening fence (might have language tag like ```json)
                    inside = True
                    continue
                else:
                    # Closing fence
                    break
            if inside:
                json_lines.append(line)
        return "\n".join(json_lines).strip()

    return s
