#!/usr/bin/env python3
"""Capture parser utility for analyzing packet captures from the Beryl AX device.

This module intentionally focuses on passive analysis and defensive insight.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List


DEFAULT_THRESHOLDS = {
    "deauth_burst": 25,
}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a packet record into expected fields."""
    return {
        "timestamp": raw.get("timestamp") or raw.get("ts") or "",
        "bssid": (raw.get("bssid") or "").lower(),
        "ssid": raw.get("ssid") or "",
        "channel": _safe_int(raw.get("channel"), 0),
        "signal": _safe_float(raw.get("signal"), 0.0),
        "frame_type": (raw.get("frame_type") or "").lower(),
        "subtype": (raw.get("subtype") or "").lower(),
        "src": (raw.get("src") or "").lower(),
        "dst": (raw.get("dst") or "").lower(),
        "encryption": (raw.get("encryption") or "unknown").lower(),
    }


def _read_capture_records(filename: str) -> List[Dict[str, Any]]:
    """Read packet records from a JSON or CSV file."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".json":
        with open(filename, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            return [_normalize_record(item if isinstance(item, dict) else {}) for item in payload]
        if isinstance(payload, dict):
            records = payload.get("packets", [])
            if isinstance(records, list):
                return [_normalize_record(item if isinstance(item, dict) else {}) for item in records]
        return []

    if ext in {".csv", ".txt"}:
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [_normalize_record(row) for row in reader]

    return []


def _build_summary(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    records = records if isinstance(records, list) else list(records)
    unique_bssids = {r["bssid"] for r in records if r["bssid"]}
    unique_clients = {
        addr
        for r in records
        for addr in (r["src"], r["dst"])
        if addr and addr != "ff:ff:ff:ff:ff:ff"
    }

    frame_counts = Counter(r["frame_type"] for r in records if r["frame_type"])
    subtype_counts = Counter(r["subtype"] for r in records if r["subtype"])

    return {
        "total_records": len(records),
        "unique_access_points": len(unique_bssids),
        "unique_clients": len(unique_clients),
        "frame_counts": dict(frame_counts),
        "subtype_counts": dict(subtype_counts),
    }


def _build_alerts(records: Iterable[Dict[str, Any]], thresholds: Dict[str, int]) -> List[Dict[str, str]]:
    records = list(records)
    alerts: List[Dict[str, str]] = []

    # Open network visibility for hardening opportunities.
    open_networks = sorted({r["ssid"] for r in records if r["encryption"] in {"open", "none"} and r["ssid"]})
    if open_networks:
        alerts.append(
            {
                "type": "open_network",
                "severity": "medium",
                "message": f"Detected open networks: {', '.join(open_networks)}",
            }
        )

    # Potential evil twin heuristics: same SSID advertised by multiple BSSIDs.
    by_ssid: Dict[str, set[str]] = defaultdict(set)
    for record in records:
        ssid = record["ssid"]
        bssid = record["bssid"]
        if ssid and bssid:
            by_ssid[ssid].add(bssid)

    suspicious_ssids = sorted(ssid for ssid, bssids in by_ssid.items() if len(bssids) > 1)
    if suspicious_ssids:
        alerts.append(
            {
                "type": "possible_evil_twin",
                "severity": "medium",
                "message": (
                    "Multiple BSSIDs advertise same SSID: "
                    f"{', '.join(suspicious_ssids)}"
                ),
            }
        )

    deauth_count = sum(1 for r in records if r["subtype"] == "deauth")
    if deauth_count >= thresholds["deauth_burst"]:
        alerts.append(
            {
                "type": "deauth_burst",
                "severity": "high",
                "message": (
                    f"Observed {deauth_count} deauth frames, above threshold "
                    f"{thresholds.get('deauth_burst', DEFAULT_THRESHOLDS['deauth_burst'])}."
                ),
            }
        )

    return alerts


def parse_capture(filename: str, thresholds: Dict[str, int] | None = None) -> Dict[str, Any]:
    """Parse a packet capture summary file.

    Supports `.json` and `.csv` exports from packet analysis workflows.
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Capture file not found: {filename}")

    merged_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    records = _read_capture_records(filename)

    return {
        "filename": filename,
        "file_size": os.path.getsize(filename),
        "packets": records,
        "summary": _build_summary(records),
        "alerts": _build_alerts(records, merged_thresholds),
        "status": "parsed" if records else "metadata_only",
    }


def main() -> None:
    """Main entry point for the capture parser."""
    print("Beryl AX Pineapple - Defensive Capture Parser")
    print("-" * 50)

    if len(sys.argv) < 2:
        print("Usage: capture_parser.py <capture_file>")
        print("\nAccepted formats:")
        print("  - JSON packet arrays")
        print("  - CSV with packet columns (ssid,bssid,subtype,...)")
        sys.exit(1)

    capture_file = sys.argv[1]

    try:
        result = parse_capture(capture_file)
        print(f"\nCapture File: {result['filename']}")
        print(f"File Size: {result['file_size']} bytes")
        print(f"Records Found: {result['summary']['total_records']}")
        print(f"Unique APs: {result['summary']['unique_access_points']}")
        print(f"Unique Clients: {result['summary']['unique_clients']}")
        print(f"Alerts: {len(result['alerts'])}")
        for alert in result["alerts"]:
            print(f"  - [{alert['severity'].upper()}] {alert['message']}")
        print(f"Status: {result['status']}")
        print("\n✓ Parsing completed successfully")
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:  # pragma: no cover - defensive CLI path
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
