#!/usr/bin/env python3
"""Fetch EC2 on-demand pricing for a given instance type and region.

Usage:
    python3 ec2_pricing.py <instance_type> <region_label>

Examples:
    python3 ec2_pricing.py r7g.4xlarge "Asia Pacific (Tokyo)"
    python3 ec2_pricing.py m5.large "US East (N. Virginia)"

Output:
    Instance Type: r7g.4xlarge
    Region: Asia Pacific (Tokyo)
    Price: $1.0336 /hr
    vCPU: 16
    Memory: 128 GiB
"""

import sys
import urllib.error
import urllib.parse
from typing import Optional

from fetch_json import fetch_json

PRICING_BASE = "https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel"


def fetch_pricing(region_label: str) -> dict:
    encoded = urllib.parse.quote(region_label, safe="")
    url = f"{PRICING_BASE}/{encoded}/Linux/index.json"
    return fetch_json(url)


def find_instance_price(data: dict, instance_type: str) -> Optional[dict]:
    for region_data in data.get("regions", {}).values():
        for details in region_data.values():
            if details.get("Instance Type", "").lower() == instance_type.lower():
                return details
    return None


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 ec2_pricing.py <instance_type> <region_label>", file=sys.stderr)
        sys.exit(1)

    instance_type = sys.argv[1]
    region_label = " ".join(sys.argv[2:])

    try:
        data = fetch_pricing(region_label)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"Error fetching pricing data: {e}", file=sys.stderr)
        sys.exit(1)

    result = find_instance_price(data, instance_type)
    if not result:
        print(f"Instance type {instance_type} not found in {region_label}", file=sys.stderr)
        sys.exit(1)

    print(f"Instance Type: {instance_type}")
    print(f"Region: {region_label}")
    print(f"Price: {result.get('price', 'N/A')} /hr")
    print(f"vCPU: {result.get('vCPU', 'N/A')}")
    print(f"Memory: {result.get('Memory', 'N/A')}")


if __name__ == "__main__":
    main()
