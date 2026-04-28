"""Tests for the capture parser script."""

import json
import os
import sys
import tempfile
import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from capture_parser import parse_capture


def test_parse_capture_with_valid_file():
    """Test parsing a valid capture file."""
    data = [
        {
            "ssid": "CorpWiFi",
            "bssid": "AA:BB:CC:DD:EE:01",
            "channel": 1,
            "subtype": "beacon",
            "frame_type": "management",
            "src": "AA:BB:CC:DD:EE:01",
            "dst": "ff:ff:ff:ff:ff:ff",
            "encryption": "wpa2",
        }
    ]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name

    try:
        result = parse_capture(tmp_path)
        assert result["filename"] == tmp_path
        assert result["summary"]["total_records"] == 1
        assert result["summary"]["unique_access_points"] == 1
        assert result["status"] == "parsed"
    finally:
        os.unlink(tmp_path)


def test_parse_capture_with_nonexistent_file():
    """Test parsing a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_capture("/nonexistent/file.pcap")


def test_parse_capture_returns_dict():
    """Test that parse_capture returns a dictionary."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pcap") as tmp:
        tmp_path = tmp.name

    try:
        result = parse_capture(tmp_path)
        assert isinstance(result, dict)
        assert "filename" in result
        assert "file_size" in result
        assert "packets" in result
        assert "status" in result
        assert result["status"] == "metadata_only"
    finally:
        os.unlink(tmp_path)


def test_parse_capture_alerts_for_suspicious_patterns():
    """Test parser emits expected passive detection alerts."""
    rows = "\n".join(
        [
            "ssid,bssid,channel,signal,frame_type,subtype,src,dst,encryption",
            "Guest,aa:aa:aa:aa:aa:01,1,-40,management,beacon,aa:aa:aa:aa:aa:01,ff:ff:ff:ff:ff:ff,open",
            "Guest,aa:aa:aa:aa:aa:02,6,-55,management,beacon,aa:aa:aa:aa:aa:02,ff:ff:ff:ff:ff:ff,wpa2",
        ] + [
            f"Guest,aa:aa:aa:aa:aa:01,1,-40,management,deauth,aa:aa:aa:aa:aa:01,11:22:33:44:55:{i:02x},wpa2"
            for i in range(0, 30)
        ]
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8") as tmp:
        tmp.write(rows)
        tmp_path = tmp.name

    try:
        result = parse_capture(tmp_path)
        alert_types = {alert["type"] for alert in result["alerts"]}
        assert "open_network" in alert_types
        assert "possible_evil_twin" in alert_types
        assert "deauth_burst" in alert_types
    finally:
        os.unlink(tmp_path)


def test_parse_capture_supports_txt_exports():
    """Test parser supports CSV-style .txt packet exports."""
    rows = "\n".join(
        [
            "ssid,bssid,channel,signal,frame_type,subtype,src,dst,encryption",
            "Office,aa:bb:cc:dd:ee:10,11,-42,management,beacon,aa:bb:cc:dd:ee:10,ff:ff:ff:ff:ff:ff,wpa2",
            "Office,aa:bb:cc:dd:ee:10,11,-47,data,,11:22:33:44:55:66,aa:bb:cc:dd:ee:10,wpa2",
        ]
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write(rows)
        tmp_path = tmp.name

    try:
        result = parse_capture(tmp_path)
        assert result["status"] == "parsed"
        assert result["summary"]["total_records"] == 2
        assert result["summary"]["unique_access_points"] == 1
        assert result["summary"]["unique_clients"] == 2
    finally:
        os.unlink(tmp_path)
