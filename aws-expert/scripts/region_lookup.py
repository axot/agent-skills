#!/usr/bin/env python3
"""Look up AWS region label from a region name or code.

Usage:
    python3 region_lookup.py <region_name_or_code>

Examples:
    python3 region_lookup.py Tokyo
    python3 region_lookup.py Oregon
    python3 region_lookup.py ap-northeast-1

Output:
    Asia Pacific (Tokyo)
"""

import sys
from typing import Optional

from fetch_json import fetch_json

LOCATIONS_URL = "https://b0.p.awsstatic.com/locations/1.0/aws/current/locations.json"


def find_region_label(query: str) -> Optional[str]:
    locations = fetch_json(LOCATIONS_URL, timeout=10)
    q = query.strip().lower()

    # Pass 1: exact match on name or code
    for loc in locations.values():
        name = loc.get("name", "")
        code = loc.get("code", "")
        if q in (name.lower(), code.lower()):
            return loc.get("label", "")

    # Pass 2: substring match (less precise, first hit wins)
    for loc in locations.values():
        name = loc.get("name", "")
        label = loc.get("label", "")
        if q in name.lower() or q in label.lower():
            return label

    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 region_lookup.py <region_name_or_code>", file=sys.stderr)
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    label = find_region_label(query)

    if label:
        print(label)
    else:
        print(f"Region not found: {query}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
