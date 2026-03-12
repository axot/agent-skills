#!/usr/bin/env python3
import gzip
import json
import urllib.request

USER_AGENT = "aws-sa-expert/1.0"


def fetch_json(url: str, timeout: int = 15) -> dict:
    """Fetch a JSON response, transparently handling gzip encoding."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        try:
            data = gzip.decompress(raw)
        except gzip.BadGzipFile:
            data = raw
        return json.loads(data)
