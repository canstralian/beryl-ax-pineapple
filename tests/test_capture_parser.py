"""Tests for the capture parser script."""

import os
import sys
import tempfile
import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from capture_parser import parse_capture


def test_parse_capture_with_valid_file():
    """Test parsing a valid capture file."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test packet data")
        tmp_path = tmp.name

    try:
        result = parse_capture(tmp_path)
        assert result["filename"] == tmp_path
        assert result["file_size"] == 16
        assert result["packets"] == []
        assert result["status"] == "ready_for_parsing"
    finally:
        os.unlink(tmp_path)


def test_parse_capture_with_nonexistent_file():
    """Test parsing a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_capture("/nonexistent/file.pcap")


def test_parse_capture_returns_dict():
    """Test that parse_capture returns a dictionary."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = parse_capture(tmp_path)
        assert isinstance(result, dict)
        assert "filename" in result
        assert "file_size" in result
        assert "packets" in result
        assert "status" in result
    finally:
        os.unlink(tmp_path)
