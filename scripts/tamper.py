#!/usr/bin/env python3
"""Change one fact in a copy of a bundle, so the verifier can be shown catching it."""

from __future__ import annotations

import json
import sys


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]
    bundle = json.loads(open(src).read())
    facts = bundle["clusters"]["sanctions"]["facts"]
    facts[0]["fields"]["matched"] = True
    json.dump(bundle, open(dst, "w"))
    print(f"edited 1 fact in {dst}: sanctions.matched -> True")
    print(f"bundle_sha256 left untouched: {bundle['bundle_sha256'][:24]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
