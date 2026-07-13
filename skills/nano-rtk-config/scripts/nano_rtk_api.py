#!/usr/bin/env python3
"""
Lightweight NANO RTK HTTP API helper.

Uses only the Python standard library so the skill stays portable.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def normalize_base(base: str) -> str:
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    return base.rstrip("/")


def normalize_path(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    if path.startswith("/api/"):
        return path
    return f"/api/v1{path}"


def build_url(base: str, path: str) -> str:
    return f"{normalize_base(base)}{normalize_path(path)}"


def parse_body(raw: str | None) -> bytes | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON body: {exc}") from exc
    return json.dumps(payload).encode("utf-8")


def emit_response(payload: bytes, content_type: str | None, compact: bool) -> None:
    text = payload.decode("utf-8", errors="replace")
    if content_type and "application/json" in content_type:
        try:
            parsed: Any = json.loads(text)
        except json.JSONDecodeError:
            print(text)
            return
        if compact:
            print(json.dumps(parsed, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print(text)


def run_request(method: str, base: str, path: str, body: str | None, timeout: float, compact: bool) -> int:
    url = build_url(base, path)
    data = parse_body(body)
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url=url, data=data, headers=headers, method=method.upper())

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            emit_response(payload, response.headers.get("Content-Type"), compact)
            return 0
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"HTTP {exc.code} for {url}\n")
        payload = exc.read()
        if payload:
            emit_response(payload, exc.headers.get("Content-Type"), compact)
        return 2
    except urllib.error.URLError as exc:
        reason = exc.reason if exc.reason else "unknown error"
        sys.stderr.write(f"Request failed for {url}: {reason}\n")
        return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Query or update a NANO RTK device over HTTP.")
    parser.add_argument("base", help="Device IP, hostname, or full base URL")
    parser.add_argument("method", help="HTTP method such as GET, POST, PATCH, PUT")
    parser.add_argument("path", help="Endpoint path, with or without /api/v1 prefix")
    parser.add_argument("--body", help="JSON request body")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    args = parser.parse_args()

    return run_request(args.method, args.base, args.path, args.body, args.timeout, args.compact)


if __name__ == "__main__":
    raise SystemExit(main())
