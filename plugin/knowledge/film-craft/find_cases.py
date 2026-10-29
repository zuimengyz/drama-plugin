"""Read-only lookup; legacy mode is dependency-free, facets use the Plugin reader.

Stable catalog order is not an aesthetic ranking.
"""
import argparse
import json
from pathlib import Path
import sys

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
    parser.add_argument("--style", action="append", default=[])
    parser.add_argument("--goal", action="append", default=[])
    parser.add_argument("--means", action="append", default=[])
    parser.add_argument("--discipline", action="append", default=[])
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--read", action="store_true", help="Load selected case and shared-method originals")
    parser.add_argument("--expression", default="", help="Expression question; expands known goal aliases")
    args = parser.parse_args()
    try:
        if args.expression or args.style or args.goal or args.means or args.discipline or args.case or args.read:
            if args.problem:
                parser.error("Use legacy --problem separately, or new --goal facets")
            sys.path.insert(0, str(ROOT.parents[1] / 'src'))
            from drama_plugin.creative_engine.craft_knowledge import discover, reading
            selection = dict(query=args.expression or args.query, styles=args.style, goals=args.goal,
                means=args.means, disciplines=args.discipline, caseIds=args.case, limit=args.limit)
            result = reading(ROOT.parent, selection) if args.read else discover(ROOT.parent,
                query=selection['query'], styles=args.style, goals=args.goal, means=args.means,
                disciplines=args.discipline, case_ids=args.case, limit=args.limit)
        else:
            result = find_cases(problems=args.problem, query=args.query, limit=args.limit)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
