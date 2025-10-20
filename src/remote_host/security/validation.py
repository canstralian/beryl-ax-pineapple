"""
Input validation and sanitization utilities.

Provides functions to validate and sanitize user inputs to prevent:
- Command injection
- Path traversal
- SQL injection
- XSS attacks
"""

import ipaddress
import re
from pathlib import Path
from typing import Optional

import validators
from fastapi import HTTPException, status


def validate_ip_address(ip: str, allow_private: bool = True) -> str:
    """
    Validate and normalize an IP address.

    Args:
        ip: IP address string (IPv4 or IPv6)
        allow_private: Whether to allow private/internal IPs

    Returns:
        Normalized IP address string

    Raises:
        HTTPException: If IP is invalid or not allowed
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IP address: {ip}",
        )

    # Check for private/internal IPs if not allowed
    if not allow_private and (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Private/internal IP addresses not allowed: {ip}",
        )

    return str(ip_obj)


def validate_port(port: int, allow_privileged: bool = False) -> int:
    """
    Validate a port number.

    Args:
        port: Port number (1-65535)
        allow_privileged: Whether to allow privileged ports (1-1023)

    Returns:
        Validated port number

    Raises:
        HTTPException: If port is invalid or not allowed
    """
    if not (1 <= port <= 65535):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port must be between 1 and 65535: {port}",
        )

    if not allow_privileged and port < 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privileged ports (< 1024) not allowed: {port}",
        )

    return port


def validate_target(target: str, allow_domains: bool = True) -> str:
    """
    Validate a scan target (IP address or domain name).

    Args:
        target: Target IP or domain
        allow_domains: Whether to allow domain names (True) or only IPs (False)

    Returns:
        Validated target string

    Raises:
        HTTPException: If target is invalid
    """
    # Try to parse as IP address first
    try:
        return validate_ip_address(target, allow_private=True)
    except HTTPException:
        pass

    # If not an IP and domains are allowed, validate as domain
    if allow_domains:
        if validators.domain(target):
            # Additional checks: no localhost, no internal domains
            if target.lower() in ["localhost", "localhost.localdomain"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Localhost not allowed as target",
                )
            return target
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid target (must be IP or domain): {target}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target (must be IP address): {target}",
        )


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to prevent path traversal and invalid characters.

    Args:
        filename: Input filename
        max_length: Maximum allowed filename length

    Returns:
        Sanitized filename

    Raises:
        HTTPException: If filename is invalid or too long
    """
    # Remove path components (prevent path traversal)
    filename = Path(filename).name

    # Remove or replace dangerous characters
    # Allow: alphanumeric, dash, underscore, dot
    sanitized = re.sub(r"[^\w\-.]", "_", filename)

    # Prevent hidden files (starting with .)
    sanitized = sanitized.lstrip(".")

    # Prevent empty filename
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename (empty after sanitization)",
        )

    # Check length
    if len(sanitized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Filename too long (max {max_length} characters)",
        )

    return sanitized


def sanitize_path(path: str, base_dir: Path, must_exist: bool = False) -> Path:
    """
    Sanitize and validate a file path to prevent path traversal.

    Args:
        path: Input path string
        base_dir: Base directory that path must be within
        must_exist: Whether path must exist

    Returns:
        Resolved Path object

    Raises:
        HTTPException: If path is invalid, outside base_dir, or doesn't exist
    """
    try:
        # Resolve to absolute path
        full_path = (base_dir / path).resolve()

        # Ensure path is within base_dir (prevent path traversal)
        full_path.relative_to(base_dir.resolve())

        # Check existence if required
        if must_exist and not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path does not exist: {path}",
            )

        return full_path

    except ValueError:
        # Path is outside base_dir
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal detected",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid path: {str(e)}",
        )


def sanitize_command_arg(arg: str, allow_special_chars: bool = False) -> str:
    """
    Sanitize a command-line argument to prevent injection attacks.

    Args:
        arg: Command argument to sanitize
        allow_special_chars: Whether to allow limited special characters

    Returns:
        Sanitized argument

    Raises:
        HTTPException: If argument contains dangerous characters
    """
    # Dangerous characters that should never be allowed
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]

    for char in dangerous_chars:
        if char in arg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dangerous character not allowed in argument: {char}",
            )

    # If special chars not allowed, restrict to alphanumeric + basic chars
    if not allow_special_chars:
        if not re.match(r"^[\w\-\./:]+$", arg):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Argument contains invalid characters",
            )

    return arg


def validate_port_range(port_range: str) -> str:
    """
    Validate a port range specification (e.g., "80", "1-1000", "80,443,8080").

    Args:
        port_range: Port range string

    Returns:
        Validated port range string

    Raises:
        HTTPException: If port range is invalid
    """
    # Pattern: number, range (n-m), or comma-separated list
    pattern = r"^(\d+(-\d+)?)(,\d+(-\d+)?)*$"

    if not re.match(pattern, port_range):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid port range format: {port_range}",
        )

    # Validate individual ports
    parts = port_range.replace("-", ",").split(",")
    for part in parts:
        try:
            port = int(part)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid port number in range: {part}",
            )

    return port_range


def validate_scan_options(options: dict) -> dict:
    """
    Validate scan options to prevent abuse.

    Args:
        options: Dictionary of scan options

    Returns:
        Validated options dictionary

    Raises:
        HTTPException: If options are invalid or dangerous
    """
    # Allowlist of safe option keys
    allowed_keys = {
        "ports",
        "scan_type",
        "timing",
        "verbosity",
        "max_rate",
        "min_rate",
        "host_timeout",
        "script",
    }

    # Check for unknown keys
    unknown_keys = set(options.keys()) - allowed_keys
    if unknown_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scan options: {', '.join(unknown_keys)}",
        )

    # Validate specific options
    if "scan_type" in options:
        allowed_types = ["syn", "connect", "udp", "ack", "window", "null", "fin", "xmas"]
        if options["scan_type"] not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scan type: {options['scan_type']}",
            )

    if "timing" in options:
        try:
            timing = int(options["timing"])
            if not (0 <= timing <= 5):
                raise ValueError
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timing must be integer 0-5",
            )

    return options
