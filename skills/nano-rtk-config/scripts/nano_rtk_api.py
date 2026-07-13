#!/usr/bin/env python3
"""
Lightweight NANO RTK HTTP API helper.

Uses only the Python standard library so the skill stays portable.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import json
import socket
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


def make_request(method: str, base: str, path: str, body: str | None, timeout: float) -> tuple[bytes, str | None]:
    url = build_url(base, path)
    data = parse_body(body)
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url=url, data=data, headers=headers, method=method.upper())
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type")


def run_request(method: str, base: str, path: str, body: str | None, timeout: float, compact: bool) -> int:
    url = build_url(base, path)
    try:
        payload, content_type = make_request(method, base, path, body, timeout)
        emit_response(payload, content_type, compact)
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


def parse_network(raw: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    try:
        return ipaddress.ip_network(raw, strict=False)
    except ValueError as exc:
        raise SystemExit(f"Invalid subnet: {raw}") from exc


def candidate_hosts(raw: str) -> list[str]:
    network = parse_network(raw)
    return [str(host) for host in network.hosts()]


def is_candidate_local_ip(raw: str) -> bool:
    try:
        addr = ipaddress.ip_address(raw)
    except ValueError:
        return False
    if addr.version != 4:
        return False
    return not (addr.is_loopback or addr.is_multicast or addr.is_unspecified)


def discover_local_ips() -> list[str]:
    candidates: set[str] = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 80))
            ip = sock.getsockname()[0]
            if is_candidate_local_ip(ip):
                candidates.add(ip)
    except OSError:
        pass

    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            if family == socket.AF_INET:
                ip = sockaddr[0]
                if is_candidate_local_ip(ip):
                    candidates.add(ip)
    except socket.gaierror:
        pass

    try:
        _, _, ips = socket.gethostbyname_ex(socket.gethostname())
        for ip in ips:
            if is_candidate_local_ip(ip):
                candidates.add(ip)
    except socket.gaierror:
        pass

    return sorted(candidates)


def subnet_prefix_for_ip(raw: str) -> int:
    addr = ipaddress.ip_address(raw)
    if addr.version != 4:
        raise SystemExit(f"Only IPv4 local discovery is supported, got: {raw}")
    if addr.is_link_local:
        return 16
    return 24


def infer_local_subnets() -> list[str]:
    subnets: list[str] = []
    seen: set[str] = set()
    for ip in discover_local_ips():
        network = ipaddress.ip_network(f"{ip}/{subnet_prefix_for_ip(ip)}", strict=False)
        cidr = str(network)
        if cidr not in seen:
            seen.add(cidr)
            subnets.append(cidr)
    return subnets


def parse_json_payload(payload: bytes, content_type: str | None) -> Any | None:
    if not content_type or "application/json" not in content_type:
        return None
    try:
        return json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


def summarize_discovered_device(host: str, payload: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"ip": host}
    if isinstance(payload, dict):
        for key in ("model", "fw_version", "device_id", "gnss_version", "name"):
            if key in payload:
                result[key] = payload[key]
        if "data" in payload and isinstance(payload["data"], dict):
            for key in ("model", "fw_version", "device_id", "gnss_version", "name"):
                if key in payload["data"] and key not in result:
                    result[key] = payload["data"][key]
        if len(result) == 1:
            result["response"] = payload
        return result
    result["response"] = payload
    return result


def is_http_service_reachable(host: str, timeout: float) -> bool:
    try:
        with socket.create_connection((host, 80), timeout=timeout):
            return True
    except OSError:
        return False


def probe_host(host: str, path: str, timeout: float) -> dict[str, Any] | None:
    try:
        payload, content_type = make_request("GET", host, path, None, timeout)
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None
    parsed = parse_json_payload(payload, content_type)
    return summarize_discovered_device(host, parsed)


def discover_reachable_hosts(hosts: list[str], timeout: float, workers: int) -> list[str]:
    candidates: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(is_http_service_reachable, host, timeout): host for host in hosts}
        for future in concurrent.futures.as_completed(future_map):
            host = future_map[future]
            if future.result():
                candidates.append(host)
    return candidates


def confirm_candidate_hosts(hosts: list[str], path: str, timeout: float, workers: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(probe_host, host, path, timeout): host for host in hosts}
        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            if result is not None:
                results.append(result)
    return results


def discover_devices_in_subnet(
    subnet: str,
    path: str,
    timeout: float,
    workers: int,
) -> list[dict[str, Any]]:
    hosts = candidate_hosts(subnet)
    candidates = discover_reachable_hosts(hosts, timeout, workers)
    return confirm_candidate_hosts(sorted(candidates), path, timeout, workers)


def emit_discovery_results(results: list[dict[str, Any]], compact: bool) -> int:
    results.sort(key=lambda item: item["ip"])
    if compact:
        print(json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def discover_devices(subnet: str, path: str, timeout: float, workers: int, compact: bool) -> int:
    return emit_discovery_results(discover_devices_in_subnet(subnet, path, timeout, workers), compact)


def discover_local_devices(path: str, timeout: float, workers: int, compact: bool) -> int:
    subnets = infer_local_subnets()
    if not subnets:
        raise SystemExit("Could not infer a local IPv4 subnet. Use --discover-subnet explicitly.")

    merged: dict[str, dict[str, Any]] = {}
    for subnet in subnets:
        for item in discover_devices_in_subnet(subnet, path, timeout, workers):
            merged[item["ip"]] = item
    return emit_discovery_results(list(merged.values()), compact)


def main() -> int:
    parser = argparse.ArgumentParser(description="Query or update a NANO RTK device over HTTP.")
    parser.add_argument("base", nargs="?", help="Device IP, hostname, or full base URL")
    parser.add_argument("method", nargs="?", help="HTTP method such as GET, POST, PATCH, PUT")
    parser.add_argument("path", nargs="?", help="Endpoint path, with or without /api/v1 prefix")
    parser.add_argument("--body", help="JSON request body")
    parser.add_argument("--timeout", type=float, default=3.0, help="Request timeout in seconds")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    parser.add_argument("--discover-local", action="store_true", help="Infer the local subnet automatically and scan it for NANO RTK devices")
    parser.add_argument("--discover-subnet", help="Scan a local subnet such as 192.168.10.0/24 for NANO RTK devices")
    parser.add_argument("--discover-path", default="/system/info", help="Read-only endpoint used during subnet discovery")
    parser.add_argument("--discover-workers", type=int, default=32, help="Number of concurrent probes during subnet discovery")
    args = parser.parse_args()

    if args.discover_local:
        return discover_local_devices(
            args.discover_path,
            args.timeout,
            args.discover_workers,
            args.compact,
        )

    if args.discover_subnet:
        return discover_devices(
            args.discover_subnet,
            args.discover_path,
            args.timeout,
            args.discover_workers,
            args.compact,
        )

    if not args.base or not args.method or not args.path:
        parser.error("base, method, and path are required unless --discover-local or --discover-subnet is used")

    return run_request(args.method, args.base, args.path, args.body, args.timeout, args.compact)


if __name__ == "__main__":
    raise SystemExit(main())
