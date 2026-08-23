#!/usr/bin/env python3
"""CLI for the read-only current-first local-state compatibility adapter."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from state_compat import lookup_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, help="Preferred current path")
    parser.add_argument("--legacy", required=True, help="Deprecated fallback path")
    parser.add_argument("--deprecated-since", required=True, help="Migration start date or release")
    parser.add_argument("--remove-after", required=True, help="Earliest allowed legacy removal date or release")
    parser.add_argument("--format", choices=("json", "path", "tsv"), default="json")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    result = lookup_path(
        Path(args.current),
        Path(args.legacy),
        deprecated_since=args.deprecated_since,
        remove_after=args.remove_after,
    )
    if args.format == "path":
        print(result.path)
    elif args.format == "tsv":
        print(
            "\t".join(
                (
                    result.origin,
                    result.path,
                    "true" if result.deprecated else "false",
                    result.deprecated_since,
                    result.remove_after,
                    result.reason,
                )
            )
        )
    else:
        print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
