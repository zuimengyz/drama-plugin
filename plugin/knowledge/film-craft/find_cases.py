"""Read-only, dependency-free lookup; stable order, no aesthetic ranking."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_cases(*, problems=(), query="", limit=3):
    if limit < 1:
        raise ValueError("limit must be positive")
    rows = json.loads((ROOT / "index.json").read_text())["cases"]
    known = {tag for row in rows for tag in row["tags"]}
    unknown = set(problems) - known
    if unknown:
        raise ValueError("Unknown tags: " + ", ".join(sorted(unknown)))
    results = []
    for row in rows:
        if problems and not set(problems).intersection(row["tags"]):
            continue
        note = ROOT / row["path"]
        haystack = " ".join([row["film"], row["problem"], *row["tags"], note.read_text()])
        if query and query.casefold() not in haystack.casefold():
            continue
        results.append({**row, "absolutePath": str(note)})
    return results[:limit]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", action="append", default=[])
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    try:
        result = find_cases(problems=args.problem, query=args.query, limit=args.limit)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
